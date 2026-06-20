# SmartWrite — Progress Log

## How to use this file

- **Start of session:** read this whole file, then check
  `git log --oneline -10` to see what actually landed.
- **End of session:** move finished items from "Next up" into "Done" (one
  line, dated), add anything you learned to "Known issues," and commit.

## Done

- 2026-06-16 — Backend skeleton landed (PROGRESS item 1): `backend/` package
  with `config.py` (pydantic-settings, reads root `.env`), `database.py`
  (async SQLAlchemy engine/session/Base from `DATABASE_URL`), and `main.py`
  (FastAPI app + `/health` endpoint that pings the DB). Alembic wired for
  async (`backend/alembic/env.py` pulls the URL from settings); empty baseline
  revision `d5e215216942` applied. `requirements.txt` + `.env.example` added.
  Smoke-tested: app imports, `alembic upgrade head` works, `GET /health` -> 200.

- 2026-06-17 — User model + JWT auth (PROGRESS item 2): `User` ORM model
  (`backend/app/models/user.py`); Pydantic schemas in `backend/app/schemas/auth.py`;
  `backend/app/auth.py` — PBKDF2-SHA256 hashing via stdlib `hashlib.pbkdf2_hmac`
  (avoids passlib/Python 3.13+ compat issues), PyJWT HS256 token mint, and
  `get_current_user` Bearer dependency; `backend/app/routers/auth.py` —
  `POST /api/register` (201, issues token) and `POST /api/login` (200, issues
  token). Alembic revision `fc7642e3fc7a` (add_users_table) applied. Added
  `PyJWT==2.10.1` + `email-validator==2.2.0` to `requirements.txt`.
  Smoke-tested: register 201, duplicate 409, login OK 200, login bad password
  401, health 200.

- 2026-06-17 — Groq `/api/correct` endpoint (PROGRESS item 3):
  `backend/app/groq_client.py` — async httpx calls to Groq's OpenAI-compatible
  endpoint, exponential backoff (1s/2s/4s) on 429 and 5xx, friendly
  `GroqUnavailableError` on all failure paths (never surfaces raw stack traces),
  JSON-mode response parsing with key validation, empty-key guard.
  `backend/app/schemas/correct.py` — `CorrectRequest` (text 1–5000 chars,
  optional tone field validated against VALID_TONES) and `CorrectResponse`.
  `backend/app/routers/correct.py` — `POST /api/correct` (JWT-protected via
  `get_current_user`; 503 on Groq issues). Router registered in `main.py`.
  No new pip packages required (httpx was already in requirements.txt).
  Smoke-tested: formal-tone correction OK, no-tone (AI picks friendly) OK,
  invalid tokens rejected with 401, invalid tone 422.

- 2026-06-18 — PWA frontend (PROGRESS item 5):
  `backend/app/auth.py` — `get_current_user` now accepts either an httpOnly
  cookie (`smartwrite_token`) or an `Authorization: Bearer` header, so the
  PWA and the Chrome extension use separate storage paths as spec'd in CLAUDE.md.
  `HTTPBearer(auto_error=False)` prevents a 403 when no header is present.
  `backend/app/routers/auth.py` — `POST /api/register` and `POST /api/login`
  both set the httpOnly `smartwrite_token` cookie (`samesite=lax`,
  `secure=not DEBUG`) in addition to returning the JSON token body.
  Added `POST /api/logout` (clears cookie) and `GET /api/me` (returns
  `{id, email}` — used by the PWA to check auth state on page load).
  `backend/app/main.py` — mounts `frontend/` as `StaticFiles(html=True)` at
  `/` after all API routers (guard: only if the directory exists).
  `frontend/index.html` — SPA with Bootstrap 5 + Bootstrap Icons; loading
  overlay, auth view (Sign In / Sign Up tabs), app view (Write / History /
  Analytics tabs).
  `frontend/app.js` — vanilla JS; async `init()` calls `/api/me` to resolve
  auth state; cookie-based fetch (`credentials:'include'`) for all API calls;
  char counter, tone selector, result display with copy button, paginated
  history, analytics stat cards + progress bar tone breakdown.
  `frontend/manifest.json` — PWA manifest (name, SVG icon, standalone display).
  `frontend/sw.js` — service worker: cache-first for static assets,
  network-only for `/api/*`; `skipWaiting` + `clients.claim` for instant activation.
  `frontend/icon.svg` — indigo "W" on rounded square.
  `.env.example` — updated: `DEBUG=true` documented for local HTTP cookie dev.
  Smoke-tested: auth view renders, cookie login/logout cycle works, Write/
  History/Analytics tabs all load with correct data; unauthenticated paths
  redirect to auth view.

