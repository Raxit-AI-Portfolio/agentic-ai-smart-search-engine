# Build context is the repo root (see docker-compose.yaml) because this app
# imports integration.shared, not just its own integration/operation package.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY integration/__init__.py integration/__init__.py
COPY integration/shared integration/shared
COPY integration/operation integration/operation

EXPOSE 8000
CMD ["uvicorn", "integration.operation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
