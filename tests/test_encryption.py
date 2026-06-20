"""Unit tests for Fernet field-level encryption helpers."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from backend.app.encryption import decrypt_text, encrypt_text


def test_encrypt_returns_bytes():
    result = encrypt_text("hello world")
    assert isinstance(result, bytes)


def test_round_trip_plain_ascii():
    original = "The quick brown fox."
    assert decrypt_text(encrypt_text(original)) == original


def test_round_trip_unicode():
    original = "Héllo wörld — with émojis 🎉"
    assert decrypt_text(encrypt_text(original)) == original


def test_round_trip_empty_string():
    assert decrypt_text(encrypt_text("")) == ""


def test_encrypt_nondeterministic():
    # Fernet embeds a random IV so two encryptions of identical input differ.
    c1 = encrypt_text("same input")
    c2 = encrypt_text("same input")
    assert c1 != c2


def test_wrong_key_raises_invalid_token():
    ciphertext = encrypt_text("secret message")
    wrong_fernet = Fernet(Fernet.generate_key())
    with pytest.raises(InvalidToken):
        wrong_fernet.decrypt(ciphertext)


def test_corrupted_ciphertext_raises():
    ciphertext = encrypt_text("data")
    corrupted = ciphertext[:-4] + b"xxxx"
    with pytest.raises(Exception):
        decrypt_text(corrupted)
