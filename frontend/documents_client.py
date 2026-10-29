import httpx

from frontend.config import settings


def list_documents(token: str) -> list[dict]:
    with httpx.Client(base_url=settings.shared_api_base_url, timeout=10) as client:
        response = client.get("/shared/documents", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()


def upload_document(token: str, filename: str, content: bytes, allowed_roles: list[str], notes: str) -> dict:
    params = [("allowed_roles", role) for role in allowed_roles]
    if notes:
        params.append(("notes", notes))
    with httpx.Client(base_url=settings.shared_api_base_url, timeout=30) as client:
        response = client.post(
            "/shared/documents",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            files={"file": (filename, content, "text/markdown")},
        )
        response.raise_for_status()
        return response.json()


def delete_document(token: str, filename: str) -> None:
    with httpx.Client(base_url=settings.shared_api_base_url, timeout=10) as client:
        response = client.delete(f"/shared/documents/{filename}", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
