<#
.SYNOPSIS
    Stop the API and frontend that scripts\start-product.ps1 started.

.DESCRIPTION
    Stops the recorded process ids and their children, and then sweeps for any server
    process still belonging to this repository.

    The sweep is not belt-and-braces; it is the part that actually works for the frontend.
    `pnpm` on Windows is a `.cmd` shim: it spawns Node and exits immediately, so the pid
    written at start-up is dead within a second while the Node server it launched keeps
    listening with no parent to walk down from. Stopping only the recorded pid tree left
    port 3000 served by an orphan, and the next start-up then silently reused the previous
    build.

    The sweep is scoped by command line to this repository's own directory, so it cannot
    touch an unrelated Node or uvicorn process on the same machine.

    A pid file naming a process that is already gone is not an error -- it is the ordinary
    state after a crash, a machine restart, or the shim exiting -- so those are reported and
    cleaned up rather than failed on.

    Neo4j is never touched. This script did not start it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runDir = Join-Path $root '.tmp'
$frontendDir = Join-Path $root 'frontend'

function Stop-Tree {
    param([int]$ProcessId)
    # Depth-first: children before the parent, so a supervisor cannot respawn a child we
    # have already stopped.
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-Tree -ProcessId $child.ProcessId
    }
    try {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

$stopped = 0

# --- 1. The recorded pids --------------------------------------------------

foreach ($service in @('api', 'frontend')) {
    $pidFile = Join-Path $runDir "$service.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Host ("  {0,-9} no pid file recorded" -f $service) -ForegroundColor DarkGray
        continue
    }
    $raw = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $parsed = 0
    if (-not [int]::TryParse($raw, [ref]$parsed)) {
        Write-Host ("  {0,-9} pid file unreadable; removing it" -f $service) -ForegroundColor Yellow
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        continue
    }
    if (Get-Process -Id $parsed -ErrorAction SilentlyContinue) {
        if (Stop-Tree -ProcessId $parsed) {
            Write-Host ("  {0,-9} stopped (pid {1} and children)" -f $service, $parsed) -ForegroundColor Green
            $stopped++
        } else {
            Write-Host ("  {0,-9} could not stop pid {1}" -f $service, $parsed) -ForegroundColor Red
        }
    } else {
        Write-Host ("  {0,-9} recorded pid {1} already gone" -f $service, $parsed) -ForegroundColor DarkGray
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

# --- 2. The sweep, scoped to this repository -------------------------------

# Matched on the command line rather than on process name, because the names are just
# `node` and `python` and this machine may be running either for something else entirely.
$patterns = @(
    @{ Name = 'next';    Match = "*$frontendDir*"; Extra = '*next*' },
    @{ Name = 'uvicorn'; Match = "*$root*";        Extra = '*vedagraph.api*' }
)

$orphans = @()
foreach ($pattern in $patterns) {
    $found = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like $pattern.Match -and
        $_.CommandLine -like $pattern.Extra
    })
    foreach ($process in $found) {
        $orphans += [pscustomobject]@{ Kind = $pattern.Name; ProcessId = $process.ProcessId }
    }
}

foreach ($orphan in $orphans) {
    if (-not (Get-Process -Id $orphan.ProcessId -ErrorAction SilentlyContinue)) { continue }
    if (Stop-Tree -ProcessId $orphan.ProcessId) {
        Write-Host ("  {0,-9} stopped orphan pid {1}" -f $orphan.Kind, $orphan.ProcessId) -ForegroundColor Green
        $stopped++
    }
}

# --- 3. Report what is actually still listening -----------------------------

Start-Sleep -Milliseconds 400
$busy = @()
foreach ($port in @(8000, 3000)) {
    $listening = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
    if ($listening.Count -gt 0) { $busy += $port }
}

Write-Host ''
if ($busy.Count -gt 0) {
    Write-Host ("  Port(s) {0} are still listening. Something outside this repository holds them." -f ($busy -join ', ')) -ForegroundColor Yellow
} elseif ($stopped -gt 0) {
    Write-Host ("  Stopped {0} process(es); ports 8000 and 3000 are clear. Neo4j was not touched." -f $stopped) -ForegroundColor Green
} else {
    Write-Host '  Nothing was running. Neo4j was not touched.' -ForegroundColor DarkGray
}
Write-Host ''
