# InGest-LLM.as File Processing and Cleanup Script
# Processes files in .ingest/raw_documents and manages lifecycle

param(
    [string]$Action = "process", # process, cleanup, status
    [switch]$Archive = $false,   # Archive processed files instead of deleting
    [switch]$DryRun = $false     # Show what would be done without doing it
)

$IngestDir = "C:\Users\steyn\ApexSigmaProjects.Dev\InGest-LLM.as\.ingest"
$RawDocuments = Join-Path $IngestDir "raw_documents"
$ArchiveDir = Join-Path $IngestDir ".archive"
$ProcessedDir = Join-Path $ArchiveDir "processed"
$FailedDir = Join-Path $ArchiveDir "failed"

# Ensure archive directories exist if archiving is enabled
if ($Archive) {
    if (-not (Test-Path $ArchiveDir)) { New-Item -ItemType Directory -Path $ArchiveDir -Force }
    if (-not (Test-Path $ProcessedDir)) { New-Item -ItemType Directory -Path $ProcessedDir -Force }
    if (-not (Test-Path $FailedDir)) { New-Item -ItemType Directory -Path $FailedDir -Force }
}

function Process-Document {
    param($FilePath, $FileType)

    $fileName = Split-Path $FilePath -Leaf
    Write-Host "Processing: $fileName ($FileType)" -ForegroundColor Yellow

    try {
        $content = Get-Content $FilePath -Raw

        # Determine appropriate endpoint and content type
        $contentType = switch ($FileType) {
            ".py" { "code" }
            ".md" { "markdown" }
            ".txt" { "text" }
            ".json" { "json" }
            ".poml" { "markdown" }  # POML treated as markdown
            default { "text" }
        }

        $request = @{
            content = $content
            metadata = @{
                source = "upload"
                content_type = $contentType
                title = $fileName
                source_url = $FilePath
            }
            memory_tier = if ($contentType -eq "code") { "PROCEDURAL" } else { "SEMANTIC" }
            process_async = $false
            chunk_size = 4000
        } | ConvertTo-Json -Depth 10

        # Send to InGest-LLM API
        $response = $request | curl -X POST "http://localhost:8000/ingest/text" -H "Content-Type: application/json" -d "@-" 2>$null

        if ($LASTEXITCODE -eq 0) {
            $responseObj = $response | ConvertFrom-Json
            if ($responseObj.status -eq "COMPLETED") {
                Write-Host "✅ Successfully processed: $fileName" -ForegroundColor Green
                return "SUCCESS"
            } else {
                Write-Host "⚠️  Processing incomplete: $fileName - $($responseObj.message)" -ForegroundColor Yellow
                return "PARTIAL"
            }
        } else {
            Write-Host "❌ Failed to process: $fileName" -ForegroundColor Red
            return "FAILED"
        }
    }
    catch {
        Write-Host "❌ Error processing $fileName`: $($_.Exception.Message)" -ForegroundColor Red
        return "FAILED"
    }
}

function Move-ProcessedFile {
    param($FilePath, $Status)

    $fileName = Split-Path $FilePath -Leaf

    if ($DryRun) {
        switch ($Status) {
            "SUCCESS" {
                if ($Archive) {
                    Write-Host "Would move $fileName to archive/processed/" -ForegroundColor Cyan
                } else {
                    Write-Host "Would delete $fileName" -ForegroundColor Cyan
                }
            }
            "FAILED" {
                if ($Archive) {
                    Write-Host "Would move $fileName to archive/failed/" -ForegroundColor Cyan
                } else {
                    Write-Host "Would keep $fileName in raw_documents/" -ForegroundColor Cyan
                }
            }
        }
        return
    }

    switch ($Status) {
        "SUCCESS" {
            if ($Archive) {
                $destination = Join-Path $ProcessedDir $fileName
                Move-Item $FilePath $destination -Force
                Write-Host "📁 Archived: $fileName" -ForegroundColor Blue
            } else {
                Remove-Item $FilePath -Force
                Write-Host "🗑️  Removed: $fileName" -ForegroundColor Gray
            }
        }
        "FAILED" {
            if ($Archive) {
                $destination = Join-Path $FailedDir $fileName
                Move-Item $FilePath $destination -Force
                Write-Host "📁 Moved to failed: $fileName" -ForegroundColor Red
            }
            # Keep failed files in raw_documents for retry
        }
    }
}

# Main processing logic
switch ($Action) {
    "process" {
        Write-Host "🚀 Starting file processing..." -ForegroundColor Green

        # Check if InGest-LLM service is running
        try {
            $healthCheck = curl -X GET "http://localhost:8000/health" 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ InGest-LLM service not available. Please start the service first." -ForegroundColor Red
                exit 1
            }
        }
        catch {
            Write-Host "❌ Cannot connect to InGest-LLM service" -ForegroundColor Red
            exit 1
        }

        # Find all files in raw_documents
        $files = Get-ChildItem -Path $RawDocuments -File -Recurse

        if ($files.Count -eq 0) {
            Write-Host "ℹ️  No files found in raw_documents directory" -ForegroundColor Yellow
            exit 0
        }

        Write-Host "Found $($files.Count) files to process" -ForegroundColor Cyan

        $processed = 0
        $succeeded = 0
        $failed = 0

        foreach ($file in $files) {
            $status = Process-Document -FilePath $file.FullName -FileType $file.Extension
            Move-ProcessedFile -FilePath $file.FullName -Status $status

            $processed++
            if ($status -eq "SUCCESS") { $succeeded++ }
            if ($status -eq "FAILED") { $failed++ }
        }

        Write-Host "`n📊 Processing Summary:" -ForegroundColor Cyan
        Write-Host "   Total files: $processed" -ForegroundColor White
        Write-Host "   Successful: $succeeded" -ForegroundColor Green
        Write-Host "   Failed: $failed" -ForegroundColor Red
    }

    "cleanup" {
        Write-Host "🧹 Manual cleanup mode" -ForegroundColor Yellow
        $files = Get-ChildItem -Path $RawDocuments -File -Recurse
        Write-Host "Files in raw_documents: $($files.Count)"

        foreach ($file in $files) {
            Write-Host "  - $($file.Name)" -ForegroundColor Gray
        }

        if ($files.Count -gt 0) {
            $response = Read-Host "Remove all files? (y/N)"
            if ($response -eq "y" -or $response -eq "Y") {
                $files | Remove-Item -Force
                Write-Host "✅ Cleaned up $($files.Count) files" -ForegroundColor Green
            }
        }
    }

    "status" {
        Write-Host "📋 InGest Directory Status:" -ForegroundColor Cyan

        $rawFiles = Get-ChildItem -Path $RawDocuments -File -Recurse -ErrorAction SilentlyContinue
        Write-Host "Raw documents pending: $($rawFiles.Count)" -ForegroundColor Yellow

        if (Test-Path $ProcessedDir) {
            $processedFiles = Get-ChildItem -Path $ProcessedDir -File -Recurse -ErrorAction SilentlyContinue
            Write-Host "Processed (archived): $($processedFiles.Count)" -ForegroundColor Green
        }

        if (Test-Path $FailedDir) {
            $failedFiles = Get-ChildItem -Path $FailedDir -File -Recurse -ErrorAction SilentlyContinue
            Write-Host "Failed (archived): $($failedFiles.Count)" -ForegroundColor Red
        }
    }
}
