# SmartWrite — Learnings & Bug Study Notes

A reference file for things discovered during development that are worth
understanding deeply, not just knowing the fix. Each entry explains *what*
broke, *why* it broke, and *what concept* to remember going forward.

---

## Session 2026-06-21 — Two Bugs Found & Fixed, Full pytest Suite Added

---

### Bug 1 — `ModuleNotFoundError: No module named 'app'`

#### What happened
Running the backend with this command:
```powershell
uvicorn app.main:app --reload --port 8000
```
Produced:
```
ModuleNotFoundError: No module named 'app'
```

#### Why it broke
`uvicorn app.main:app` tells uvicorn to import a Python module called `app`,
then find an attribute called `main` inside it, then find `app` inside that.
Python looks for this module in `sys.path`, which starts with the current
working directory.

The actual file is at `backend/app/main.py`. If you're sitting in the
`SmartWrite/` directory, Python can see `backend/` as a package — but there
is no top-level `app/` package. So Python raises `ModuleNotFoundError`.

The `main.py` docstring at the very top already documented the correct command:
```
uvicorn backend.app.main:app --reload
```
This tells uvicorn: import `backend.app.main` (which Python can resolve from
`SmartWrite/`), then find the `app` FastAPI instance inside it.

#### The fix
Always run from the `SmartWrite/` project root:
```powershell
uvicorn backend.app.main:app --reload --port 8000
```

#### Concept to remember
Python module paths in strings (like the ones uvicorn and gunicorn accept)
mirror `import` statements exactly. `backend.app.main:app` is equivalent to:
```python
from backend.app.main import app
```
If the import would fail in a Python shell, the uvicorn command will fail
with the same error. When you see `ModuleNotFoundError`, first ask: "from
which directory am I running this, and does that directory contain the first
part of the dotted path as a package (a folder with `__init__.py`)?"

---

### Bug 2 — Groq Retry Logic Off-By-One (Only 3 Attempts Made Instead of 4)

#### What happened
The `correct_text()` function in `backend/app/groq_client.py` was supposed
to retry a failed Groq API call up to 3 times (4 total attempts). In
practice it only made 3 attempts and gave up one attempt early.

#### The broken code
```python
max_retries = 3
max_attempts = max_retries + 1  # = 4

for attempt in range(max_attempts):   # loop: attempt = 0, 1, 2, 3
    ...
    if response.status_code == 429:
        if attempt == max_retries - 1:   # <-- BUG: fires when attempt == 2
            raise GroqUnavailableError(...)
        await asyncio.sleep(...)
        continue
```

#### Tracing through the bug
| attempt | `max_retries - 1` check | what happens |
|---------|------------------------|--------------|
| 0       | `0 == 2`? No           | sleep, retry |
| 1       | `1 == 2`? No           | sleep, retry |
| 2       | `2 == 2`? **Yes**      | **raises — never reaches attempt 3** |
| 3       | *(never reached)*      | — |

The intent was: "on the *last* attempt, raise instead of sleeping and
retrying." The last attempt has index `max_attempts - 1 = 3`, not
`max_retries - 1 = 2`. The bug was using the wrong variable.

This same off-by-one was repeated in all three retry branches:
- `httpx.ConnectError / TimeoutException`
- HTTP 429 (rate limit)
- HTTP 5xx (server error)

#### The fix
Change all three to:
```python
if attempt >= max_retries:   # fires when attempt == 3 (the last one)
    raise GroqUnavailableError(...)
```

`>= max_retries` is equivalent to `== max_retries` here (since `attempt`
can never exceed `max_attempts - 1 = max_retries`), but `>=` is defensive —
it catches the case if the bounds ever change.

Also fixed the log format string, which said `"attempt %d/%d", attempt + 1,
max_retries` and would print "attempt 4/3" on the last attempt. Changed
`max_retries` → `max_attempts` so it prints "attempt 4/4".

#### Concept to remember — Off-By-One Errors in Retry Loops
Off-by-one errors are extremely common in retry logic. The mental model that
helps: distinguish between the *number* of retries and the *index* of the
last attempt.

```
max_retries = 3        → you want 3 extra chances after the first try
max_attempts = 4       → total calls to the external service
last index   = 3       → range(4) produces 0, 1, 2, 3
```

The guard check should always be: **"is this the last element in the loop?"**
which is `attempt == max_attempts - 1` or equivalently `attempt >= max_retries`.
Never use `attempt == max_retries - 1` unless you intentionally want to stop
one attempt early.

#### How the tests catch this bug
`test_groq_client.py` has three regression tests that assert the exact call
count after all retries are exhausted:

```python
async def test_rate_limit_retries_4_times_then_raises():
    ctx, client_mock = _mock_ctx(_http_response(429))
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(GroqUnavailableError):
            await correct_text("text", "formal")
    assert client_mock.post.call_count == 4   # <-- fails if bug is re-introduced
```

If the off-by-one bug returns, `call_count` would be 3 and the assertion
would fail immediately, pointing directly at the retry logic.

---

### Testing Patterns Introduced — Things Worth Studying

#### 1. Setting env vars before importing the application in tests

