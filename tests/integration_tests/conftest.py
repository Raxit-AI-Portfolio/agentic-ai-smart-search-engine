from pathlib import Path

import httpx
import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

RESULTS_DIR = Path(__file__).parent / "results"

# Demo accounts seeded into membershipdb — see project-notes/DbSetup.md and
# integration/shared/db/membershipdb_seed.sql.
DEMO_USERS = {
    "customer": ("alice", "customer123"),
    "worker": ("bob", "worker123"),
    "manager": ("carol", "manager123"),
}


class _AuthTestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_api_base_url: str = "http://localhost:8003"


@pytest.fixture(scope="session")
def auth_api_base_url() -> str:
    return _AuthTestSettings().auth_api_base_url


@pytest.fixture(scope="session")
def auth_tokens(auth_api_base_url: str) -> dict[str, dict[str, str]]:
    """Logs each seeded demo user into the real auth-api once per test session,
    so tests exercise the actual login -> JWT -> Redis-cached-identity flow
    rather than minting tokens locally."""
    tokens: dict[str, dict[str, str]] = {}
    with httpx.Client(base_url=auth_api_base_url, timeout=10) as client:
        for role, (username, password) in DEMO_USERS.items():
            response = client.post("/auth/token", json={"username": username, "password": password})
            response.raise_for_status()
            body = response.json()
            tokens[role] = {"username": username, "token": body["access_token"]}
    return tokens


@pytest.fixture(scope="session", autouse=True)
def _ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
