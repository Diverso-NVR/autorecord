import sys
from typing import Set
from pydantic import BaseSettings, Field

from loguru import logger


class Settings(BaseSettings):
    google_creds_path: str = Field(None, env="GOOGLE_CREDS_PATH")
    google_drive_token_path: str = Field(..., env="GOOGLE_DRIVE_TOKEN_PATH")
    google_drive_scopes: Set[str] = Field(..., env="GOOGLE_DRIVE_SCOPES")
    google_semaphore: int = Field(15, env="GOOGLE_SEMAPHORE")
    upload_without_sound: bool = Field(False, env="UPLOAD_WITHOUT_SOUND")

    psql_url: str = Field(..., env="PSQL_URL")

    nvr_api_url: str = Field(..., env="NVR_API_URL")
    nvr_api_key: str = Field(..., env="NVR_API_KEY")

    record_days: Set[str] = Field(
        {
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
        },
        env="RECORD_DAYS",
    )
    record_duration: int = Field(
        30,
        env="RECORD_DURATION",
    )
    record_start: int = Field(9, env="RECORD_START")
    record_end: int = Field(21, env="RECORD_END")
    records_folder: str = Field("/records", env="RECORDS_FOLDER")

    loguru_level: str = Field("DEBUG", env="LOGURU_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# weird
def set_config(file_path: str = "../.env"):
    global config
    config = Settings(_env_file=file_path)
    return config


config = set_config()

logger.remove()
logger.add(sys.stderr, level=config.loguru_level)