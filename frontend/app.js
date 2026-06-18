'use strict';

const API = '';           // same origin — no prefix needed
const HISTORY_LIMIT = 10;

let historyOffset = 0;
let historyTotal  = 0;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function hide(id) { document.getElementById(id).classList.add('d-none'); }
function show(id) { document.getElementById(id).classList.remove('d-none'); }

// ---------------------------------------------------------------------------
// Auth state
// ---------------------------------------------------------------------------

async function init() {
  try {
    const res = await fetch(`${API}/api/me`, { credentials: 'include' });
    if (res.ok) {
      const { email } = await res.json();
      enterApp(email);
    } else {
      enterAuth();
    }
  } catch {
    enterAuth();
  } finally {
    hide('loading-overlay');
  }
}

function enterAuth() {
  hide('app-view');
  show('auth-view');
}

function enterApp(email) {
  hide('auth-view');
  show('app-view');
  if (email) document.getElementById('user-email').textContent = email;
  // Reset to Write tab whenever we enter the app view
  switchTab('write');
}

// ---------------------------------------------------------------------------
// Auth forms
// ---------------------------------------------------------------------------

function setAuthError(msg) {
  const el = document.getElementById('auth-error');
  if (msg) { el.textContent = msg; show('auth-error'); }
  else       { hide('auth-error'); }
}

async function submitAuth(url, body, emailId, spinnerId, btnId) {
  setAuthError('');
  const email   = document.getElementById(emailId).value;
  const spinner = document.getElementById(spinnerId);
  const btn     = document.getElementById(btnId);

  spinner.classList.remove('d-none');
  btn.disabled = true;
  try {
    const res = await fetch(`${API}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'include',
    });
    if (res.ok) {
      enterApp(email);
    } else {
      const data = await res.json().catch(() => ({}));
      setAuthError(data.detail || 'Request failed. Please try again.');
    }
  } catch {
    setAuthError('Network error. Please check your connection.');
  } finally {
    spinner.classList.add('d-none');
    btn.disabled = false;
  }
}

document.getElementById('login-form').addEventListener('submit', (e) => {
  e.preventDefault();
  submitAuth('/api/login', {
    email:    document.getElementById('login-email').value,
    password: document.getElementById('login-password').value,
  }, 'login-email', 'login-spinner', 'login-btn');
});

document.getElementById('register-form').addEventListener('submit', (e) => {
  e.preventDefault();
  submitAuth('/api/register', {
    email:    document.getElementById('reg-email').value,
    password: document.getElementById('reg-password').value,
  }, 'reg-email', 'register-spinner', 'register-btn');
});

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

document.getElementById('logout-btn').addEventListener('click', async () => {
  await fetch(`${API}/api/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
  // Clear form state
  document.getElementById('input-text').value = '';
  document.getElementById('char-count').textContent = '0';
  hide('result-card');
  hide('correct-error');
  enterAuth();
});

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

function switchTab(tab) {
  document.querySelectorAll('#main-tabs .nav-link').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  ['write', 'history', 'analytics'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('d-none', t !== tab);
  });
  if (tab === 'history')   loadHistory(true);
  if (tab === 'analytics') loadAnalytics();
}

document.getElementById('main-tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('[data-tab]');
  if (btn) switchTab(btn.dataset.tab);
});

// ---------------------------------------------------------------------------
// Correction
// ---------------------------------------------------------------------------

document.getElementById('input-text').addEventListener('input', (e) => {
  document.getElementById('char-count').textContent = e.target.value.length;
});

document.getElementById('correct-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = document.getElementById('input-text').value.trim();
  if (!text) return;

  const tone    = document.getElementById('tone-select').value || null;
  const spinner = document.getElementById('correct-spinner');
  const btn     = document.getElementById('correct-btn');

  hide('correct-error');
  hide('result-card');
  spinner.classList.remove('d-none');
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/correct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, tone }),
      credentials: 'include',
    });

    if (res.ok) {
      const data = await res.json();
      showResult(data);
    } else if (res.status === 401 || res.status === 403) {
      enterAuth();
    } else if (res.status === 503) {
      const data = await res.json().catch(() => ({}));
      showCorrectError(data.detail || 'AI service temporarily unavailable. Try again shortly.');
    } else {
      const data = await res.json().catch(() => ({}));
      showCorrectError(data.detail || 'Correction failed. Please try again.');
    }
  } catch {
    showCorrectError('Network error. Please check your connection.');
  } finally {
    spinner.classList.add('d-none');
    btn.disabled = false;
  }
});

