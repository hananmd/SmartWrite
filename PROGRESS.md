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

## Next up (in order)

1. [x] User model + JWT auth: `/api/register`, `/api/login`, PBKDF2-SHA256
   hashing. ✓ Done 2026-06-17
2. [ ] `/api/correct` (protected): Groq integration, tone detection +
   rewrite + grammar correction, graceful handling of Groq downtime/rate
   limits. — **Next up**
3. [ ] `CorrectionHistory` model with encrypted `original_text` /
   `corrected_text` (Fernet, key from `HISTORY_ENCRYPTION_KEY`); save on
   every `/api/correct` call.
4. [ ] `/api/history` + basic analytics endpoint (most-used tone,
   correction frequency).
5. [ ] PWA frontend: Bootstrap UI, installable manifest + service worker,
   wired to the backend.
6. [ ] Chrome extension: MV3 manifest, selection-capture content script,
   floating action button, popup, wired to the backend.
7. [ ] Deploy: Render web service + Render free Postgres, env vars set,
   CORS configured for the PWA and extension origins.
8. [ ] Polish: README with setup instructions + screenshots, a basic
   pytest suite, final error-handling pass.

## Known issues / operational reminders

- Render's free Postgres instance auto-deletes 30 days after creation —
  recreate it and rerun Alembic migrations before that date, or data is
  lost.
- Groq free tier: ~30 requests/min, ~1,000/day per model — expect
  occasional 429s under any real testing load; backoff is implemented in
  step 3 above, not optional.
- HF fallback model: re-verify it's live on huggingface.co before relying
  on it — don't assume a model that worked last month still does.
- The current `HISTORY_ENCRYPTION_KEY` in `.env` is a 64-char hex string, but
  Fernet expects a base64 key from `Fernet.generate_key()`. Regenerate it the
  correct way before wiring up encryption (item 3, the `CorrectionHistory`
  work), or Fernet will reject it.
- Local env runs Python 3.14: a few packages have no prebuilt wheels at older
  pins and try to compile from C source (needs MSVC, which isn't installed).
  Pin versions that ship cp314 wheels (e.g. greenlet>=3.5.1, asyncpg>=0.31.0).

## Decisions log

- 2026-06-16 — AI engine: Groq primary, HF Inference Providers as
  documented fallback (verify live model before use).
- 2026-06-16 — Production DB: Render free Postgres, accepting the 30-day
  reset as a known operational task rather than switching engines.
- 2026-06-16 — Encryption: field-level encryption (Fernet) on correction
  history text fields is in MVP scope, not deferred.
