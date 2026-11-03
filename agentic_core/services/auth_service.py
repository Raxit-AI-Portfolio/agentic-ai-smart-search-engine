import jwt

from agentic_core.configs.config import settings
from agentic_core.state.state import State


def decode_token(authorization_header: str) -> dict:
    token = authorization_header.removeprefix("Bearer ").strip()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def build_initial_state(query: str, authorization_header: str, debug: bool = False) -> State:
    claims = decode_token(authorization_header)
    return State(query=query, role=claims["role"], authorization_header=authorization_header, debug=debug)