function showResult(data) {
  document.getElementById('corrected-text-box').textContent = data.corrected_text;
  document.getElementById('result-detected').textContent = `detected: ${data.detected_tone}`;
  document.getElementById('result-applied').textContent  = `applied: ${data.applied_tone}`;
  document.getElementById('result-summary').textContent  = data.changes_summary;

  const warnEl = document.getElementById('result-warning');
  if (data.warning) { warnEl.textContent = data.warning; show('result-warning'); }
  else               { hide('result-warning'); }

  show('result-card');
}

function showCorrectError(msg) {
  const el = document.getElementById('correct-error');
  el.textContent = msg;
  show('correct-error');
}

document.getElementById('copy-btn').addEventListener('click', () => {
  const text = document.getElementById('corrected-text-box').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
    setTimeout(() => {
      btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy';
    }, 2000);
  }).catch(() => {});
});

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

async function loadHistory(reset = false) {
  if (reset) {
    historyOffset = 0;
    historyTotal  = 0;
    document.getElementById('history-list').innerHTML = '';
    hide('history-empty');
    hide('load-more-footer');
  }

  try {
    const res = await fetch(
      `${API}/api/history?limit=${HISTORY_LIMIT}&offset=${historyOffset}`,
      { credentials: 'include' }
    );
    if (!res.ok) return;
    const data = await res.json();

    historyTotal   = data.total;
    historyOffset += data.items.length;

    if (data.total === 0) { show('history-empty'); return; }

    const list = document.getElementById('history-list');
    data.items.forEach(item => list.appendChild(makeHistoryItem(item)));

    if (historyOffset < historyTotal) show('load-more-footer');
    else                               hide('load-more-footer');
  } catch {
    // Silent — user may be offline or session expired
  }
}

function makeHistoryItem(item) {
  const date = new Date(item.created_at).toLocaleString();
  const snip = (s, n) => esc(s.length > n ? s.slice(0, n) + '…' : s);

  const div = document.createElement('div');
  div.className = 'list-group-item py-3';
  div.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <span class="badge text-capitalize" style="background:#6366f1;">${esc(item.tone)}</span>
      <small class="text-muted">${esc(date)}</small>
    </div>
    <div class="row g-2">
      <div class="col-md-6">
        <div class="text-muted small mb-1">Original</div>
        <div class="bg-light rounded p-2 small" style="line-height:1.5;">${snip(item.original_text, 200)}</div>
      </div>
      <div class="col-md-6">
        <div class="text-muted small mb-1">Corrected</div>
        <div class="bg-light rounded p-2 small" style="border-left:3px solid #6366f1;line-height:1.5;">${snip(item.corrected_text, 200)}</div>
      </div>
    </div>`;
  return div;
}

document.getElementById('refresh-history-btn').addEventListener('click', () => loadHistory(true));
document.getElementById('load-more-btn').addEventListener('click', () => loadHistory(false));

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

async function loadAnalytics() {
  document.getElementById('tone-breakdown').innerHTML = `
    <div class="text-center py-3">
      <div class="spinner-border text-primary spinner-border-sm"></div>
    </div>`;
  document.getElementById('stat-total').textContent    = '—';
  document.getElementById('stat-7d').textContent       = '—';
  document.getElementById('stat-top-tone').textContent = '—';

  try {
    const res = await fetch(`${API}/api/analytics`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-total').textContent    = data.total_corrections;
    document.getElementById('stat-7d').textContent       = data.corrections_last_7_days;
    document.getElementById('stat-top-tone').textContent = data.most_used_tone ?? '—';

    const breakdown = document.getElementById('tone-breakdown');
    if (!data.corrections_per_tone.length) {
      breakdown.innerHTML = '<p class="text-muted mb-0 text-center py-2">No data yet.</p>';
      return;
    }
    const max = data.corrections_per_tone[0].count;
    breakdown.innerHTML = data.corrections_per_tone.map(tc => `
      <div class="mb-3">
        <div class="d-flex justify-content-between mb-1">
          <span class="text-capitalize">${esc(tc.tone)}</span>
          <span class="fw-semibold">${tc.count}</span>
        </div>
        <div class="progress" style="height:8px;">
          <div class="progress-bar" style="background:#6366f1;width:${Math.round(tc.count/max*100)}%;"></div>
        </div>
      </div>`).join('');
  } catch {
    document.getElementById('tone-breakdown').innerHTML =
      '<p class="text-danger small mb-0">Could not load analytics.</p>';
  }
}

// ---------------------------------------------------------------------------
// Service Worker registration
// ---------------------------------------------------------------------------

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

init();
