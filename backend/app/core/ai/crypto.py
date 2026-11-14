"""Encryption for secrets kept in the database (AI provider API keys)."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    key = hashlib.sha256(get_settings().secrets_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str | None:
    """None if the token can't be decrypted (e.g. secrets_key changed)."""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
