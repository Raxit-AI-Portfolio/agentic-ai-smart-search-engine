# Drops and recreates customerdb, operationsdb, and membershipdb on the
# docker-postgre container, then reapplies their schema and seed scripts.
# Local dev use only. Reads POSTGRES_PASSWORD from .env, same as app-start.ps1
# (see project-notes/DbSetup.md for the generic, placeholder version of these
# commands).

$ErrorActionPreference = "Stop"

$Container = "docker-postgre"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    throw ".env not found at repo root. Copy .env.example to .env and fill in real values first."
}
$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "POSTGRES_PASSWORD\s*=\s*(\S+)") {
    throw "POSTGRES_PASSWORD is missing from .env."
}
$PgPassword = $Matches[1]

$env:PGPASSWORD = $PgPassword

function Invoke-Psql {
    param([string]$Database, [string]$Command)
    docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d $Database -c $Command
}

Write-Host "Terminating existing connections..."
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IN ('customerdb','operationsdb','membershipdb') AND pid <> pg_backend_pid();"

Write-Host "Dropping existing databases..."
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "DROP DATABASE IF EXISTS customerdb;"
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "DROP DATABASE IF EXISTS operationsdb;"
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "DROP DATABASE IF EXISTS membershipdb;"

Write-Host "Creating databases..."
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "CREATE DATABASE customerdb;"
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "CREATE DATABASE operationsdb;"
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -c "CREATE DATABASE membershipdb;"

Write-Host "Copying schema and seed scripts into the container..."
docker cp "$ProjectRoot\integration\customer\db\customerdb_schema.sql" "${Container}:/tmp/customerdb_schema.sql"
docker cp "$ProjectRoot\integration\customer\db\customerdb_seed.sql" "${Container}:/tmp/customerdb_seed.sql"
docker cp "$ProjectRoot\integration\operation\db\operationsdb_schema.sql" "${Container}:/tmp/operationsdb_schema.sql"
docker cp "$ProjectRoot\integration\operation\db\operationsdb_seed.sql" "${Container}:/tmp/operationsdb_seed.sql"
docker cp "$ProjectRoot\integration\shared\db\membershipdb_schema.sql" "${Container}:/tmp/membershipdb_schema.sql"
docker cp "$ProjectRoot\integration\shared\db\membershipdb_seed.sql" "${Container}:/tmp/membershipdb_seed.sql"

Write-Host "Applying schemas and seed data..."
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d customerdb -f /tmp/customerdb_schema.sql
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d customerdb -f /tmp/customerdb_seed.sql
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d operationsdb -f /tmp/operationsdb_schema.sql
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d operationsdb -f /tmp/operationsdb_seed.sql
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d membershipdb -f /tmp/membershipdb_schema.sql
docker exec -e PGPASSWORD=$PgPassword $Container psql -U postgres -d membershipdb -f /tmp/membershipdb_seed.sql

Write-Host "Done."
