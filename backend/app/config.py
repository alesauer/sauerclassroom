import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve a raiz do projeto quando executado localmente fora do Docker
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = _BASE_DIR / "data"
_DEFAULT_CREDENTIALS_DIR = _BASE_DIR / "credentials"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str = "local_dev_secret_key_sauer_classroom"
    DATABASE_URL: str = f"sqlite:///{(_DEFAULT_DATA_DIR / 'academic_hub.db').as_posix()}"
    CREDENTIALS_DIR: str = str(_DEFAULT_CREDENTIALS_DIR)

    GOOGLE_CLIENT_SECRETS_FILE: str = ""
    GOOGLE_TOKEN_FILE: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    COTEMIG_ADAPTER_MODE: str = "mock"
    COTEMIG_PORTAL_URL: str = "https://portal.cotemig.com.br"

    @property
    def credentials_path(self) -> Path:
        path = Path(self.CREDENTIALS_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def google_client_secrets_path(self) -> Path:
        if self.GOOGLE_CLIENT_SECRETS_FILE:
            return Path(self.GOOGLE_CLIENT_SECRETS_FILE)
        return self.credentials_path / "credentials.json"

    @property
    def google_token_path(self) -> Path:
        if self.GOOGLE_TOKEN_FILE:
            return Path(self.GOOGLE_TOKEN_FILE)
        return self.credentials_path / "token.json"

    @property
    def cotemig_session_path(self) -> Path:
        return self.credentials_path / "cotemig_session.json"


settings = Settings()


def _get_fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_json(payload: dict[str, Any]) -> bytes:
    """Criptografa um dicionário JSON usando Fernet para persistência segura em volume local."""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _get_fernet().encrypt(raw)


def decrypt_json(token: bytes) -> dict[str, Any]:
    """Descriptografa payload JSON salvo com Fernet."""
    try:
        raw = _get_fernet().decrypt(token)
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise ValueError("Falha ao descriptografar sessão local.") from exc


def ensure_data_dir() -> None:
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_file = settings.DATABASE_URL.replace("sqlite:///", "", 1)
        if db_file.startswith("/"):
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        else:
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    os.makedirs(settings.credentials_path, exist_ok=True)

