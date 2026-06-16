# SmartWrite — Progress Log

## How to use this file

- **Start of session:** read this whole file, then check
  `git log --oneline -10` to see what actually landed.
- **End of session:** move finished items from "Next up" into "Done" (one
  line, dated), add anything you learned to "Known issues," and commit.

## Done

No completed items yet — update this as work lands.

## Next up (in order)

1. [ ] Backend skeleton: FastAPI app, SQLAlchemy async setup against local
   SQLite, Alembic initialized.
2. [ ] User model + JWT auth: `/api/register`, `/api/login`, PBKDF2-SHA256
   hashing.
3. [ ] `/api/correct` (protected): Groq integration, tone detection +
   rewrite + grammar correction, graceful handling of Groq downtime/rate
   limits.
4. [ ] `CorrectionHistory` model with encrypted `original_text` /
   `corrected_text` (Fernet, key from `HISTORY_ENCRYPTION_KEY`); save on
   every `/api/correct` call.
5. [ ] `/api/history` + basic analytics endpoint (most-used tone,
   correction frequency).
6. [ ] PWA frontend: Bootstrap UI, installable manifest + service worker,
   wired to the backend.
7. [ ] Chrome extension: MV3 manifest, selection-capture content script,
   floating action button, popup, wired to the backend.
8. [ ] Deploy: Render web service + Render free Postgres, env vars set,
   CORS configured for the PWA and extension origins.
9. [ ] Polish: README with setup instructions + screenshots, a basic
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

## Decisions log

- 2026-06-16 — AI engine: Groq primary, HF Inference Providers as
  documented fallback (verify live model before use).
- 2026-06-16 — Production DB: Render free Postgres, accepting the 30-day
  reset as a known operational task rather than switching engines.
- 2026-06-16 — Encryption: field-level encryption (Fernet) on correction
  history text fields is in MVP scope, not deferred.