`tests/conftest.py` sets environment variables at the very top, before any
`from backend...` import:

```python
import os
from cryptography.fernet import Fernet

os.environ["SECRET_KEY"] = "test-secret-key-..."
os.environ["HISTORY_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
...

# Only NOW import the backend
from backend.app.config import get_settings
from backend.app.database import Base, get_db
from backend.app.main import app
```

**Why this matters:** `get_settings()` is decorated with `@lru_cache`, so
the first call caches the result forever (within a process). Several modules
call it at import time (`database.py`, `auth.py`, routers). If the env vars
aren't set before those imports happen, the cached settings will have empty
`SECRET_KEY`, empty `HISTORY_ENCRYPTION_KEY`, etc., and auth and encryption
will silently fail or raise `RuntimeError`.

Setting env vars first means the very first `get_settings()` call — wherever
it happens during module import — reads our test values and caches those.

#### 2. NullPool for async SQLite in tests

```python
from sqlalchemy.pool import NullPool

_test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    future=True,
    poolclass=NullPool,
)
```

**Why NullPool?** SQLAlchemy normally keeps a pool of open database
connections. With aiosqlite, those connections are internally tied to the
asyncio event loop they were created in. pytest-asyncio creates a fresh
event loop for each test function. If a pooled connection was created in the
previous test's loop, using it in the next test's loop would raise a
`RuntimeError: Task attached to a different loop` error.

`NullPool` disables connection pooling entirely: every `db.begin()` call
creates a brand-new connection and closes it when done. No loop-binding, no
cross-test contamination.

**Why a temp file instead of `:memory:`?** SQLite in-memory databases are
per-connection by default. If the session setup (`asyncio.run(create_all())`)
creates tables in connection A, and tests create connection B, connection B
sees an empty database. A temp file on disk is shared across all connections,
so the tables created in setup are visible to every test.

#### 3. Overriding FastAPI dependencies in tests

```python
@pytest_asyncio.fixture
async def client():
    async def _override_db():
        async with _TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db   # swap in test DB
    async with AsyncClient(...) as c:
        yield c
    app.dependency_overrides.clear()                   # restore after test
```

`app.dependency_overrides` is a dict that FastAPI checks before resolving
any `Depends(...)`. By mapping `get_db` → `_override_db`, every endpoint
that does `db: AsyncSession = Depends(get_db)` gets a session from the
test engine instead of the production one. After the test, `clear()` removes
the override so it doesn't leak into other tests.

This is the canonical FastAPI testing pattern. It lets you test the full
HTTP stack (routing, auth, Pydantic validation, business logic, database
queries) without mocking anything deep in the internals.

#### 4. Mocking `async with httpx.AsyncClient() as client:` calls

The Groq client uses:
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(...)
```

To mock this without making real HTTP requests:
```python
def _mock_ctx(response):
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client

with patch("httpx.AsyncClient", return_value=ctx):
    result = await correct_text(...)
```

Step by step:
1. `patch("httpx.AsyncClient", return_value=ctx)` — when code calls
   `httpx.AsyncClient(timeout=30.0)`, it gets our `ctx` object back instead.
2. `async with ctx as client:` — Python calls `await ctx.__aenter__()`,
   which we set to return our `client` AsyncMock.
3. `await client.post(...)` — returns the `response` MagicMock we provided.
4. On exit: `await ctx.__aexit__(...)` — called with `(None, None, None)`,
   returning `False` (meaning: don't suppress any exceptions).

**Patching `asyncio.sleep` to skip delays:**
```python
with patch("asyncio.sleep", new_callable=AsyncMock):
    ...
```
Replaces `asyncio.sleep` with an `AsyncMock` that returns immediately.
Without this, retry tests would wait 1s + 2s + 4s = 7 seconds each.

#### 5. Patching at the point of import, not the point of definition

The correct router imports like this:
```python
from backend.app.groq_client import correct_text
```

To mock `correct_text` in a router test, patch the *name in the router's
namespace*, not the original function:
```python
with patch("backend.app.routers.correct.correct_text", new_callable=AsyncMock):
    ...
```

If you patched `backend.app.groq_client.correct_text` instead, the router
would still hold a reference to the original unpatched function and the mock
would have no effect. Always patch where the name is *used*, not where it is
*defined*.

---

## General Rules to Carry Forward

1. **Run uvicorn from the project root with the full dotted module path.**
   `uvicorn backend.app.main:app`, never `uvicorn app.main:app`.

2. **Off-by-one in retry loops:** the last-attempt check is
   `attempt >= max_retries` (or `== max_attempts - 1`), never
   `attempt == max_retries - 1`.

3. **In pytest, set env vars before the first backend import.** Otherwise
   `@lru_cache` bakes in empty/wrong config values permanently for the
   test session.

4. **Use `NullPool` + a temp file for async SQLAlchemy tests** — avoids
   both the in-memory per-connection isolation problem and the event-loop
   binding problem of aiosqlite connection pools.

5. **Patch at the import site, not the definition site.** `from x import f`
   creates a new name binding; you must patch that binding, not the original.
