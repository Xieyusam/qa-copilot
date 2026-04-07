# Dev startup script - starts frontend and backend in separate windows
# Usage:
#   .\dev.ps1            - start both
#   .\dev.ps1 -Restart   - kill existing processes then restart
#   .\dev.ps1 -Backend   - backend only
#   .\dev.ps1 -Frontend  - frontend only

param(
    [switch]$Restart,
    [switch]$NoKill,
    [switch]$Reload,
    [switch]$Backend,
    [switch]$Frontend
)

$Root        = $PSScriptRoot
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$BackendPort = 8008

if (-not $Backend -and -not $Frontend) {
    $Backend  = $true
    $Frontend = $true
}

function Kill-Port([int]$Port) {
    $pids = netstat -ano | Select-String ":$Port\s" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique
    foreach ($p in $pids) {
        if ($p -match '^\d+$' -and $p -ne '0') {
            Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($Restart -or -not $NoKill) {
    Write-Host "==> Clearing occupied service ports..." -ForegroundColor Cyan
    if ($Backend)  { Kill-Port $BackendPort; Write-Host "  port $BackendPort cleared" }
    if ($Frontend) { Kill-Port 5173; Write-Host "  port 5173 cleared" }
    Start-Sleep -Seconds 1
}

if ($Backend) {
    Write-Host "==> Starting backend (http://localhost:$BackendPort)" -ForegroundColor Cyan
    $venv = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venv)) {
        Write-Host "  [ERROR] venv not found: $venv" -ForegroundColor Red
        Write-Host "  Run in backend/: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
        exit 1
    }
    $backendCmd = ".venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"
    if ($Reload) {
        $backendCmd = "$backendCmd --reload"
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "cd '$BackendDir'; $backendCmd"
    Write-Host "  backend started" -ForegroundColor Green
}

if ($Frontend) {
    Write-Host "==> Starting frontend (http://localhost:5173)" -ForegroundColor Cyan
    $nm = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nm)) {
        Write-Host "  [ERROR] node_modules not found" -ForegroundColor Red
        Write-Host "  Run in frontend/: npm install"
        exit 1
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "cd '$FrontendDir'; npm run dev"
    Write-Host "  frontend started" -ForegroundColor Green
}

Write-Host ""
Write-Host "Services:" -ForegroundColor Yellow
if ($Backend)  { Write-Host "  Backend   -> http://localhost:$BackendPort" }
if ($Backend)  { Write-Host "  API Docs  -> http://localhost:$BackendPort/docs" }
if ($Frontend) { Write-Host "  Frontend  -> http://localhost:5173" }
