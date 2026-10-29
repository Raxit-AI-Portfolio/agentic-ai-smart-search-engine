from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from integration.shared.auth_client import CurrentUser
from integration.shared.authz import require_manager_dep
from integration.shared.documents.schemas import DocumentListItem, DocumentUploadResponse
from integration.shared.documents.service import VALID_ROLES, get_documents, remove_document, upload_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentListItem])
async def list_all(current_user: CurrentUser = Depends(require_manager_dep)) -> list[DocumentListItem]:
    return [DocumentListItem(**doc) for doc in await get_documents()]


@router.post("", response_model=DocumentUploadResponse)
async def upload(
    file: UploadFile = File(...),
    allowed_roles: list[str] = Query(...),
    notes: str | None = Query(None),
    current_user: CurrentUser = Depends(require_manager_dep),
) -> DocumentUploadResponse:
    if not file.filename.endswith(".md"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .md files are supported")

    invalid_roles = set(allowed_roles) - VALID_ROLES
    if invalid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid roles: {sorted(invalid_roles)}")

    content = await file.read()
    chunks_ingested = await upload_document(file.filename, content, allowed_roles, notes)
    return DocumentUploadResponse(filename=file.filename, chunks_ingested=chunks_ingested, allowed_roles=allowed_roles, notes=notes)


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(filename: str, current_user: CurrentUser = Depends(require_manager_dep)) -> None:
    deleted = await remove_document(filename)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
