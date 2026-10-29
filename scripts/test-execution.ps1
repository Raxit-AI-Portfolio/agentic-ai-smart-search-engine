# Runs everything tests/test_execution.md describes by hand: brings up the
# stack, (re)seeds the databases, ingests the RAG docs, and runs the
# integration tests. Local dev use only.
#
# Usage:
#   .\scripts\test-execution.ps1                  # full reset + run
#   .\scripts\test-execution.ps1 -SkipDbReset      # keep existing DB data
#   .\scripts\test-execution.ps1 -SkipIngest       # skip RAG (re)ingestion
#   .\scripts\test-execution.ps1 -SkipBuild        # don't rebuild images first
#   .\scripts\test-execution.ps1 -TestArgs "-k customer"   # extra pytest args

param(
    [switch]$SkipDbReset,
    [switch]$SkipIngest,
    [switch]$SkipBuild,
    [string]$TestArgs = ""
)

# Deliberately NOT setting $ErrorActionPreference = "Stop": docker compose
# writes normal progress lines to stderr, and Stop treats any native-command
# stderr line as a terminating error even on success. Every step below checks
# $LASTEXITCODE explicitly instead.
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

# --- 1. .env sanity check (can't fill it in for you, just flag the obvious) ---
Write-Step "Checking .env"
if (-not (Test-Path ".env")) {
    throw ".env not found at repo root. Copy .env.example to .env and fill in real values first."
}
$envContent = Get-Content ".env" -Raw
if ($envContent -match "CHANGE_ME") {
    Write-Warning ".env still has CHANGE_ME placeholder(s) - schema/docker-compose passwords must match. See tests/test_execution.md."
}
if ($envContent -notmatch "GOOGLE_API_KEY\s*=\s*\S+") {
    throw "GOOGLE_API_KEY is missing from .env - required for planning_node/synthesis_node (every graph run needs it)."
}

# --- 2. Postgres + Redis up, then (re)seed ---
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

if (-not $SkipDbReset) {
    Write-Step "Recreating and seeding databases"
    & "$PSScriptRoot\recreate-databases.ps1"
    if ($LASTEXITCODE -ne 0) { throw "recreate-databases.ps1 failed." }
} else {
    Write-Host "Skipping DB reset (-SkipDbReset)."
}

# --- 3. Rest of the stack ---
Write-Step "Bringing up the full stack"
if ($SkipBuild) {
    docker compose up -d 2>$null
} else {
    # Rebuild first - a container running a stale image (built before a code
    # change) is a recurring, confusing failure mode; always rebuilding here
    # is cheap once Docker's layer cache is warm.
    docker compose up -d --build 2>$null
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
            # answering - Windows PowerShell 5.1's Invoke-WebRequest throws
            # WebException for both connection-refused AND non-2xx status,
            # so this is the only reliable way to tell them apart.
            $authApiUp = $true
        } else {
            Start-Sleep -Seconds 2
        }
    }
} while (-not $authApiUp -and (Get-Date) -lt $deadline)
if (-not $authApiUp) { Write-Warning "auth-api did not respond within 60s - tests may fail at the login fixture." }

# --- 4. Python deps + RAG ingestion ---
Write-Step "Installing Python test dependencies"
python -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

if (-not $SkipIngest) {
    Write-Step "Ingesting RAG documents"
    python scripts/ingest_documents.py
    if ($LASTEXITCODE -ne 0) { throw "RAG ingestion failed." }
} else {
    Write-Host "Skipping RAG ingestion (-SkipIngest)."
}

# --- 5. Run the integration tests ---
Write-Step "Running integration tests"
$pytestArgs = @("-m", "pytest", "tests/integration_tests", "-v")
if ($TestArgs) { $pytestArgs += $TestArgs.Split(" ") }
python @pytestArgs
exit $LASTEXITCODE
