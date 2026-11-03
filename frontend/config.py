from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_api_base_url: str = "http://localhost:8003"
    shared_api_base_url: str = "http://localhost:8002"


settings = FrontendSettings()
