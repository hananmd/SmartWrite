# SmartWrite

An AI-powered writing assistant that corrects grammar, restructures sentences, and adjusts tone — available as an installable PWA and a Chrome extension, deployed at $0 ongoing cost.

Built with FastAPI + Groq's free LPU inference API (Llama 3.3 70B), deployed on Render's free tier.

---

## Features

- **AI tone rewriting** — detects the current tone of your text and rewrites it as Formal, Casual, Friendly, or Professional
- **Grammar & spelling correction** — applied on every request, regardless of tone selection
- **Correction history** — every correction is saved and encrypted at rest with Fernet field-level encryption
- **Analytics** — most-used tone, correction frequency, 7-day activity stats
- **Dual surface** — installable PWA (works in any browser) and a Chrome extension with a floating action button for in-page corrections
- **Secure auth** — JWT (HS256) with PBKDF2-SHA256 password hashing; httpOnly cookies for the PWA, `chrome.storage.local` for the extension

---

## Tech Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, async SQLAlchemy |
| AI | Groq API (`llama-3.3-70b-versatile`) |
| DB — local | SQLite via `aiosqlite` |
| DB — production | Render free managed Postgres via `asyncpg` |
| Migrations | Alembic |
| Encryption | `cryptography` Fernet (field-level, correction history) |
| Auth | PyJWT HS256 + PBKDF2-SHA256 |
| Frontend (PWA) | HTML5, Bootstrap 5, vanilla JS, service worker |
| Extension | Chrome Manifest V3 |
| Deploy | Render free web service + Render free Postgres |

---

## Project Structure

```text
SmartWrite/
├── backend/
│   ├── alembic/               # migrations
│   │   └── versions/
│   └── app/
│       ├── models/            # SQLAlchemy ORM models (User, CorrectionHistory)
│       ├── routers/           # FastAPI route handlers (auth, correct, history)
│       ├── schemas/           # Pydantic request/response schemas
│       ├── auth.py            # JWT mint/verify, PBKDF2 hashing, Bearer+cookie dependency
│       ├── config.py          # pydantic-settings, async driver rewrite for Render Postgres
│       ├── database.py        # async engine, session factory, Base
│       ├── encryption.py      # Fernet encrypt/decrypt helpers
│       ├── groq_client.py     # async Groq API calls, exponential backoff on 429/5xx
│       └── main.py            # FastAPI app, routers, static file mount, CORS
├── extension/
│   ├── manifest.json          # MV3 manifest
│   ├── background.js          # service worker, all API calls via chrome.runtime.onMessage
│   ├── content.js             # selection capture, floating action button, inline panel
│   ├── content.css            # scoped sw- prefixed styles
│   ├── popup.html             # extension popup UI
│   └── popup.js              # popup logic
├── frontend/
│   ├── index.html             # SPA shell (auth view + app view)
│   ├── app.js                 # vanilla JS, cookie-based fetch, history pagination
│   ├── manifest.json          # PWA manifest
│   ├── sw.js                  # service worker (cache-first static, network-only /api/*)
│   └── icon.svg
├── tests/
│   ├── conftest.py            # fixtures: temp SQLite DB, env vars, ASGI test client
│   ├── test_auth_utils.py     # hashing, JWT, expiry (11 tests)
│   ├── test_encryption.py     # Fernet round-trips, wrong-key, corruption (7 tests)
│   ├── test_groq_client.py    # tone validation, retry logic, mocked responses (13 tests)
│   └── test_api.py            # all endpoints end-to-end (24 tests)
├── .env.example               # template — copy to .env, never commit .env
├── alembic.ini
├── pytest.ini
├── render.yaml                # Render Blueprint (web service + Postgres add-on)
├── requirements.txt
└── runtime.txt                # pins Python 3.12 for Render
```

---

## Local Setup

### Prerequisites

