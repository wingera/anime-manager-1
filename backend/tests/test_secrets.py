from pathlib import Path

import pytest

from app.utils import secrets


def test_encrypt_secret_does_not_return_plaintext() -> None:
    encrypted = secrets.encrypt_secret("secret-value")

    assert encrypted is not None
    assert encrypted != "secret-value"


def test_decrypt_secret_restores_plaintext() -> None:
    encrypted = secrets.encrypt_secret("secret-value")

    assert secrets.decrypt_secret(encrypted) == "secret-value"


def test_decrypt_secret_accepts_legacy_plaintext() -> None:
    assert secrets.decrypt_secret("legacy-plain-value") == "legacy-plain-value"


def test_development_secret_file_is_ignored_by_git() -> None:
    gitignore = next(
        (
            parent / ".gitignore"
            for parent in Path(__file__).resolve().parents
            if (parent / ".gitignore").exists()
        ),
        None,
    )
    if gitignore is None:
        pytest.skip("当前运行环境未包含 Git 根目录 .gitignore")

    assert "data/secret.key" in gitignore.read_text(encoding="utf-8")
