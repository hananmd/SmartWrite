"""Unit tests for auth utility functions (no DB, no HTTP required)."""

import jwt
import pytest

from backend.app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    _ALGORITHM,
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.config import get_settings


# ── hash_password ─────────────────────────────────────────────────────────────

def test_hash_password_produces_correct_format():
    h = hash_password("password123")
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == 600_000
    assert len(parts[2]) == 32  # hex salt
    assert len(parts[3]) == 64  # hex SHA-256 digest


def test_hash_password_is_nondeterministic():
    # Different salts must produce different hashes for the same input.
    assert hash_password("same") != hash_password("same")


# ── verify_password ───────────────────────────────────────────────────────────

def test_verify_password_correct():
    h = hash_password("secret")
    assert verify_password("secret", h) is True


def test_verify_password_wrong_password():
    h = hash_password("secret")
    assert verify_password("wrong", h) is False


def test_verify_password_empty_password():
    h = hash_password("secret")
    assert verify_password("", h) is False


def test_verify_password_malformed_hash_returns_false():
    assert verify_password("secret", "not-a-valid-hash-format") is False


def test_verify_password_empty_hash_returns_false():
    assert verify_password("secret", "") is False


# ── create_access_token / decode ──────────────────────────────────────────────

def test_create_access_token_is_string():
    assert isinstance(create_access_token(1), str)


def test_create_access_token_decodes_to_correct_user_id():
    settings = get_settings()
    token = create_access_token(42)
    payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    assert payload["sub"] == "42"


def test_create_access_token_has_expiry_claim():
    settings = get_settings()
    token = create_access_token(1)
    payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    assert "exp" in payload


def test_token_invalid_with_wrong_secret():
    token = create_access_token(99)
    with pytest.raises(jwt.exceptions.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=[_ALGORITHM])


def test_access_token_expire_minutes_is_positive():
    assert ACCESS_TOKEN_EXPIRE_MINUTES > 0
