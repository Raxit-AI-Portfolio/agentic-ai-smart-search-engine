# Build context is the repo root (see docker-compose.yaml). Only needs
# integration.shared.cache (auth status lives in Redis, checked on every
# /auth/verify call) — no other shared submodule.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY integration/__init__.py integration/__init__.py
COPY integration/shared/__init__.py integration/shared/__init__.py
COPY integration/shared/cache integration/shared/cache
COPY integration/auth integration/auth

EXPOSE 8000
CMD ["uvicorn", "integration.auth.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
