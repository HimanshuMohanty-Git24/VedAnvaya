<#
.SYNOPSIS
    Start VedaGraph locally: the API, the frontend, and a readiness check on each.

.DESCRIPTION
    One command instead of the several a developer would otherwise have to remember, in the
    right order, from the right directories.

    It runs the doctor first and stops if a REQUIRED check fails, because every failure mode
    the doctor catches produces a *worse* symptom later: an unloaded graph looks like an
    empty corpus, a missing frontend install looks like a connection refused. Pass
    -SkipDoctor to start anyway.

    Neo4j is checked and never started or migrated. The database is managed outside this
    repository (see infra\docker-compose.neo4j.yml) and a start script that silently brought
    up or mutated a graph this product treats as frozen would be the wrong kind of
    convenient.

    A missing LLM key is not an error. The browsing product -- corpus, search, graph,
    cross-Veda, audio -- works entirely without one, and Ask VedaGraph reports
    NOT_CONFIGURED rather than taking the product down with it.

.PARAMETER SkipDoctor
    Start without the preflight checks.

.PARAMETER ApiOnly
    Start the API and not the frontend.

.PARAMETER Production
    Build the frontend and serve the built output instead of running the dev server.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipDoctor,
    [switch]$ApiOnly,
    [switch]$Production
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runDir = Join-Path $root '.tmp'
$null = New-Item -ItemType Directory -Force -Path $runDir

if (-not $SkipDoctor) {
    Write-Host 'Preflight...' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\doctor.ps1')
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host 'Not starting: a required check failed above. Use -SkipDoctor to override.' -ForegroundColor Red
        exit 1
    }
}

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'No .venv interpreter. Run: uv sync --extra dev' -ForegroundColor Red
    exit 1
}

# --- API -------------------------------------------------------------------

$apiLog = Join-Path $runDir 'api.log'
Write-Host 'Starting the API on http://127.0.0.1:8000 ...' -ForegroundColor Cyan
$api = Start-Process -FilePath $python `
    -ArgumentList @('-m', 'uvicorn', 'vedagraph.api.app:app', '--host', '127.0.0.1', '--port', '8000') `
    -WorkingDirectory $root `
    -RedirectStandardOutput $apiLog `
    -RedirectStandardError (Join-Path $runDir 'api.err.log') `
    -PassThru -WindowStyle Hidden
Set-Content -LiteralPath (Join-Path $runDir 'api.pid') -Value $api.Id -Encoding ascii

# Poll /ready rather than sleeping a fixed interval. /ready checks connectivity, the
# ontology version and the four works, so a 200 here means the product can actually answer
# rather than merely that a port opened.
$ready = $false
for ($attempt = 1; $attempt -le 40; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/ready' -UseBasicParsing -TimeoutSec 4
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        if ($api.HasExited) { break }
    }
}

if ($ready) {
    Write-Host '  API ready.' -ForegroundColor Green
} elseif ($api.HasExited) {
    Write-Host '  API exited during startup. Last lines of its log:' -ForegroundColor Red
    if (Test-Path $apiLog) { Get-Content -LiteralPath $apiLog -Tail 15 }
    if (Test-Path (Join-Path $runDir 'api.err.log')) { Get-Content -LiteralPath (Join-Path $runDir 'api.err.log') -Tail 15 }
    exit 1
} else {
    Write-Host '  API did not report ready in 20s. It may still be starting; see .tmp\api.log' -ForegroundColor Yellow
}

if ($ApiOnly) {
    Write-Host ''
    Write-Host '  API      http://127.0.0.1:8000' -ForegroundColor Green
    Write-Host '  API docs http://127.0.0.1:8000/docs' -ForegroundColor Green
    Write-Host '  Stop it  scripts\stop-product.ps1' -ForegroundColor DarkGray
    exit 0
}

# --- Frontend --------------------------------------------------------------

$frontend = Join-Path $root 'frontend'
$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpm) {
    Write-Host 'pnpm is not on PATH; the API is running but the frontend was not started.' -ForegroundColor Yellow
    exit 1
}

if ($Production) {
    Write-Host 'Building the frontend...' -ForegroundColor Cyan
    Push-Location $frontend
    & pnpm build
    $buildCode = $LASTEXITCODE
    Pop-Location
    if ($buildCode -ne 0) {
        Write-Host 'The frontend build failed; the API is still running.' -ForegroundColor Red
        exit 1
    }
    $script = 'start'
} else {
    $script = 'dev'
}

Write-Host "Starting the frontend on http://localhost:3000 (pnpm $script) ..." -ForegroundColor Cyan
$web = Start-Process -FilePath $pnpm.Source `
    -ArgumentList @($script) `
    -WorkingDirectory $frontend `
    -RedirectStandardOutput (Join-Path $runDir 'frontend.log') `
    -RedirectStandardError (Join-Path $runDir 'frontend.err.log') `
    -PassThru -WindowStyle Hidden
Set-Content -LiteralPath (Join-Path $runDir 'frontend.pid') -Value $web.Id -Encoding ascii

$webUp = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 4
        if ($response.StatusCode -eq 200) { $webUp = $true; break }
    } catch {
        if ($web.HasExited) { break }
    }
}

Write-Host ''
if ($webUp) {
    Write-Host '  VedaGraph  http://localhost:3000' -ForegroundColor Green
} elseif ($web.HasExited) {
    Write-Host '  The frontend exited during startup. See .tmp\frontend.err.log' -ForegroundColor Red
} else {
    Write-Host '  Frontend still compiling. It will answer on http://localhost:3000 shortly.' -ForegroundColor Yellow
}
Write-Host '  API        http://127.0.0.1:8000' -ForegroundColor Green
Write-Host '  API docs   http://127.0.0.1:8000/docs' -ForegroundColor Green
Write-Host ''
Write-Host '  Logs       .tmp\api.log, .tmp\frontend.log' -ForegroundColor DarkGray
Write-Host '  Stop it    scripts\stop-product.ps1' -ForegroundColor DarkGray
Write-Host ''
