from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings only reads .env into its own fields; LangSmith tracing reads os.environ.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    customerdb_manager_url: str
    operationsdb_manager_url: str

    customer_api_base_url: str
    operations_api_base_url: str

    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    google_api_key: str
    planning_model: str = "gemini-2.5-flash"


settings = Settings()
