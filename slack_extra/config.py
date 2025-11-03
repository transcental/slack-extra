from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class SlackConfig(BaseSettings):
    bot_token: str
    signing_secret: str
    app_token: str | None
    heartbeat_channel: str | None = None


class AirtableNDABaseConfig(BaseSettings):
    base_id: str
    table_id: str
    view_id: str
    api_key: str


class AirtableConfig(BaseSettings):
    nda: AirtableNDABaseConfig


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", extra="ignore"
    )
    slack: SlackConfig
    airtable: AirtableConfig
    environment: str = "development"
    port: int = 3000


config = Config()  # type: ignore
