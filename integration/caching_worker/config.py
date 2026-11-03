from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    customerdb_worker_url: str
    operationsdb_worker_url: str


worker_settings = WorkerSettings()
