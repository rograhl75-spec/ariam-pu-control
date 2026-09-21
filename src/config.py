"""Configuração centralizada e segura da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class MailSettings:
    """Configurações SMTP."""

    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True


@dataclass(frozen=True)
class Settings:
    """Configurações centrais da aplicação."""

    db_path: Path
    weather_latitude: float
    weather_longitude: float
    users: dict[str, dict[str, str]]
    mail: MailSettings | None


def _secrets_get(path: str, default: Any = None) -> Any:
    current: Any = st.secrets
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def _build_mail_settings() -> MailSettings | None:
    host = _secrets_get("smtp.host") or os.getenv("SMTP_HOST")
    if not host:
        return None

    port = int(_secrets_get("smtp.port", os.getenv("SMTP_PORT", "587")))
    username = _secrets_get("smtp.username") or os.getenv("SMTP_USERNAME", "")
    smtp_secret = _secrets_get("smtp.password") or os.getenv("SMTP_PASSWORD", "")
    use_tls = bool(_secrets_get("smtp.use_tls", True))

    if not username or not smtp_secret:
        raise ValueError("SMTP configurado sem username/password em st.secrets.")

    return MailSettings(host, port, username, smtp_secret, use_tls)


def get_settings() -> Settings:
    """Retorna configurações seguras e validadas."""
    db_path = Path(_secrets_get("database.path", "data/ariam_pu.db"))

    users = _secrets_get("users", {})
    if not users:
        users = {
            "admin": {
                "password_hash": "pbkdf2_sha256$260000$demo$6b41a8dbf95fbb2f6e3e95f3f8ecef1f907058d8f58c7f7562ef42f7518d3774",
                "role": "admin",
            }
        }

    settings = Settings(
        db_path=db_path,
        weather_latitude=float(_secrets_get("weather.latitude", -23.31028)),
        weather_longitude=float(_secrets_get("weather.longitude", -51.16278)),
        users=users,
        mail=_build_mail_settings(),
    )
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
