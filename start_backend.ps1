# Start Backend Server
Write-Host "Starting NexTraction 2 Backend..." -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"

if (-not (Test-Path "$backendPath\venv\Scripts\Activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: cd backend; python -m venv venv; venv\Scripts\activate; pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Set-Location $backendPath

# Activate venv and start server
& "$backendPath\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

