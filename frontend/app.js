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
    btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:18px;">check</span> Copied!';
    setTimeout(() => {
      btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:18px;">content_copy</span> Copy';
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

  const toneColors = {
    formal:       { bg: 'rgba(210,187,255,0.15)', text: '#d2bbff', border: 'rgba(210,187,255,0.25)' },
    casual:       { bg: 'rgba(76,215,246,0.15)',  text: '#4cd7f6', border: 'rgba(76,215,246,0.25)'  },
    friendly:     { bg: 'rgba(255,183,132,0.15)', text: '#ffb784', border: 'rgba(255,183,132,0.25)' },
    professional: { bg: 'rgba(210,187,255,0.15)', text: '#d2bbff', border: 'rgba(210,187,255,0.25)' },
  };
  const c = toneColors[item.tone] || { bg:'rgba(255,255,255,0.08)', text:'#ccc3d8', border:'rgba(255,255,255,0.12)' };

  const div = document.createElement('div');
  div.className = 'glass-card rounded-2xl p-6';
  div.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;">
      <span style="padding:4px 12px;border-radius:9999px;font-size:10px;letter-spacing:0.15em;font-weight:700;text-transform:uppercase;
                   background:${c.bg};color:${c.text};border:1px solid ${c.border};">${esc(item.tone)}</span>
      <span style="font-size:12px;color:#9991CC;">${esc(date)}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div>
        <p style="font-size:10px;letter-spacing:0.15em;font-weight:700;text-transform:uppercase;color:#9991CC;margin-bottom:8px;">Original</p>
        <div style="padding:16px;border-radius:12px;background:rgba(13,13,26,0.5);border:1px solid rgba(255,255,255,0.06);font-size:14px;color:#ccc3d8;line-height:1.6;font-style:italic;">${snip(item.original_text, 200)}</div>
      </div>
      <div>
        <p style="font-size:10px;letter-spacing:0.15em;font-weight:700;text-transform:uppercase;color:${c.text};margin-bottom:8px;">Corrected</p>
        <div style="padding:16px;border-radius:12px;background:${c.bg};border:1px solid ${c.border};font-size:14px;color:#e3e0f4;line-height:1.6;">${snip(item.corrected_text, 200)}</div>
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
    <div style="display:flex;justify-content:center;padding:24px;">
      <div class="spin-ring" style="width:1.5rem;height:1.5rem;border-width:3px;"></div>
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
      breakdown.innerHTML = '<p style="color:#9991CC;text-align:center;padding:16px 0;">No data yet.</p>';
      return;
    }
    const max = data.corrections_per_tone[0].count;
    const barColors = { formal:'#d2bbff', casual:'#4cd7f6', friendly:'#ffb784', professional:'#d2bbff' };
    breakdown.innerHTML = data.corrections_per_tone.map(tc => {
      const color = barColors[tc.tone] || '#d2bbff';
      const pct   = Math.round(tc.count / max * 100);
      return `
        <div style="margin-bottom:28px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:12px;letter-spacing:0.12em;font-weight:600;text-transform:uppercase;color:#e3e0f4;">${esc(tc.tone)}</span>
            <span style="font-size:12px;letter-spacing:0.12em;font-weight:600;color:${color};">${tc.count}</span>
          </div>
          <div style="height:10px;border-radius:9999px;background:rgba(255,255,255,0.06);overflow:hidden;">
            <div style="height:100%;border-radius:9999px;width:${pct}%;
                        background:linear-gradient(90deg,${color}99,${color});
                        transition:width 1.4s cubic-bezier(0.22,1,0.36,1);"></div>
          </div>
        </div>`;
    }).join('');
  } catch {
    document.getElementById('tone-breakdown').innerHTML =
      '<p style="color:#ffb4ab;font-size:14px;">Could not load analytics.</p>';
  }
}

// ---------------------------------------------------------------------------
// Service Worker registration
// ---------------------------------------------------------------------------

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch((err) => {
      console.error('Service Worker registration failed:', err);
    });
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

init();
