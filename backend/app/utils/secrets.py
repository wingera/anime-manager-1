import os
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings


def _secret_file_path() -> Path:
    return get_settings().data_dir / "secret.key"


def _read_or_create_development_key() -> bytes:
    secret_file = _secret_file_path()
    if secret_file.exists():
        return secret_file.read_bytes().strip()

    secret_file.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    secret_file.write_bytes(key + b"\n")
    secret_file.chmod(0o600)
    return key


def _load_key() -> bytes:
    env_key = os.getenv("SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip().encode("utf-8")
    return _read_or_create_development_key()


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(_load_key())


def ensure_secret_key_available() -> None:
    _fernet()


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def is_encrypted_secret(value: str | None) -> bool:
    if value is None:
        return False
    try:
        _fernet().decrypt(value.encode("utf-8"))
    except (InvalidToken, ValueError, TypeError):
        return False
    return True


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError, UnicodeDecodeError):
        return value
