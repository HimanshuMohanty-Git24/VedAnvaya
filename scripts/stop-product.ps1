<#
.SYNOPSIS
    Stop the API and frontend that scripts\start-product.ps1 started.

.DESCRIPTION
    Reads the process ids written to .tmp and stops those processes and their children.
    Children matter: `pnpm dev` spawns the Next.js server as a separate process, so killing
    only the recorded pid leaves port 3000 held by an orphan and the next start silently
    serves the previous build.

    A pid file naming a process that is already gone is not an error -- it is the ordinary
    state after a crash or a machine restart -- so those are reported and cleaned up rather
    than failed on.

    Neo4j is never touched. This script did not start it.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\stop-product.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runDir = Join-Path $root '.tmp'

function Stop-Tree {
    param([int]$ProcessId)
    # Depth-first: children before the parent, so a parent cannot respawn a child it
    # supervises after we have already stopped it.
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
foreach ($service in @('api', 'frontend')) {
    $pidFile = Join-Path $runDir "$service.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Host ("  {0,-9} no pid file; nothing recorded as running" -f $service) -ForegroundColor DarkGray
        continue
    }
    $raw = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $parsed = 0
    if (-not [int]::TryParse($raw, [ref]$parsed)) {
        Write-Host ("  {0,-9} pid file is unreadable; removing it" -f $service) -ForegroundColor Yellow
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        continue
    }
    $process = Get-Process -Id $parsed -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host ("  {0,-9} pid {1} is not running; clearing the stale pid file" -f $service, $parsed) -ForegroundColor DarkGray
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        continue
    }
    if (Stop-Tree -ProcessId $parsed) {
        Write-Host ("  {0,-9} stopped (pid {1} and children)" -f $service, $parsed) -ForegroundColor Green
        $stopped++
    } else {
        Write-Host ("  {0,-9} could not stop pid {1}" -f $service, $parsed) -ForegroundColor Red
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host ''
if ($stopped -gt 0) {
    Write-Host ("  Stopped {0} service(s). Neo4j was not touched." -f $stopped) -ForegroundColor Green
} else {
    Write-Host '  Nothing was running. Neo4j was not touched.' -ForegroundColor DarkGray
}
Write-Host ''
