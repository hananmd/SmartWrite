"""Fernet field-level encryption for correction history text fields.

Encrypt original_text / corrected_text before writing to the database;
decrypt when serving history back to the authenticated owner. The key lives
only in HISTORY_ENCRYPTION_KEY (env var / .env) — never in source code or
committed config.

Tone label and timestamp are stored unencrypted (needed for analytics
aggregation without decrypting every row — deliberate design from CLAUDE.md).
"""

from functools import lru_cache

from cryptography.fernet import Fernet

from backend.app.config import get_settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Return a cached Fernet instance built from the env key.

    Raises RuntimeError if HISTORY_ENCRYPTION_KEY is missing or blank —
    the app should fail loudly rather than silently skip encryption.

    Generate a valid key with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    key = get_settings().history_encryption_key
    if not key:
        raise RuntimeError(
            "HISTORY_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_text(plaintext: str) -> bytes:
    """Return Fernet-encrypted ciphertext bytes for a UTF-8 string."""
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes) -> str:
    """Decrypt Fernet ciphertext bytes and return the original UTF-8 string."""
    return _fernet().decrypt(ciphertext).decode("utf-8")
