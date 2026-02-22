from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class DittoSettings(BaseModel):
    base_url: str = ""
    username: str = ""
    password: str = ""


class PopulatorSettings(BaseModel):
    polling_interval: int = 3600


class Settings(BaseSettings):
    model_config = SettingsConfigDict(toml_file="config.toml")

    ditto: DittoSettings = DittoSettings()
    populator: PopulatorSettings = PopulatorSettings()

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


settings = Settings()
