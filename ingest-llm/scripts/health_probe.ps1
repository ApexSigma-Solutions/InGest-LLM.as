#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Infrastructure health probe script for OmegaKG services.

.DESCRIPTION
    Performs health checks against all OmegaKG microservices and reports
    their status. Exits with code 0 only when all services are healthy.
#>

$ErrorActionPreference = "Stop"

# Service health endpoint mappings
$services = @{
    "ingest_llm" = "http://ingest-llm:8000/health"
    "omega_kg"   = "http://omega-kg:8000/health"
    "memos_mcp"  = "http://memos-mcp:8000/health"
}

$allHealthy = $true

foreach ($service in $services.GetEnumerator()) {
    $name = $service.Key
    $url = $service.Value

    Write-Host "[$name] Checking health at $url..." -ForegroundColor Cyan

    try {
        $response = Invoke-WebRequest -Method Get -Uri $url -TimeoutSec 5

        if ($response.StatusCode -ne 200) {
            Write-Host "[$name] HTTP Error: $($response.StatusCode)" -ForegroundColor Red
            $allHealthy = $false
            continue
        }

        $content = $response.Content | ConvertFrom-Json

        if ($content.upstream -eq "ok") {
            Write-Host "[$name] Healthy - upstream: ok" -ForegroundColor Green
        } else {
            Write-Host "[$name] Degraded - upstream: $($content.upstream)" -ForegroundColor Yellow
            $allHealthy = $false
        }
    } catch [System.Net.WebException] {
        Write-Host "[$name] Connection failed: $($_.Exception.Message)" -ForegroundColor Red
        $allHealthy = $false
    } catch {
        Write-Host "[$name] Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
        $allHealthy = $false
    }
}

if ($allHealthy) {
    Write-Host "`nAll services are healthy." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nOne or more services are unhealthy." -ForegroundColor Red
    exit 1
}
