from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str


cache_settings = CacheSettings()
