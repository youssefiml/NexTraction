# Ingest content into NexTraction 2
param(
    [Parameter(Mandatory=$true)]
    [string[]]$Urls,
    
    [string[]]$DomainAllowlist = $null,
    [int]$MaxPages = 10,
    [int]$MaxDepth = 2
)

Write-Host "=== Ingesting Content ===" -ForegroundColor Cyan
Write-Host "URLs: $($Urls -join ', ')" -ForegroundColor Yellow
Write-Host "Max Pages: $MaxPages" -ForegroundColor Yellow
Write-Host "Max Depth: $MaxDepth" -ForegroundColor Yellow

$body = @{
    urls = $Urls
    max_pages = $MaxPages
    max_depth = $MaxDepth
}

if ($DomainAllowlist) {
    $body.domain_allowlist = $DomainAllowlist
}

$jsonBody = $body | ConvertTo-Json

try {
    Write-Host "`nStarting ingestion..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/ingest" `
        -Method POST `
        -ContentType "application/json" `
        -Body $jsonBody
    
    $jobId = $response.job_id
    Write-Host "✅ Job created: $jobId" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor Cyan
    
    # Monitor progress
    Write-Host "`nMonitoring progress..." -ForegroundColor Cyan
    $maxWait = 300  # 5 minutes
    $waited = 0
    
    do {
        Start-Sleep -Seconds 3
        $waited += 3
        
        $status = Invoke-RestMethod -Uri "http://localhost:8000/api/ingest/$jobId" -Method GET
        
        $progressPercent = [math]::Round($status.progress * 100)
        Write-Host "   Progress: $progressPercent% - Pages: $($status.pages_processed)/$($status.total_pages) - Status: $($status.status)" -ForegroundColor Cyan
        
        if ($status.status -eq "completed") {
            Write-Host "`n✅ Ingestion completed!" -ForegroundColor Green
            Write-Host "   Pages processed: $($status.pages_processed)" -ForegroundColor Cyan
            break
        }
        
        if ($status.status -eq "failed") {
            Write-Host "`n❌ Ingestion failed!" -ForegroundColor Red
            if ($status.error_message) {
                Write-Host "   Error: $($status.error_message)" -ForegroundColor Yellow
            }
            break
        }
        
    } while ($waited -lt $maxWait)
    
    if ($waited -ge $maxWait) {
        Write-Host "`n⏱️ Timeout waiting for completion" -ForegroundColor Yellow
    }
    
    # Check final metrics
    $metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/metrics" -Method GET
    Write-Host "`n=== Final Metrics ===" -ForegroundColor Cyan
    Write-Host "   Total pages indexed: $($metrics.total_pages_indexed)" -ForegroundColor $(if ($metrics.total_pages_indexed -gt 0) { "Green" } else { "Red" })
    Write-Host "   Index size: $($metrics.index_size_mb) MB" -ForegroundColor Cyan
    
} catch {
    Write-Host "`n❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        $errorJson = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "   Detail: $($errorJson.detail)" -ForegroundColor Yellow
    }
}

