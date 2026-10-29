from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    source_file: str
    header_path: str
    score: float
