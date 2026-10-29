# Build context is the repo root (see docker-compose.yaml), consistent with
# the other services — this one imports integration.shared.cache, plus
# customer-api's and operations-api's `app` objects (for route reflection in
# loader.py's _load_api_permissions) without ever opening their DB pools.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY integration/__init__.py integration/__init__.py
COPY integration/shared integration/shared
COPY integration/customer integration/customer
COPY integration/operation integration/operation
COPY integration/caching_worker integration/caching_worker

CMD ["python", "-m", "integration.caching_worker.main"]
