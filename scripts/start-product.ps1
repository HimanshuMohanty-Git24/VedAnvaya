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

    Both servers are launched detached, through a generated .cmd shim. See Start-Detached
    for why: PowerShell's own output redirection keeps this script alive for as long as the
    server writes, which means it never returns to the prompt.

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

function Start-Detached {
    <#
        Launch a long-lived server without tying this script's lifetime to it.

        `Start-Process -RedirectStandardOutput` makes PowerShell hold the child's output
        handles and then wait for them to close, so a script that starts `next dev` that way
        never returns to the prompt even though the server is up and answering. Measured:
        the API alone returned fine, the dev server did not.

        So the command and its redirection are written into a .cmd shim and cmd.exe is
        launched on that. cmd owns the pipe, the log file still gets written, and this
        script keeps no handle at all. Writing a shim rather than passing a quoted `/c`
        string also avoids a layer of PowerShell-to-cmd quote escaping that is easy to get
        subtly wrong for paths containing spaces.

        The pid returned is cmd's, not the server's -- which is why stop-product.ps1 sweeps
        by command line instead of trusting the recorded pid alone.
    #>
    param(
        [string]$Name,
        [string]$Command,
        [string]$WorkingDirectory,
        [string]$LogPath
    )
    $shim = Join-Path $runDir "$Name.cmd"
    $lines = @(
        '@echo off',
        "cd /d `"$WorkingDirectory`"",
        "$Command > `"$LogPath`" 2>&1"
    )
    Set-Content -LiteralPath $shim -Value $lines -Encoding ascii
    return Start-Process -FilePath $env:ComSpec `
        -ArgumentList @('/c', $shim) `
        -WorkingDirectory $WorkingDirectory `
        -PassThru -WindowStyle Hidden
}

function Test-Endpoint {
    param([string]$Url, [int]$Attempts = 40)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) { return $true }
        } catch {
            # Not up yet. Keep waiting; the caller reports the timeout.
        }
    }
    return $false
}

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
$api = Start-Detached -Name 'api' `
    -Command "`"$python`" -m uvicorn vedagraph.api.app:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $root `
    -LogPath $apiLog
Set-Content -LiteralPath (Join-Path $runDir 'api.pid') -Value $api.Id -Encoding ascii

# Poll /ready rather than sleeping a fixed interval. /ready checks connectivity, the
# ontology version and the four works, so a 200 here means the product can actually answer
# rather than merely that a port opened.
if (Test-Endpoint -Url 'http://127.0.0.1:8000/ready') {
    Write-Host '  API ready.' -ForegroundColor Green
} else {
    Write-Host '  API did not report ready in 20s. Last lines of its log:' -ForegroundColor Yellow
    if (Test-Path $apiLog) { Get-Content -LiteralPath $apiLog -Tail 20 }
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

# Resolve something that can actually be launched. `Get-Command pnpm` returns the PowerShell
# shim (pnpm.ps1) first on a standard Node install, and Start-Process refuses it with
# "%1 is not a valid Win32 application" -- so prefer an Application-type command, and the
# .cmd shim where several exist.
$pnpmCandidates = @(Get-Command pnpm -All -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandType -eq 'Application' })
$pnpmPath = $null
foreach ($candidate in $pnpmCandidates) {
    if ($candidate.Source -like '*.cmd') { $pnpmPath = $candidate.Source; break }
}
if (-not $pnpmPath -and $pnpmCandidates.Count -gt 0) { $pnpmPath = $pnpmCandidates[0].Source }
if (-not $pnpmPath) {
    Write-Host 'pnpm is not on PATH; the API is running but the frontend was not started.' -ForegroundColor Yellow
    Write-Host '  Install it with: npm install -g pnpm' -ForegroundColor DarkGray
    exit 1
}

if ($Production) {
    Write-Host 'Building the frontend...' -ForegroundColor Cyan
    Push-Location $frontend
    & $pnpmPath build
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
$web = Start-Detached -Name 'frontend' `
    -Command "`"$pnpmPath`" $script" `
    -WorkingDirectory $frontend `
    -LogPath (Join-Path $runDir 'frontend.log')
Set-Content -LiteralPath (Join-Path $runDir 'frontend.pid') -Value $web.Id -Encoding ascii

$webUp = Test-Endpoint -Url 'http://localhost:3000' -Attempts 90

Write-Host ''
if ($webUp) {
    Write-Host '  VedaGraph  http://localhost:3000' -ForegroundColor Green
} else {
    Write-Host '  Frontend still compiling. It will answer on http://localhost:3000 shortly.' -ForegroundColor Yellow
    Write-Host '  If it does not, see .tmp\frontend.log' -ForegroundColor DarkGray
}
Write-Host '  API        http://127.0.0.1:8000' -ForegroundColor Green
Write-Host '  API docs   http://127.0.0.1:8000/docs' -ForegroundColor Green
Write-Host ''
Write-Host '  Logs       .tmp\api.log, .tmp\frontend.log' -ForegroundColor DarkGray
Write-Host '  Stop it    scripts\stop-product.ps1' -ForegroundColor DarkGray
Write-Host ''
