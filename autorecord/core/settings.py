from typing import Set
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    google_creds_path: str = Field(None, env="GOOGLE_CREDS_PATH")
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
    record_start: str = Field("09:30", env="RECORD_START")
    record_end: str = Field("21:00", env="RECORD_END")
    records_folder: str = Field("/records", env="RECORDS_FOLDER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# weird
def set_config(file_path: str = "../.env"):
    global config
    config = Settings(_env_file=file_path)
    return config


config = set_config()
