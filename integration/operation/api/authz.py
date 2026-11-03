from fastapi import Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user

STAFF_ROLES = {"worker", "manager"}


def require_staff(current_user: CurrentUser) -> None:
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires worker or manager role")


def require_manager(current_user: CurrentUser) -> None:
    if current_user.role != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires manager role")


def require_self_or_staff(current_user: CurrentUser, customer_id: int) -> None:
    if current_user.role in STAFF_ROLES:
        return
    if current_user.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another customer's data")


# FastAPI-dependency wrappers: routes take these via Depends() instead of
# calling the checks above in the body, so a route's role requirement is
# visible on route.dependant (e.g. for a startup pass building the API MCP
# server's permission manifest) instead of being invisible to reflection.


def require_staff_dep(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    require_staff(current_user)
    return current_user


require_staff_dep.allowed_roles = STAFF_ROLES


def require_manager_dep(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    require_manager(current_user)
    return current_user


require_manager_dep.allowed_roles = {"manager"}
