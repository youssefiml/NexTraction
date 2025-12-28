# Ask a question to NexTraction 2 API
param(
    [Parameter(Mandatory=$true)]
    [string]$Question,
    
    [int]$TopK = 5,
    [double]$MinConfidence = 0.7
)

Write-Host "=== Asking Question ===" -ForegroundColor Cyan
Write-Host "Question: $Question" -ForegroundColor Yellow

# Check if content is indexed
Write-Host "`nChecking if content is indexed..." -ForegroundColor Cyan
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/metrics" -Method GET

if ($metrics.total_pages_indexed -eq 0) {
    Write-Host "❌ No content indexed yet!" -ForegroundColor Red
    Write-Host "`nPlease ingest content first:" -ForegroundColor Yellow
    Write-Host "  1. Go to http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  2. Click 'Ingest Content'" -ForegroundColor Cyan
    Write-Host "  3. Add a URL and start ingestion" -ForegroundColor Cyan
    Write-Host "`nOr use API:" -ForegroundColor Yellow
    Write-Host '  $body = @{ urls = @("https://example.com"); max_pages = 5 } | ConvertTo-Json' -ForegroundColor Gray
    Write-Host '  Invoke-RestMethod -Uri "http://localhost:8000/api/ingest" -Method POST -ContentType "application/json" -Body $body' -ForegroundColor Gray
    exit 1
}

Write-Host "✅ Content indexed: $($metrics.total_pages_indexed) pages" -ForegroundColor Green

# Ask question
Write-Host "`nSending question..." -ForegroundColor Cyan
$body = @{
    question = $Question
    top_k = $TopK
    min_confidence = $MinConfidence
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/ask" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "`n=== Answer ===" -ForegroundColor Green
    Write-Host $response.answer -ForegroundColor White
    Write-Host "`n=== Confidence ===" -ForegroundColor Cyan
    Write-Host "$([math]::Round($response.confidence * 100))%" -ForegroundColor $(if ($response.confidence -ge 0.7) { "Green" } else { "Yellow" })
    Write-Host "`n=== Citations ($($response.citations.Count)) ===" -ForegroundColor Cyan
    
    $i = 1
    foreach ($citation in $response.citations) {
        Write-Host "`n[$i] $($citation.title)" -ForegroundColor Yellow
        Write-Host "   URL: $($citation.url)" -ForegroundColor Gray
        Write-Host "   Excerpt: $($citation.excerpt)" -ForegroundColor Gray
        Write-Host "   Relevance: $([math]::Round($citation.relevance_score * 100))%" -ForegroundColor Cyan
        $i++
    }
    
    if ($response.missing_information) {
        Write-Host "`n=== Missing Information ===" -ForegroundColor Yellow
        foreach ($info in $response.missing_information) {
            Write-Host "  - $info" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n=== Processing Time ===" -ForegroundColor Cyan
    Write-Host "$([math]::Round($response.processing_time_ms, 2)) ms" -ForegroundColor Gray
    
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $errorBody = $reader.ReadToEnd()
    
    Write-Host "`n❌ Error $statusCode" -ForegroundColor Red
    $errorJson = $errorBody | ConvertFrom-Json
    Write-Host $errorJson.detail -ForegroundColor Yellow
}

