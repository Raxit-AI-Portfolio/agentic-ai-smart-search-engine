# Starts the full EFSSE stack (infra + integration APIs) and launches the
# Streamlit frontend. Local dev use only.
#
# Usage:
#   .\scripts\app-start.ps1                                 # start stack (no DB reset/rebuild) + launch UI
#   .\scripts\app-start.ps1 -SeedDb                         # also recreate/seed databases first
#   .\scripts\app-start.ps1 -Build                          # rebuild docker images before starting
#   .\scripts\app-start.ps1 -SkipIngest                     # skip RAG document ingestion
#   .\scripts\app-start.ps1 -Port 8600                      # run Streamlit on a different port
#   .\scripts\app-start.ps1 -Clean                          # remove this project's existing containers/images first, then start
#   .\scripts\app-start.ps1 -Clean -SeedDb -Build           # run Streamlit with a fresh DB, rebuilt images, and RAG ingestion
param(
    [switch]$SeedDb,
    [switch]$Build,
    [switch]$SkipIngest,
    [switch]$Clean,
    [int]$Port = 8501
)

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
$envContent = Get-Content ".env" -Raw
if ($envContent -match "CHANGE_ME") {
    Write-Warning ".env still has CHANGE_ME placeholder(s) - schema/docker-compose passwords must match."
}
if ($envContent -notmatch "GOOGLE_API_KEY\s*=\s*\S+") {
    throw "GOOGLE_API_KEY is missing from .env - required for guardrail/planning/synthesis nodes."
}

# --- 1b. Optionally remove this project's existing containers/images ---
if ($Clean) {
    Write-Step "Removing existing containers and images for this project"
    docker compose down --rmi local --remove-orphans 2>$null
    if ($LASTEXITCODE -ne 0) { throw "docker compose down --rmi local failed." }
}

# --- 2. Postgres + Redis up, then optionally (re)seed ---
Write-Step "Starting postgres and redis"
docker compose up -d postgres redis 2>$null
if ($LASTEXITCODE -ne 0) { throw "docker compose up (postgres, redis) failed." }

Write-Step "Waiting for postgres to be healthy"
$deadline = (Get-Date).AddSeconds(60)
do {
    $status = docker inspect --format '{{.State.Health.Status}}' docker-postgre 2>$null
    if ($status -eq "healthy") { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($status -ne "healthy") { throw "postgres did not become healthy within 60s." }

if ($SeedDb) {
    Write-Step "Recreating and seeding databases"
    & "$PSScriptRoot\recreate-databases.ps1"
    if ($LASTEXITCODE -ne 0) { throw "recreate-databases.ps1 failed." }
} else {
    Write-Host "Skipping DB seed (pass -SeedDb to recreate/reseed)."
}

# --- 3. Rest of the stack ---
Write-Step "Bringing up the full stack"
if ($Build) {
    docker compose up -d --build 2>$null
} else {
    docker compose up -d 2>$null
}
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed." }

Write-Step "Waiting for auth-api to accept connections"
$deadline = (Get-Date).AddSeconds(60)
$authApiUrl = "http://localhost:8003/auth/verify"
$authApiUp = $false
do {
    try {
        Invoke-WebRequest -Uri $authApiUrl -Method Post -TimeoutSec 3 -ErrorAction Stop | Out-Null
        $authApiUp = $true
    } catch {
        if ($_.Exception.Response) {
            # A real HTTP response (even 401/422) means the server is up and
            # answering - see scripts/test-execution.ps1 for why this check
            # is needed on Windows PowerShell 5.1.
            $authApiUp = $true
        } else {
            Start-Sleep -Seconds 2
        }
    }
} while (-not $authApiUp -and (Get-Date) -lt $deadline)
if (-not $authApiUp) { Write-Warning "auth-api did not respond within 60s - login may fail until it's up." }

# --- 4. Python deps + RAG ingestion ---
Write-Step "Installing Python dependencies"
python -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

if (-not $SkipIngest) {
    Write-Step "Ingesting RAG documents"
    python scripts/ingest_documents.py
    if ($LASTEXITCODE -ne 0) { throw "RAG ingestion failed." }
} else {
    Write-Host "Skipping RAG ingestion (-SkipIngest)."
}

# --- 5. Launch the Streamlit frontend ---
Write-Step "Launching Streamlit frontend on port $Port"
streamlit run frontend/Smart_Search.py --server.port $Port