- 2026-06-18 — History + analytics endpoints (PROGRESS item 4):
  `backend/app/schemas/history.py` — `HistoryItem`, `HistoryResponse`,
  `ToneCount`, `AnalyticsResponse` Pydantic schemas.
  `backend/app/routers/history.py` — `GET /api/history` (paginated,
  decrypts text fields, newest-first; `limit`/`offset` query params) and
  `GET /api/analytics` (total corrections, per-tone breakdown ordered by
  count desc, most-used tone, corrections in last 7 days — all aggregated
  from unencrypted `tone`/`created_at` columns per CLAUDE.md design).
  Both endpoints are JWT-protected; token validation failures return 401.
  Router registered in `main.py`. No new migration needed.
  Smoke-tested: history returns decrypted items + total; analytics returns
  correct counts; invalid tokens rejected with 401.

- 2026-06-18 — CorrectionHistory model + encrypted history save (PROGRESS item 3 continued):
  `backend/app/encryption.py` — Fernet encrypt/decrypt helpers; key loaded from
  `HISTORY_ENCRYPTION_KEY` env var, raises `RuntimeError` if missing (fail loudly).
  `backend/app/models/history.py` — `CorrectionHistory` ORM model: `original_text`
  and `corrected_text` stored as `LargeBinary` (Fernet bytes); `tone` and
  `detected_tone` stored unencrypted for analytics. FK to `users.id` with CASCADE.
  `backend/alembic/versions/20260618_8e3f920c1a74_add_correction_history_table.py`
  — Alembic migration for the new table; applied.
  `backend/app/routers/correct.py` updated — injects `db` session, saves a
  `CorrectionHistory` record (encrypted) after every successful Groq call.
  `cryptography==44.0.2` added to `requirements.txt`. `.env.example` recreated.
  Fixed `HISTORY_ENCRYPTION_KEY` in `.env` — replaced broken 64-char hex string
  with a valid Fernet key generated by `Fernet.generate_key()`.
  Smoke-tested: Fernet round-trip OK; imports clean; migration applied cleanly.

- 2026-06-21 — Bug fixes + pytest suite (PROGRESS item 8 partial):
  **Bug 1 fixed — wrong uvicorn command:**
  Running `uvicorn app.main:app` from `SmartWrite/` causes
  `ModuleNotFoundError: No module named 'app'` because Python looks for a
  top-level `app` package. The backend lives at `backend/app/main.py`, so the
  correct module path is `backend.app.main`. Always run from the project root:
  `uvicorn backend.app.main:app --reload --port 8000`.
  **Bug 2 fixed — retry off-by-one in `backend/app/groq_client.py`:**
  `max_retries = 3`, `max_attempts = max_retries + 1 = 4`. The loop runs on
  indices 0, 1, 2, 3. Three `if attempt == max_retries - 1:` checks (one per
  error branch: ConnectError, 429, 5xx) all evaluated as `if attempt == 2:`,
  which caused them to raise on the 3rd attempt — never reaching the 4th.
  Fixed to `if attempt >= max_retries:` (i.e. `>= 3`), so all 4 attempts
  fire before giving up. Log format strings also corrected from `max_retries`
  → `max_attempts` so "attempt X/4" displays correctly.
  **pytest suite added — 55 tests, all green (5.2 s):**
  `tests/conftest.py` — sets env vars before any backend import (so
  lru_cached Settings + Fernet pick up test values), creates a temp-file
  SQLite DB with NullPool (avoids event-loop-binding issues with aiosqlite),
  overrides `get_db` in the ASGI test client.
  `tests/test_auth_utils.py` (11 tests) — hash format, verify correct/wrong/
  malformed, JWT decode, expiry, wrong-secret rejection.
  `tests/test_encryption.py` (7 tests) — ASCII + Unicode round-trips, empty
  string, nondeterminism, wrong-key InvalidToken, corrupted ciphertext.
  `tests/test_groq_client.py` (13 tests) — tone validation, missing API key,
  happy path, retry count regression (asserts call_count == 4, catches the
  off-by-one bug if it reappears), success-after-retry, malformed JSON.
  `tests/test_api.py` (24 tests) — all endpoints end-to-end: register,
  login, me, logout, correct (Groq mocked), history (paginated), analytics.
  `pytest.ini` — `asyncio_mode = auto` (pytest-asyncio 1.4.0 installed).
  `requirements.txt` — added `pytest>=8.3.0` + `pytest-asyncio>=0.24.0`.
  Full details + learning notes: see `LEARNINGS.md`.

