from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_ingested: int
    allowed_roles: list[str]
    notes: str | None = None


class DocumentListItem(BaseModel):
    filename: str
    allowed_roles: list[str]
    notes: str | None = None
    description: str | None = None