- Python 3.12+ (3.14 works; see [Known Limitations](#known-limitations))
- A free [Groq API key](https://console.groq.com) — no credit card required
- OpenSSL 3.0+ (required by `cryptography>=48.0.0`)

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd SmartWrite
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
DEBUG=true

DATABASE_URL=sqlite+aiosqlite:///./smartwrite.db

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here

GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile

# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
HISTORY_ENCRYPTION_KEY=your-fernet-key-here
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) — the PWA loads directly from the FastAPI app.

---

## Running Tests

```bash
pytest
```

55 tests across auth utilities, encryption, Groq client (mocked), and full API end-to-end. All green in ~5 s.

```text
tests/test_auth_utils.py     11 tests
tests/test_encryption.py      7 tests
tests/test_groq_client.py    13 tests
tests/test_api.py            24 tests
```

---

## Chrome Extension

1. Open `chrome://extensions` in Chrome
2. Enable **Developer mode** (toggle, top-right)
3. Click **Load unpacked** and select the `extension/` folder
4. Click the SmartWrite icon in the toolbar to open the popup
5. Log in, then highlight any text on any page — a floating **W** button appears; click it to correct inline

The extension talks to `http://localhost:8000` by default. Change the API base URL in the popup settings field to point to your deployed Render URL after deploying.

---

## API Reference

All protected routes require a JWT as a `Bearer` token in the `Authorization` header (extension) or the `smartwrite_token` httpOnly cookie (PWA).

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | — | DB ping, returns `{"status":"ok"}` |
| `POST` | `/api/register` | — | Create account, returns JWT + sets cookie |
| `POST` | `/api/login` | — | Authenticate, returns JWT + sets cookie |
| `POST` | `/api/logout` | — | Clears httpOnly cookie |
| `GET` | `/api/me` | JWT | Returns `{id, email}` |
| `POST` | `/api/correct` | JWT | Correct text; body: `{text, tone?}` |
| `GET` | `/api/history` | JWT | Paginated correction history (`?limit=&offset=`) |
| `GET` | `/api/analytics` | JWT | Tone breakdown, total corrections, 7-day count |

### `/api/correct` request body

```json
{
  "text": "your text here (1–5000 chars)",
  "tone": "formal"
}
```

`tone` is optional — omit it and the AI detects the best tone automatically. Valid values: `formal`, `casual`, `friendly`, `professional`.

---

## Deployment (Render)

The `render.yaml` Blueprint provisions everything in one click.

### Steps

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo
3. Render creates the web service and free Postgres add-on automatically
4. In the Render dashboard, manually set the two secrets that cannot be auto-generated:
   - `GROQ_API_KEY` — your Groq key from [console.groq.com](https://console.groq.com)
   - `HISTORY_ENCRYPTION_KEY` — a Fernet key (generate locally with the command in `.env.example`)
5. The start command runs `alembic upgrade head` before uvicorn on every deploy, so migrations are always applied

> **Operational reminder:** Render's free Postgres add-on is **deleted 30 days after creation**. Before that deadline, recreate the add-on and trigger a redeploy — Alembic recreates the schema in seconds. Set a calendar reminder.

---

## Security Design

| Concern | Approach |
| --- | --- |
| Password storage | PBKDF2-SHA256 via stdlib `hashlib` — no plaintext ever stored |
| Session tokens | JWT HS256, short-lived; httpOnly cookie (PWA) or `chrome.storage.local` (extension) |
| Text at rest | Fernet field-level encryption on `original_text` / `corrected_text`; key never committed |
| Analytics aggregation | `tone` and `created_at` stored unencrypted — deliberate tradeoff to avoid decrypting every row for aggregate queries |
| TLS in transit | Render provides HTTPS automatically; no extra config needed |
| Secrets | `.env` only, never committed; `.env.example` holds placeholders |
| Logs | Raw passwords, JWTs, API keys, and user text are never written to logs |

---

## Known Limitations

- **Groq free tier**: ~30 requests/min, ~1,000/day. The client implements exponential backoff (1 s → 2 s → 4 s) and surfaces a friendly message on rate-limit; heavy testing will still hit the cap.
- **Render Postgres 30-day reset**: free instances are auto-deleted. Treat renewal as a recurring operational task, not a surprise outage.
- **Python 3.14 on Windows**: some packages lack pre-built wheels at older pins and attempt C compilation (requires MSVC). Pinned versions in `requirements.txt` (`greenlet>=3.5.1`, `asyncpg>=0.31.0`) ship `cp314` wheels to avoid this.
- **No refresh-token flow**: the MVP uses a single short-lived access token. Token expiry requires a new login. Refresh tokens are a planned later phase.
- **HF fallback**: the Hugging Face Inference Providers fallback is wired behind the same interface but not enabled by default. Verify a model is live on its Hugging Face page before enabling — availability changes without notice.

---

## License

[MIT](LICENSE) © 2026 M.Y Hanan Mohamed