## Next up (in order)

1. [x] User model + JWT auth: `/api/register`, `/api/login`, PBKDF2-SHA256
   hashing. ✓ Done 2026-06-17
2. [x] `/api/correct` (protected): Groq integration, tone detection +
   rewrite + grammar correction, graceful handling of Groq downtime/rate
   limits. ✓ Done 2026-06-17
3. [x] `CorrectionHistory` model with encrypted `original_text` /
   `corrected_text` (Fernet, key from `HISTORY_ENCRYPTION_KEY`); save on
   every `/api/correct` call. ✓ Done 2026-06-18
4. [x] `/api/history` + basic analytics endpoint (most-used tone,
   correction frequency). ✓ Done 2026-06-18
5. [x] PWA frontend: Bootstrap UI, installable manifest + service worker,
   wired to the backend. ✓ Done 2026-06-18
6. [ ] Chrome extension: MV3 manifest, selection-capture content script,
   floating action button, popup, wired to the backend.
7. [ ] Deploy: Render web service + Render free Postgres, env vars set,
   CORS configured for the PWA and extension origins.
8. [x] pytest suite (55 tests, all green) + two production bugs fixed. ✓ Done 2026-06-21

## Known issues / operational reminders

- Render's free Postgres instance auto-deletes 30 days after creation —
  recreate it and rerun Alembic migrations before that date, or data is
  lost.
- Groq free tier: ~30 requests/min, ~1,000/day per model — expect
  occasional 429s under any real testing load; backoff is implemented in
  step 3 above, not optional.
- HF fallback model: re-verify it's live on huggingface.co before relying
  on it — don't assume a model that worked last month still does.
- ~~The current `HISTORY_ENCRYPTION_KEY` in `.env` was a 64-char hex string.~~
  Fixed 2026-06-18 — `.env` now holds a valid Fernet base64 key.
- Local env runs Python 3.14: a few packages have no prebuilt wheels at older
  pins and try to compile from C source (needs MSVC, which isn't installed).
  Pin versions that ship cp314 wheels (e.g. greenlet>=3.5.1, asyncpg>=0.31.0).
- **Environment Notice (Added 2026-06-18)**: `cryptography>=48.0.0` (introduced below on [2026-06-18](#done)) requires **Python 3.9+** and **OpenSSL 3.0+**. Ensure deployment environments (e.g., Render, CI) meet these minimums.

## Decisions log

- 2026-06-16 — AI engine: Groq primary, HF Inference Providers as
  documented fallback (verify live model before use).
- 2026-06-16 — Production DB: Render free Postgres, accepting the 30-day
  reset as a known operational task rather than switching engines.
- 2026-06-16 — Encryption: field-level encryption (Fernet) on correction
  history text fields is in MVP scope, not deferred.
