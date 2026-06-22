'use strict';

// Guard against double-injection (e.g. from scripting.executeScript calls).
if (!window.__sw_loaded) {
  window.__sw_loaded = true;
  main();
}

function main() {
  if (!document.body) return;

  // -----------------------------------------------------------------------
  // Floating action button (FAB)
  // -----------------------------------------------------------------------

  const fab = document.createElement('button');
  fab.id = 'sw-fab';
  fab.textContent = 'W';
  fab.title = 'SmartWrite: correct selected text';
  document.body.appendChild(fab);

  // -----------------------------------------------------------------------
  // Inline correction panel
  // -----------------------------------------------------------------------

  const panel = document.createElement('div');
  panel.id = 'sw-panel';
  panel.innerHTML = `
    <div class="sw-ph">
      <span class="sw-logo">SmartWrite</span>
      <button id="sw-close" title="Close">&#x2715;</button>
    </div>
    <div class="sw-pb">
      <!-- Shown when user is not logged in -->
      <div id="sw-notauth" class="sw-notice sw-hidden">
        <p>You&#8217;re not signed in.</p>
        <p>Click the <strong>SmartWrite</strong> extension icon in the toolbar to sign in.</p>
      </div>

      <!-- Main correction UI -->
      <div id="sw-ui" class="sw-hidden">
        <div class="sw-field">
          <label>Text to correct</label>
          <textarea id="sw-input" rows="4" maxlength="5000"></textarea>
          <span id="sw-char-count">0 / 5000</span>
        </div>
        <div class="sw-row">
          <select id="sw-tone">
            <option value="">Auto-detect tone</option>
            <option value="formal">Formal</option>
            <option value="casual">Casual</option>
            <option value="friendly">Friendly</option>
            <option value="professional">Professional</option>
          </select>
          <button id="sw-correct-btn">Correct</button>
        </div>
        <div id="sw-error" class="sw-error sw-hidden"></div>
        <div id="sw-loading" class="sw-hidden">Correcting&hellip;</div>
        <div id="sw-result" class="sw-hidden">
          <div class="sw-meta">
            <span id="sw-detected"></span>
            <span id="sw-applied"></span>
          </div>
          <div id="sw-corrected"></div>
          <div class="sw-row-mt">
            <span id="sw-summary"></span>
            <button id="sw-copy-btn">Copy</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(panel);

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  function swShow(id) { panel.querySelector('#' + id).classList.remove('sw-hidden'); }
  function swHide(id) { panel.querySelector('#' + id).classList.add('sw-hidden'); }

  function sendMsg(msg) {
    return new Promise(resolve => {
      try {
        chrome.runtime.sendMessage(msg, response => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
          } else {
            resolve(response);
          }
        });
      } catch {
        resolve({ ok: false, error: 'Extension context invalid. Reload the page.' });
      }
    });
  }

  function updateCharCount() {
    const len = panel.querySelector('#sw-input').value.length;
    panel.querySelector('#sw-char-count').textContent = `${len} / 5000`;
  }

  // -----------------------------------------------------------------------
  // Open / close panel
  // -----------------------------------------------------------------------

  async function openPanel(selectedText) {
    // Reset state
    swHide('sw-error');
    swHide('sw-result');
    swHide('sw-loading');

    panel.querySelector('#sw-input').value = selectedText;
    updateCharCount();

    // Check auth before showing the correction UI
    const { token } = await sendMsg({ action: 'getConfig' });
    if (token) {
      swHide('sw-notauth');
      swShow('sw-ui');
    } else {
      swShow('sw-notauth');
      swHide('sw-ui');
    }

    panel.classList.add('sw-open');
  }

  panel.querySelector('#sw-close').addEventListener('click', () => {
    panel.classList.remove('sw-open');
  });

  // -----------------------------------------------------------------------
  // Char counter
  // -----------------------------------------------------------------------

  panel.querySelector('#sw-input').addEventListener('input', updateCharCount);

  // -----------------------------------------------------------------------
  // Correct button
  // -----------------------------------------------------------------------

  panel.querySelector('#sw-correct-btn').addEventListener('click', async () => {
    const text = panel.querySelector('#sw-input').value.trim();
    if (!text) return;

    const tone = panel.querySelector('#sw-tone').value || null;
    const btn  = panel.querySelector('#sw-correct-btn');

    swHide('sw-error');
    swHide('sw-result');
    swShow('sw-loading');
    btn.disabled = true;

    const resp = await sendMsg({ action: 'correct', text, tone });

    swHide('sw-loading');
    btn.disabled = false;

    if (!resp || resp.error) {
      panel.querySelector('#sw-error').textContent = resp?.error || 'Extension error. Please try again.';
      swShow('sw-error');
      return;
    }

    if (resp.ok) {
      const d = resp.data;
      panel.querySelector('#sw-corrected').textContent = d.corrected_text;
      panel.querySelector('#sw-detected').textContent  = `Detected: ${d.detected_tone}`;
      panel.querySelector('#sw-applied').textContent   = `Applied: ${d.applied_tone}`;
      panel.querySelector('#sw-summary').textContent   = d.changes_summary;
      swShow('sw-result');
    } else if (resp.status === 401 || resp.status === 403) {
      // Token expired — clear stale token then prompt re-login
      await sendMsg({ action: 'logout' });
      swHide('sw-ui');
      swShow('sw-notauth');
    } else if (resp.status === 503) {
      panel.querySelector('#sw-error').textContent =
        resp.data?.detail || 'AI service temporarily unavailable. Try again shortly.';
      swShow('sw-error');
    } else {
      panel.querySelector('#sw-error').textContent =
        resp.data?.detail || 'Correction failed. Please try again.';
      swShow('sw-error');
    }
  });

  // -----------------------------------------------------------------------
  // Copy button
  // -----------------------------------------------------------------------

  panel.querySelector('#sw-copy-btn').addEventListener('click', () => {
    const text = panel.querySelector('#sw-corrected').textContent;
    navigator.clipboard.writeText(text).then(() => {
      const btn = panel.querySelector('#sw-copy-btn');
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    }).catch(() => {});
  });

  // -----------------------------------------------------------------------
  // Selection → FAB
  // -----------------------------------------------------------------------

  // Store selected text on the element so the click handler can read it.
  let _pendingText = '';

  document.addEventListener('mouseup', (e) => {
    // Ignore clicks inside our own UI.
    if (panel.contains(e.target) || fab.contains(e.target)) return;

    // Defer slightly so the selection is fully committed.
    setTimeout(() => {
      const sel  = window.getSelection();
      const text = sel ? sel.toString().trim() : '';

      if (text.length > 5) {
        const range = sel.getRangeAt(0);
        const rect  = range.getBoundingClientRect();

        // Position FAB just below the end of the selection, within viewport.
        let top  = rect.bottom + 8;
        let left = Math.min(rect.right, window.innerWidth - 42);
        if (top + 36 > window.innerHeight) top = rect.top - 42;

        fab.style.top  = `${top}px`;
        fab.style.left = `${left}px`;
        fab.style.display = 'flex';
        _pendingText = text;
      } else if (!panel.classList.contains('sw-open')) {
        fab.style.display = 'none';
      }
    }, 10);
  });

  // Hide FAB when clicking elsewhere (not on panel or FAB).
  document.addEventListener('mousedown', (e) => {
    if (!fab.contains(e.target) && !panel.contains(e.target)) {
      fab.style.display = 'none';
    }
  });

  fab.addEventListener('click', (e) => {
    e.stopPropagation();
    fab.style.display = 'none';
    openPanel(_pendingText);
  });
}
