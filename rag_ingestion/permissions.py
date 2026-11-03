from agentic_core.models.constants import ROLE_PERMISSIONS_DELTA

ALL_ROLES = list(ROLE_PERMISSIONS_DELTA.keys())


def default_allowed_roles(doc_key: str) -> list[str]:
    roles = [role for role, perms in ROLE_PERMISSIONS_DELTA.items() if doc_key in perms["rag"]]
    return roles or list(ALL_ROLES)
