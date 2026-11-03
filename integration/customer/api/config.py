from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    customerdb_customer_url: str
    customerdb_worker_url: str
    customerdb_manager_url: str

    auth_api_base_url: str


settings = Settings()
