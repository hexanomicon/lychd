from __future__ import annotations

import secrets
from typing import Final

from pydantic import Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

PORT_PHOENIX_UI: Final[int] = 6006
PORT_PHOENIX_OTLP: Final[int] = 4318


class PhoenixSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PHOENIX_")

    # Port for the Web Interface (e.g. http://localhost:6006)
    ui_port: int = 6006

    # Port for receiving data via HTTP (Standard OTel port)
    otlp_port: int = 4318
    image: str = "docker.io/arizephoenix/phoenix:12"
    host: str = "localhost"
    admin_user: str = "admin"
    admin_password: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(16)),
    )

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.otlp_port}"


phoenix: PhoenixSettings = Field(default_factory=PhoenixSettings)
