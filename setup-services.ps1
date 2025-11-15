# Setup script for d2xmoney backend and frontend services
# This script checks prerequisites and installs dependencies

Write-Host "=== d2xmoney Service Setup ===" -ForegroundColor Cyan
Write-Host ""

# Function to check if a command exists
function Test-Command {
    param([string]$Command)
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    return ($null -ne $cmd)
}

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = $null
if (Test-Command "python") {
    try {
        $version = python --version 2>&1
        if ($version -notmatch "was not found") {
            $pythonCmd = "python"
            Write-Host "[OK] Python found: $version" -ForegroundColor Green
        }
    } catch {
        # Python stub might be present
    }
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeCmd = $null
if (Test-Command "node") {
    try {
        $version = node --version 2>&1
        if ($version -notmatch "was not found") {
            $nodeCmd = "node"
            Write-Host "[OK] Node.js found: $version" -ForegroundColor Green
        }
    } catch {
    }
}

if (-not $nodeCmd) {
    Write-Host "[ERROR] Node.js not found!" -ForegroundColor Red
    Write-Host "  Please install Node.js from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "  The LTS version is recommended" -ForegroundColor Yellow
    exit 1
}

# Check npm
Write-Host "Checking npm installation..." -ForegroundColor Yellow
if (Test-Command "npm") {
    $npmVersion = npm --version
    Write-Host "[OK] npm found: v$npmVersion" -ForegroundColor Green
} else {
    Write-Host "[ERROR] npm not found!" -ForegroundColor Red
    Write-Host "  npm should come with Node.js. Please reinstall Node.js." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=== Setting up Backend ===" -ForegroundColor Cyan

# Setup backend virtual environment
$backendPath = Join-Path $PSScriptRoot "backend"
$venvPath = Join-Path $backendPath "venv"

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    & $pythonCmd -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment already exists" -ForegroundColor Green
}

# Activate venv and install requirements
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Host "[ERROR] Virtual environment activation script not found!" -ForegroundColor Red
    exit 1
}

# Install requirements using the venv's pip
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
if (Test-Path $venvPip) {
    & $venvPip install -r (Join-Path $backendPath "requirements.txt") --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install backend dependencies!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Backend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] pip not found in virtual environment!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Setting up Frontend ===" -ForegroundColor Cyan

# Install frontend dependencies
$frontendPath = Join-Path $PSScriptRoot "frontend"
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location $frontendPath
npm install --silent
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install frontend dependencies!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== Running Database Migrations ===" -ForegroundColor Cyan
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (Test-Path $venvPython) {
    Set-Location $backendPath
    & $venvPython manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Migrations may have failed, but continuing..." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Database migrations completed" -ForegroundColor Green
    }
    Set-Location $PSScriptRoot
}

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To start the services, run:" -ForegroundColor Cyan
Write-Host "  .\start-services.ps1" -ForegroundColor White
Write-Host ""

