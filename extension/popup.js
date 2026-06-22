'use strict';

const $ = id => document.getElementById(id);

// ---------------------------------------------------------------------------
// Messaging
// ---------------------------------------------------------------------------

function send(msg) {
  return new Promise(resolve => chrome.runtime.sendMessage(msg, resolve));
}

// ---------------------------------------------------------------------------
// Show / hide
// ---------------------------------------------------------------------------

function hide(id) { $(id).classList.add('hidden'); }
function show(id) { $(id).classList.remove('hidden'); }

// ---------------------------------------------------------------------------
// Init — check stored token and route to the right view
// ---------------------------------------------------------------------------

async function init() {
  const { token, apiBase, userEmail } = await send({ action: 'getConfig' });
  hide('loading-view');

  $('api-base-input').value = apiBase;

  if (token) {
    $('user-email').textContent = userEmail;
    show('app-view');
  } else {
    show('auth-view');
  }
}

// ---------------------------------------------------------------------------
// Tab switching (Sign In / Sign Up)
// ---------------------------------------------------------------------------

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === tab)
    );
    $('tab-login').classList.toggle('hidden', tab !== 'login');
    $('tab-register').classList.toggle('hidden', tab !== 'register');
  });
});

// ---------------------------------------------------------------------------
// Shared auth handler (login + register share identical flow)
// ---------------------------------------------------------------------------

async function handleAuth(action, emailId, passwordId, spinnerId, btnId, errorId) {
  hide(errorId);
  const email    = $(emailId).value.trim();
  const password = $(passwordId).value;
  if (!email || !password) return;

  $(spinnerId).classList.remove('hidden');
  $(btnId).disabled = true;

  const resp = await send({ action, email, password });

  $(spinnerId).classList.add('hidden');
  $(btnId).disabled = false;

  if (resp && resp.ok) {
    const { apiBase, userEmail } = await send({ action: 'getConfig' });
    $('api-base-input').value = apiBase;
    $('user-email').textContent = userEmail;
    hide('auth-view');
    show('app-view');
  } else {
    const fallback = action === 'login'
      ? 'Login failed. Check your credentials.'
      : 'Registration failed. Try a different email.';
    $(errorId).textContent = resp?.data?.detail || fallback;
    show(errorId);
  }
}

$('login-btn').addEventListener('click', () =>
  handleAuth('login', 'login-email', 'login-password', 'login-spinner', 'login-btn', 'login-error')
);
$('reg-btn').addEventListener('click', () =>
  handleAuth('register', 'reg-email', 'reg-password', 'reg-spinner', 'reg-btn', 'reg-error')
);

// Enter key triggers submit on both password fields
$('login-password').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('login-btn').click();
});
$('reg-password').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('reg-btn').click();
});

// ---------------------------------------------------------------------------
// Sign Out
// ---------------------------------------------------------------------------

$('logout-btn').addEventListener('click', async () => {
  await send({ action: 'logout' });
  $('input-text').value    = '';
  $('char-count').textContent = '0';
  hide('result-card');
  hide('correct-error');
  hide('app-view');
  show('auth-view');
});

// ---------------------------------------------------------------------------
// Text correction
// ---------------------------------------------------------------------------

$('input-text').addEventListener('input', () => {
  $('char-count').textContent = $('input-text').value.length;
});

$('correct-btn').addEventListener('click', async () => {
  const text = $('input-text').value.trim();
  if (!text) return;

  const tone = $('tone-select').value || null;

  hide('correct-error');
  hide('result-card');
  $('correct-spinner').classList.remove('hidden');
  $('correct-btn').disabled = true;

  const resp = await send({ action: 'correct', text, tone });

  $('correct-spinner').classList.add('hidden');
  $('correct-btn').disabled = false;

  if (!resp || resp.error) {
    $('correct-error').textContent = resp?.error || 'Extension error. Please try again.';
    show('correct-error');
    return;
  }

  if (resp.ok) {
    const d = resp.data;
    $('corrected-text').textContent  = d.corrected_text;
    $('result-detected').textContent = `detected: ${d.detected_tone}`;
    $('result-applied').textContent  = `applied: ${d.applied_tone}`;
    $('result-summary').textContent  = d.changes_summary;

    if (d.warning) {
      $('result-warning').textContent = d.warning;
      show('result-warning');
    } else {
      hide('result-warning');
    }
    show('result-card');
  } else if (resp.status === 401 || resp.status === 403) {
    // Token expired — force re-login
    await send({ action: 'logout' });
    hide('app-view');
    show('auth-view');
  } else if (resp.status === 429) {
    $('correct-error').textContent = 'Rate limit reached. Please wait a moment and try again.';
    show('correct-error');
  } else if (resp.status === 503) {
    $('correct-error').textContent =
      resp.data?.detail || 'AI service temporarily unavailable. Try again shortly.';
    show('correct-error');
  } else {
    $('correct-error').textContent =
      resp.data?.detail || 'Correction failed. Please try again.';
    show('correct-error');
  }
});

// ---------------------------------------------------------------------------
// Copy corrected text
// ---------------------------------------------------------------------------

$('copy-btn').addEventListener('click', () => {
  const text = $('corrected-text').textContent;
  navigator.clipboard.writeText(text).then(() => {
    $('copy-btn').textContent = 'Copied!';
    setTimeout(() => { $('copy-btn').textContent = 'Copy'; }, 2000);
  }).catch(() => {});
});

// ---------------------------------------------------------------------------
// API base URL
// ---------------------------------------------------------------------------

$('save-api-base').addEventListener('click', async () => {
  const url = $('api-base-input').value.trim();
  if (!url) return;

  // Quick client-side format check before hitting the background.
  try {
    const p = new URL(url);
    if (p.protocol !== 'http:' && p.protocol !== 'https:') throw new Error();
  } catch {
    $('save-api-base').textContent = 'Invalid URL';
    setTimeout(() => { $('save-api-base').textContent = 'Save'; }, 3000);
    return;
  }

  const resp = await send({ action: 'setApiBase', apiBase: url });
  if (resp && !resp.ok) {
    $('save-api-base').textContent = resp.error || 'Invalid URL';
    setTimeout(() => { $('save-api-base').textContent = 'Save'; }, 3000);
  } else {
    $('save-api-base').textContent = 'Saved!';
    setTimeout(() => { $('save-api-base').textContent = 'Save'; }, 2000);
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

init();
