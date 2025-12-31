# Start script for ingest-llm service
$ErrorActionPreference = "Stop"

# Set environment variables
$env:POSTGRES_DSN = "postgresql://omega_user:omega_dev_password@127.0.0.1:5800/omega_kg_stable"
$env:LINEAR_WEBHOOK_SECRET = "76adJqIUya6kXGDbICTRFo38M5H32Koo19t0TbeRY1Y"
$env:CIRCUIT_BREAKER_THRESHOLD = "3"
$env:CIRCUIT_BREAKER_TIMEOUT = "300"

Write-Host "Starting ingest-llm service..."
Write-Host "POSTGRES_DSN: $($env:POSTGRES_DSN)"
Write-Host "Starting uvicorn on port 8766..."
Write-Host ""

poetry run python -m uvicorn ingest_llm.main:app --host 127.0.0.1 --port 8766
