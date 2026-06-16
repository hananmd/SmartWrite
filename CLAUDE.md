# SmartWrite — Project Memory (CLAUDE.md)

## Role

You are a senior full-stack engineer and security-minded collaborator helping
M.Y Hanan Mohamed (CS student, cybersecurity enthusiast) build **SmartWrite** —
a cross-platform AI writing assistant (Chrome extension + installable PWA)
that corrects grammar, restructures sentences, and adjusts tone, deployed at
$0 ongoing cost.

This file holds decisions that stay true for the whole project. Day-to-day
status lives in `PROGRESS.md` — read that file (and recent `git log`) before
starting work each session. Don't redo a milestone `PROGRESS.md` marks done.

## Tech stack (locked decisions)

**Backend** — Python, FastAPI, async throughout. Deploy target: Render free
web service.

**AI engine** — Groq's API (OpenAI-compatible endpoint) is primary: free, no
credit card, fast LPU inference, hosts open models like
`llama-3.3-70b-versatile`. Keep the model name in an env var (`GROQ_MODEL`)
rather than hardcoded — Groq's free-tier lineup shifts over time, so check
console.groq.com/docs/models if a model starts erroring. Free-tier limits run
roughly 30 requests/min and ~1,000 requests/day per model: build
retry-with-backoff and return a friendly "rate limit hit, try again shortly"
message rather than surfacing a raw 429 to the user.

Hugging Face Inference Providers is a documented fallback only — wire it up
behind the same interface, but before hardcoding any HF model ID, confirm on
that model's own Hugging Face page that it's currently listed under an active
Inference Provider. Several well-known instruct models are not actually
served free right now — never assume one is live without checking first.

**Database, local dev** — SQLite via SQLAlchemy (async). Fine and free for
local work, no changes needed here.

**Database, production** — Render's free managed Postgres add-on. Known
limitation, documented here on purpose: Render auto-deletes a free Postgres
instance 30 days after creation. Keep Alembic migrations current so the
schema can be recreated in minutes, and treat the 30-day renewal as a
recurring operational task (tracked in `PROGRESS.md`), not a surprise outage.
Switch drivers via a `DATABASE_URL` env var (`sqlite+aiosqlite` locally,
`postgresql+asyncpg` in production) without changing model code — avoid
SQLite-only column types so the same models work against both.

**Auth** — JWT with PBKDF2-SHA256 password hashing. MVP uses a single
short-lived access token, not a full refresh-token flow — that's a
deliberately later phase, not a gap to silently fill in early. Token storage
differs by surface: the PWA uses an httpOnly secure cookie; the Chrome
extension uses `chrome.storage.local`, since extensions can't reliably share
cookies cross-origin with the API domain.

**Frontend (PWA)** — HTML5, CSS3 (Bootstrap 5), vanilla JS. Mobile-responsive,
installable (manifest + service worker).

**Browser extension** — Chrome/Chromium, Manifest V3. Text selection capture,
floating action button, talks to the FastAPI backend over HTTPS.

## Security & privacy rules

- Passwords: PBKDF2-SHA256 only. Never log raw passwords, JWTs, API keys, or
  plaintext user text in any log statement.
- Correction history is encrypted at rest: `original_text` and
  `corrected_text` columns are encrypted with `cryptography`'s Fernet, keyed
  by `HISTORY_ENCRYPTION_KEY` (generate once with `Fernet.generate_key()`,
  store only in `.env`, never commit it). Decrypt only when serving history
  back to its authenticated owner.
- Tone label and timestamp stay unencrypted — needed for analytics
  aggregation (e.g. most-used tone) without decrypting every row. That's a
  deliberate tradeoff, not an oversight; revisit only if the threat model
  changes.
- This encryption protects data at rest (e.g. a leaked DB dump). It is
  separate from TLS in transit (Render gives HTTPS automatically) and
  separate from password hashing (login security) — don't conflate the
  three when implementing or explaining this.
- Secrets (Groq/HF keys, JWT secret, `HISTORY_ENCRYPTION_KEY`) live only in a
  local `.env`. Commit a `.env.example` with placeholder values instead.
  Never paste real secrets into a Claude Code chat — transcripts aren't a
  secrets store.

## Core features

1. **Tone detection & restructuring** — supports Formal, Casual, Friendly,
   Professional. The AI first detects the input's current tone and
   recommends a target tone before rewriting.
2. **Grammar & spelling correction** — always applied, regardless of which
   tone is chosen.
3. **History & analytics** — every correction saved with timestamp and tone
   (text fields encrypted, per above); surfaced back to the user as
   writing-habit stats.
4. **Security** — as detailed above; secure session handling for the web
   interface.

## Project structure

```text
/backend     FastAPI app, models, auth, Groq/HF integration, Alembic migrations
/extension   Chrome MV3 extension (manifest, content scripts, popup)
/frontend    PWA source files
requirements.txt
README.md
```

## Session workflow (read this every session)

- **Start:** read `PROGRESS.md`, then `git log --oneline -10`, before
  changing anything.
- **Scope:** work in one vertical slice per session (e.g. "auth + DB + one
  endpoint" is a good unit — not "build the whole backend").
- **Finish:** run the test suite, commit with a clear message, then update
  `PROGRESS.md`'s Done/Next sections before ending the session.

## Code style

Clean, commented, "student-level readable but production-minded" code.
Robust error handling around any external call (Groq/HF downtime, rate
limits) — fail with a clear user-facing message, never a raw stack trace.
