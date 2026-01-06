from pydantic import PostgresDsn
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class SlackConfig(BaseSettings):
    bot_token: str
    user_token: str
    signing_secret: str
    app_token: str | None = None
    heartbeat_channel: str | None = None
    client_id: str
    client_secret: str
    redirect_uri: str
    xoxc_token: str
    xoxd_token: str
    maintainer_id: str
    support_channel: str


class AirtableNDABaseConfig(BaseSettings):
    base_id: str
    table_id: str
    view_id: str | None = None
    api_key: str


class AirtableConfig(BaseSettings):
    nda: AirtableNDABaseConfig


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", extra="ignore"
    )
    slack: SlackConfig
    airtable: AirtableConfig
    database_url: PostgresDsn
    environment: str = "development"
    port: int = 3000


config = Config()  # type: ignore
