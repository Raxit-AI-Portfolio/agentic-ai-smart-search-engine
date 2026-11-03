# Ingests documents/*.md into Qdrant for RAG. Local dev use only.
#
# Usage:
#   .\scripts\ingest-documents-vdb.ps1

# Deliberately NOT setting $ErrorActionPreference = "Stop" — see
# scripts/test-execution.ps1 for why; every step below checks $LASTEXITCODE
# explicitly instead.
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

# --- 1. .env sanity check ---
Write-Step "Checking .env"
if (-not (Test-Path ".env")) {
    throw ".env not found at repo root. Copy .env.example to .env and fill in real values first."
}

# --- 2. Qdrant up ---
Write-Step "Starting qdrant"
docker compose up -d qdrant 2>$null
if ($LASTEXITCODE -ne 0) { throw "docker compose up (qdrant) failed." }

# --- 3. Python deps + RAG ingestion ---
Write-Step "Installing Python dependencies"
python -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

Write-Step "Ingesting RAG documents"
python scripts/ingest_documents.py
if ($LASTEXITCODE -ne 0) { throw "RAG ingestion failed." }

Write-Host "Done."
