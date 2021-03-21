from typing import Set, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    google_creds_path: str = Field(..., env="GOOGLE_CREDS_PATH")
    google_drive_token_path: str = Field(..., env="GOOGLE_DRIVE_TOKEN_PATH")
    google_drive_scopes: Set[str] = Field(..., env="GOOGLE_DRIVE_SCOPES")

    psql_url: str = Field(..., env="PSQL_URL")

    nvr_api_url: str = Field(..., env="NVR_API_URL")
    nvr_api_key: str = Field(..., env="NVR_API_KEY")

    record_days: Set[str] = Field(
        {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
        },
        env="RECORD_DAYS",
    )
    record_duration: int = Field(
        30,
        env="RECORD_DURATION",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# weird
def set_config(file_path: str = "../.env"):
    global config
    config = Settings(_env_file=file_path)
    return config


config = set_config()
