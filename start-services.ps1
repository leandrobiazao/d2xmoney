# Start script for d2xmoney backend and frontend services
# This script starts both services in the background

Write-Host "=== Starting d2xmoney Services ===" -ForegroundColor Cyan
Write-Host ""

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"
$venvPath = Join-Path $backendPath "venv"

# Check if setup has been run
if (-not (Test-Path $venvPath)) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "  Please run setup-services.ps1 first" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path (Join-Path $frontendPath "node_modules"))) {
    Write-Host "[ERROR] Frontend dependencies not installed!" -ForegroundColor Red
    Write-Host "  Please run setup-services.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Start backend server
Write-Host "Starting backend server (port 8000)..." -ForegroundColor Yellow
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$backendJob = Start-Job -ScriptBlock {
    param($pythonPath, $backendPath)
    Set-Location $backendPath
    & $pythonPath manage.py runserver
} -ArgumentList $venvPython, $backendPath

Start-Sleep -Seconds 2
if ($backendJob.State -eq "Running") {
    Write-Host "[OK] Backend server started (Job ID: $($backendJob.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Backend server may have issues starting. Check logs." -ForegroundColor Yellow
}

# Start frontend server
Write-Host "Starting frontend server (port 4400)..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    param($frontendPath)
    Set-Location $frontendPath
    npm start
} -ArgumentList $frontendPath

Start-Sleep -Seconds 3
if ($frontendJob.State -eq "Running") {
    Write-Host "[OK] Frontend server started (Job ID: $($frontendJob.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Frontend server may have issues starting. Check logs." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Services Started ===" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend App: http://localhost:4400" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view service logs:" -ForegroundColor Yellow
Write-Host "  Receive-Job -Id $($backendJob.Id)   # Backend logs" -ForegroundColor White
Write-Host "  Receive-Job -Id $($frontendJob.Id)   # Frontend logs" -ForegroundColor White
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Yellow
Write-Host "  Stop-Job -Id $($backendJob.Id), $($frontendJob.Id)" -ForegroundColor White
Write-Host "  Remove-Job -Id $($backendJob.Id), $($frontendJob.Id)" -ForegroundColor White
Write-Host ""
Write-Host "Job IDs saved to: .service-jobs.txt" -ForegroundColor Gray

# Save job IDs to file for easy reference
@{
    BackendJobId = $backendJob.Id
    FrontendJobId = $frontendJob.Id
} | ConvertTo-Json | Out-File -FilePath ".service-jobs.txt" -Encoding utf8

Write-Host ""
Write-Host "Services are running in the background. Press Ctrl+C to exit this script (services will continue running)." -ForegroundColor Gray
Write-Host ""

# Keep script running to show status
try {
    while ($true) {
        $backendStatus = (Get-Job -Id $backendJob.Id).State
        $frontendStatus = (Get-Job -Id $frontendJob.Id).State
        
        Write-Host "`r[Backend: $backendStatus] [Frontend: $frontendStatus]" -NoNewline -ForegroundColor Gray
        Start-Sleep -Seconds 5
        
        # Check if jobs failed
        if ($backendStatus -eq "Failed" -or $frontendStatus -eq "Failed") {
            Write-Host ""
            Write-Host "[WARNING] One or more services have failed. Check logs with Receive-Job" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host ""
    Write-Host "Monitoring stopped. Services continue running in background." -ForegroundColor Gray
}

