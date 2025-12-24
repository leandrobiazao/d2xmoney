<# 
Starts backend and frontend in separate PowerShell terminals using the README commands.

Backend: cd backend; .\venv\Scripts\Activate.ps1; python manage.py runserver
Frontend: cd frontend; npm start

Assumes setup-services.ps1 has already been run (venv and node_modules exist).
#>

$rootPath = $PSScriptRoot
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"

$venvActivate = Join-Path $backendPath "venv\Scripts\Activate.ps1"
$frontendNodeModules = Join-Path $frontendPath "node_modules"

if (-not (Test-Path $venvActivate)) {
    Write-Host "[ERROR] Backend virtual environment not found. Run setup-services.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $frontendNodeModules)) {
    Write-Host "[ERROR] Frontend dependencies not installed. Run setup-services.ps1 first." -ForegroundColor Red
    exit 1
}

$shellPath = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $shellPath) {
    $shellPath = (Get-Command powershell -ErrorAction SilentlyContinue)?.Source
}

if (-not $shellPath) {
    Write-Host "[ERROR] Neither pwsh nor powershell is available on PATH." -ForegroundColor Red
    exit 1
}

$backendCommand = "Set-Location `"$backendPath`"; .\venv\Scripts\Activate.ps1; python manage.py runserver"
$frontendCommand = "Set-Location `"$frontendPath`"; npm start"

Write-Host "Opening backend terminal..." -ForegroundColor Cyan
Start-Process $shellPath -ArgumentList "-NoExit", "-Command", $backendCommand

Write-Host "Opening frontend terminal..." -ForegroundColor Cyan
Start-Process $shellPath -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host "Terminals launched. Backend on http://localhost:8000, frontend on http://localhost:4400." -ForegroundColor Green





