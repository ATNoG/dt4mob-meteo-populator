import json
import sys

from loguru import logger
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class OidcSettings(BaseModel):
    base_url: str = ""
    realm: str = ""
    username: str = ""
    password: str = ""
    client_id: str = ""
    scope: str = "openid"


class PopulatorSettings(BaseModel):
    dry_run: bool = False


class LoggingSettings(BaseModel):
    level: str = "INFO"


class StationSettings(BaseModel):
    namespace: str = "internal"
    subject: str = "meteo"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(toml_file="config.toml")

    populator: PopulatorSettings = PopulatorSettings()
    logging: LoggingSettings = LoggingSettings()
    oidc: OidcSettings = OidcSettings()
    station: StationSettings = StationSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)


def _formatter(record: dict) -> str:
    base_format = (
        "<dim>{time:YYYY-MM-DD HH:mm:ss.SSS}</dim>"
        " | <level>{level: <8}</level>"
        " | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<yellow>{line}</yellow>"
        " | <level>{message}</level>"
    )

    extra = record["extra"].get("extra")
    if extra:
        extra_str = (
            json.dumps(extra, indent=2, ensure_ascii=False)
            .replace("{", "{{")
            .replace("}", "}}")
        )
        extra_part = f"\n<magenta>{extra_str}</magenta>"
    else:
        extra_part = ""
    return base_format + extra_part + "\n{exception}"


def configure_logging(level: str = "DEBUG") -> None:
    logger.remove()
    logger.add(sys.stderr, format=_formatter, level=level, colorize=True)  # ty: ignore[no-matching-overload]


settings = Settings()
configure_logging(settings.logging.level)
