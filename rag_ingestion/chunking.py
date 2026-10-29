from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from rag_ingestion.config import settings

_HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


@dataclass
class Chunk:
    id: str
    text: str
    source_file: str
    header_path: str
    chunk_index: int
    allowed_roles: list[str]


def _header_path(metadata: dict) -> str:
    return " > ".join(metadata[level] for level in ("h1", "h2", "h3") if level in metadata)


def extract_description(markdown_text: str, max_chars: int = 500) -> str:
    """Pulls a short description straight from the document's own content —
    the first real paragraph after its title and any **Key:** metadata
    bullets (a "## 1. Purpose" section's text if the doc has one, otherwise
    whatever paragraph/blockquote comes next) — so the RAG catalog
    description lives with the document, the same way a SQL object's comes
    from its own COMMENT ON and an API endpoint's comes from its own
    docstring, rather than being hand-maintained separately.
    """
    lines = markdown_text.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)

    paragraph: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("**") or stripped.startswith("#"):
            continue  # metadata bullet or a heading (e.g. "## 1. Purpose") — keep looking for its paragraph
        paragraph.append(stripped.lstrip("> ").strip())

    return " ".join(paragraph).strip()[:max_chars]


def chunk_document(source_file: str, markdown_text: str, allowed_roles: list[str]) -> list[Chunk]:
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS_TO_SPLIT_ON, strip_headers=False)
    sections = header_splitter.split_text(markdown_text)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[Chunk] = []
    for section in sections:
        header_path = _header_path(section.metadata)
        for piece in char_splitter.split_text(section.page_content):
            chunks.append(
                Chunk(
                    id=f"{source_file}::{len(chunks)}",
                    text=piece,
                    source_file=source_file,
                    header_path=header_path,
                    chunk_index=len(chunks),
                    allowed_roles=allowed_roles,
                )
            )
    return chunks
