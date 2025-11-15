# Stop script for d2xmoney backend and frontend services

Write-Host "=== Stopping d2xmoney Services ===" -ForegroundColor Cyan
Write-Host ""

$jobsFile = Join-Path $PSScriptRoot ".service-jobs.txt"

if (Test-Path $jobsFile) {
    $jobs = Get-Content $jobsFile | ConvertFrom-Json
    $backendJobId = $jobs.BackendJobId
    $frontendJobId = $jobs.FrontendJobId
    
    Write-Host "Stopping backend server (Job ID: $backendJobId)..." -ForegroundColor Yellow
    Stop-Job -Id $backendJobId -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJobId -ErrorAction SilentlyContinue
    
    Write-Host "Stopping frontend server (Job ID: $frontendJobId)..." -ForegroundColor Yellow
    Stop-Job -Id $frontendJobId -ErrorAction SilentlyContinue
    Remove-Job -Id $frontendJobId -ErrorAction SilentlyContinue
    
    Remove-Item $jobsFile -ErrorAction SilentlyContinue
    Write-Host "✓ Services stopped" -ForegroundColor Green
} else {
    Write-Host "No running services found (jobs file not found)" -ForegroundColor Yellow
    Write-Host "Checking for any running jobs..." -ForegroundColor Yellow
    
    $allJobs = Get-Job
    if ($allJobs) {
        Write-Host "Found $($allJobs.Count) job(s). Stopping all..." -ForegroundColor Yellow
        Stop-Job $allJobs
        Remove-Job $allJobs
        Write-Host "✓ All jobs stopped" -ForegroundColor Green
    } else {
        Write-Host "No jobs found running" -ForegroundColor Gray
    }
}

Write-Host ""


