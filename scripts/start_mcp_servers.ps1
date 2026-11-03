# Starts the SQL (8010), RAG (8011) and API (8012) MCP servers, each in its own
# window, and waits until all three accept connections. A server whose port is
# already listening is left alone. Local dev use only.
#
# Usage:
#   .\scripts\start_mcp_servers.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$servers = [ordered]@{ sql_server = 8010; rag_server = 8011; api_server = 8012 }

function Test-Listening($port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

foreach ($name in $servers.Keys) {
    $port = $servers[$name]
    if (Test-Listening $port) {
        Write-Host "$name already listening on $port."
        continue
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; python -m agentic_core.mcp_servers.$name.server"
}

# The RAG server loads the embedding model at startup, so give it time.
$deadline = (Get-Date).AddSeconds(120)
foreach ($name in $servers.Keys) {
    $port = $servers[$name]
    while (-not (Test-Listening $port) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
    if (-not (Test-Listening $port)) { throw "$name did not start listening on port $port within 120s." }
    Write-Host "$name ready on $port."
}
