'use strict';

const DEFAULT_API_BASE = 'http://localhost:8000';

// Keep the message channel open for async responses.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  dispatch(msg)
    .then(sendResponse)
    .catch(err => sendResponse({ ok: false, error: err.message }));
  return true;
});

async function dispatch(msg) {
  switch (msg.action) {
    case 'getConfig':   return getConfig();
    case 'setApiBase':  return setApiBase(msg.apiBase);
    case 'login':       return login(msg.email, msg.password);
    case 'register':    return register(msg.email, msg.password);
    case 'logout':      return logout();
    case 'correct':     return correct(msg.text, msg.tone);
    case 'history':     return history(msg.limit, msg.offset);
    case 'analytics':   return analytics();
    default:
      throw new Error(`Unknown action: ${msg.action}`);
  }
}

// --- Storage helpers ---

async function getApiBase() {
  const { apiBase } = await chrome.storage.local.get('apiBase');
  return apiBase || DEFAULT_API_BASE;
}

async function setApiBase(url) {
  await chrome.storage.local.set({ apiBase: url.replace(/\/$/, '') });
  return { ok: true };
}

async function getConfig() {
  const { token, apiBase, userEmail } = await chrome.storage.local.get(['token', 'apiBase', 'userEmail']);
  return {
    token: token || null,
    apiBase: apiBase || DEFAULT_API_BASE,
    userEmail: userEmail || '',
  };
}

async function logout() {
  await chrome.storage.local.remove(['token', 'userEmail']);
  return { ok: true };
}

// --- API fetch ---

async function apiFetch(path, method, body, token) {
  const base = await getApiBase();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body !== null) opts.body = JSON.stringify(body);

  const res = await fetch(`${base}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

// --- Auth ---

async function login(email, password) {
  const result = await apiFetch('/api/login', 'POST', { email, password }, null);
  if (result.ok) {
    await chrome.storage.local.set({
      token: result.data.access_token,
      userEmail: email,
    });
  }
  return result;
}

async function register(email, password) {
  const result = await apiFetch('/api/register', 'POST', { email, password }, null);
  if (result.ok) {
    await chrome.storage.local.set({
      token: result.data.access_token,
      userEmail: email,
    });
  }
  return result;
}

// --- Correction ---

async function correct(text, tone) {
  const { token } = await chrome.storage.local.get('token');
  return apiFetch('/api/correct', 'POST', { text, tone }, token);
}

async function history(limit = 10, offset = 0) {
  const { token } = await chrome.storage.local.get('token');
  return apiFetch(`/api/history?limit=${limit}&offset=${offset}`, 'GET', null, token);
}

async function analytics() {
  const { token } = await chrome.storage.local.get('token');
  return apiFetch('/api/analytics', 'GET', null, token);
}
