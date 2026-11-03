from fastapi import FastAPI
from fastapi.routing import APIRoute

ALL_ROLES = ["customer", "worker", "manager"]


def extract_permissions(app: FastAPI) -> dict[str, dict]:
    """Per route: {"roles": [...], "description": "..."} — the description is
    the endpoint function's docstring, used to give the planning LLM a real
    idea of what each API resource does/needs instead of just its route
    string (see agentic_core/services/api_service.py's describe_objects)."""
    permissions: dict[str, dict] = {}
    _walk(app.routes, permissions)
    return permissions


def _walk(routes, permissions: dict[str, dict]) -> None:
    for route in routes:
        if isinstance(route, APIRoute):
            allowed_roles = ALL_ROLES
            for dependency in route.dependant.dependencies:
                roles = getattr(dependency.call, "allowed_roles", None)
                if roles is not None:
                    allowed_roles = sorted(roles)
            description = (route.endpoint.__doc__ or "").strip()
            for method in route.methods - {"HEAD", "OPTIONS"}:
                permissions[f"{method} {route.path}"] = {"roles": allowed_roles, "description": description}
        # include_router() wraps the sub-router rather than flattening its
        # routes into app.routes directly, so descend into whichever
        # attribute actually holds them.
        elif hasattr(route, "original_router"):
            _walk(route.original_router.routes, permissions)
        elif hasattr(route, "routes"):
            _walk(route.routes, permissions)
