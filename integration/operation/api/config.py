from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    operationsdb_customer_url: str
    operationsdb_worker_url: str
    operationsdb_manager_url: str

    # For GetByPaymentType: PaymentMethod.PaymentType lives in CustomerDb, so
    # this API resolves it via the Customer API instead of a cross-db query.
    customer_api_base_url: str

    auth_api_base_url: str


settings = Settings()
