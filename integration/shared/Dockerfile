# Build context is the repo root (see docker-compose.yaml). Unlike the other
# two API images, this one also needs agentic_core/models (ROLE_PERMISSIONS_DELTA,
# read by rag_ingestion.permissions) and rag_ingestion itself, since the
# documents router embeds/upserts uploaded docs directly rather than going
# through a separate ingestion service. Manager-only document endpoints call
# the Auth API over HTTP (integration.shared.auth_client) instead of verifying
# JWTs locally.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY integration/__init__.py integration/__init__.py
COPY integration/shared integration/shared
COPY agentic_core/__init__.py agentic_core/__init__.py
COPY agentic_core/models agentic_core/models
COPY rag_ingestion rag_ingestion

EXPOSE 8000
CMD ["uvicorn", "integration.shared.main:app", "--host", "0.0.0.0", "--port", "8000"]
