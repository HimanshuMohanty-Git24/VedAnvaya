<#
.SYNOPSIS
    Check that this machine can run VedaGraph, and say precisely what is missing.

.DESCRIPTION
    Seven things have to be true before the product works, and when one is not, the symptom
    is usually reported by the wrong layer: a missing Neo4j password surfaces as an empty
    graph page, an unbuilt frontend as a connection refused, an absent LLM key as a broken
    Ask panel. This script checks each one separately and names it, so the failure is
    diagnosed where it actually lives.

    It NEVER prints a secret. Where a credential matters, the check reports only whether it
    is set and how many characters it has -- enough to tell "absent" from "present but
    truncated" without putting the value in a terminal, a screenshot or a CI log.

    Exit code is 0 when every REQUIRED check passes. Optional checks -- the LLM provider,
    the audio catalog -- report and never fail the run, because the browsing product works
    without them and a doctor that failed on them would be ignored.

.PARAMETER Json
    Emit the result as JSON instead of a table.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
#>

[CmdletBinding()]
param(
    [switch]$Json
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$checks = New-Object System.Collections.ArrayList

function Add-Check {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Detail,
        [string]$Severity = 'REQUIRED',
        [string]$Fix = ''
    )
    $null = $checks.Add([pscustomobject]@{
        Name     = $Name
        Status   = $Status
        Severity = $Severity
        Detail   = $Detail
        Fix      = $Fix
    })
}

function Read-DotEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $index = $trimmed.IndexOf('=')
        if ($index -lt 1) { continue }
        $key = $trimmed.Substring(0, $index).Trim()
        $value = $trimmed.Substring($index + 1).Trim()
        # Strip one layer of surrounding quotes, which .env files commonly carry.
        if ($value.Length -ge 2) {
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
        $map[$key] = $value
    }
    return $map
}

function Get-Setting {
    param([hashtable]$Env, [string]$Name)
    # A real environment variable wins over .env, which is the precedence pydantic-settings
    # applies. Checking them in the other order would report a value the app will not use.
    $live = [Environment]::GetEnvironmentVariable($Name)
    if ($live) { return $live }
    if ($Env.ContainsKey($Name)) { return $Env[$Name] }
    return $null
}

# ---------------------------------------------------------------------------
# 1. Python environment
# ---------------------------------------------------------------------------

$python = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $python) {
    $version = & $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Add-Check 'python-venv' 'OK' "Python $version at .venv"
    } else {
        Add-Check 'python-venv' 'FAIL' 'The interpreter at .venv exists but did not run.' 'REQUIRED' 'Recreate it: uv sync --extra dev'
    }
} else {
    Add-Check 'python-venv' 'FAIL' 'No interpreter at .venv\Scripts\python.exe' 'REQUIRED' 'uv sync --extra dev'
}

if (Test-Path $python) {
    $imports = & $python -c "import fastapi, neo4j, pydantic, uvicorn; print('ok')" 2>$null
    if ($imports -eq 'ok') {
        Add-Check 'python-deps' 'OK' 'fastapi, neo4j, pydantic and uvicorn all import'
    } else {
        Add-Check 'python-deps' 'FAIL' 'A core dependency does not import.' 'REQUIRED' 'uv sync --extra dev'
    }
}

# ---------------------------------------------------------------------------
# 2. Configuration file
# ---------------------------------------------------------------------------

$envPath = Join-Path $root '.env'
$envMap = Read-DotEnv $envPath
if (Test-Path $envPath) {
    Add-Check 'env-file' 'OK' ".env present with $($envMap.Count) setting(s)"
} else {
    Add-Check 'env-file' 'FAIL' 'No .env file.' 'REQUIRED' 'Copy .env.example to .env and fill in NEO4J_PASSWORD'
}

# ---------------------------------------------------------------------------
# 3. Neo4j: credentials, reachability, and that the graph is actually loaded
# ---------------------------------------------------------------------------

$neoUri = Get-Setting $envMap 'NEO4J_URI'
if (-not $neoUri) { $neoUri = 'bolt://localhost:7687' }
$neoPassword = Get-Setting $envMap 'NEO4J_PASSWORD'

if ($neoPassword) {
    # Length only. The value never reaches stdout.
    Add-Check 'neo4j-password' 'OK' "NEO4J_PASSWORD is set ($($neoPassword.Length) characters; value not shown)"
} else {
    Add-Check 'neo4j-password' 'FAIL' 'NEO4J_PASSWORD is not set.' 'REQUIRED' 'Set it in .env'
}

if ((Test-Path $python) -and $neoPassword) {
    # Delegated to Python rather than a TCP probe: a port that accepts a connection tells
    # you nothing about whether the credentials work or the corpus is present, and both
    # have been the real cause here.
    $probe = @'
import json, os, sys
sys.path.insert(0, "src")
try:
    from neo4j import GraphDatabase
    uri = os.environ["VG_URI"]
    driver = GraphDatabase.driver(uri, auth=(os.environ["VG_USER"], os.environ["VG_PASS"]))
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        works = session.run("MATCH (w:Work) RETURN count(w) AS c").single()["c"]
    driver.close()
    print(json.dumps({"ok": True, "nodes": nodes, "rels": rels, "works": works}))
except Exception as error:
    print(json.dumps({"ok": False, "error": type(error).__name__}))
'@
    $env:VG_URI = $neoUri
    $neoUser = Get-Setting $envMap 'NEO4J_USER'
    if (-not $neoUser) { $neoUser = 'neo4j' }
    $env:VG_USER = $neoUser
    $env:VG_PASS = $neoPassword
    Push-Location $root
    $raw = $probe | & $python - 2>$null
    Pop-Location
    Remove-Item Env:\VG_PASS -ErrorAction SilentlyContinue
    Remove-Item Env:\VG_URI -ErrorAction SilentlyContinue
    Remove-Item Env:\VG_USER -ErrorAction SilentlyContinue

    $result = $null
    if ($raw) { try { $result = $raw | ConvertFrom-Json } catch { $result = $null } }
    if ($result -and $result.ok) {
        Add-Check 'neo4j-reachable' 'OK' "Connected to $neoUri"
        if ($result.works -ge 4 -and $result.nodes -gt 100000) {
            Add-Check 'neo4j-loaded' 'OK' "$($result.nodes) nodes, $($result.rels) relationships, $($result.works) works"
        } else {
            Add-Check 'neo4j-loaded' 'FAIL' "Reachable but the corpus looks absent: $($result.nodes) nodes, $($result.works) works" 'REQUIRED' 'Load the graph projection before starting the product'
        }
    } else {
        $reason = 'connection failed'
        if ($result) { $reason = $result.error }
        Add-Check 'neo4j-reachable' 'FAIL' "Could not connect to $neoUri ($reason)" 'REQUIRED' 'Start Neo4j (see infra\docker-compose.neo4j.yml) and check NEO4J_PASSWORD'
        Add-Check 'neo4j-loaded' 'SKIP' 'Not checked: the database could not be reached.' 'REQUIRED'
    }
}

# ---------------------------------------------------------------------------
# 4. Frontend
# ---------------------------------------------------------------------------

$frontend = Join-Path $root 'frontend'
if (Test-Path (Join-Path $frontend 'node_modules')) {
    Add-Check 'frontend-deps' 'OK' 'frontend\node_modules present'
} else {
    Add-Check 'frontend-deps' 'FAIL' 'frontend\node_modules is missing.' 'REQUIRED' 'cd frontend; pnpm install'
}

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nodeVersion = (& node --version) 2>$null
    Add-Check 'node' 'OK' "node $nodeVersion"
} else {
    Add-Check 'node' 'FAIL' 'node is not on PATH.' 'REQUIRED' 'Install Node.js 20 or newer'
}

$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if ($pnpm) {
    Add-Check 'pnpm' 'OK' "pnpm $((& pnpm --version) 2>$null)"
} else {
    Add-Check 'pnpm' 'FAIL' 'pnpm is not on PATH.' 'REQUIRED' 'npm install -g pnpm'
}

# ---------------------------------------------------------------------------
# 5. LLM provider -- optional by design
# ---------------------------------------------------------------------------

$provider = Get-Setting $envMap 'VEDAGRAPH_LLM_PROVIDER'
$apiKey = Get-Setting $envMap 'VEDAGRAPH_LLM_API_KEY'
if (-not $apiKey) {
    foreach ($fallback in @('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GROQ_API_KEY', 'OPENROUTER_API_KEY', 'XAI_API_KEY')) {
        $candidate = Get-Setting $envMap $fallback
        if ($candidate) { $apiKey = $candidate; break }
    }
}
if ($apiKey) {
    $shown = 'not shown'
    Add-Check 'llm-provider' 'OK' "provider '$provider', key is set ($($apiKey.Length) characters; value $shown)" 'OPTIONAL'
} else {
    Add-Check 'llm-provider' 'WARN' "No LLM key found. Browsing, search and the graph all work; Ask VedaGraph will report NOT_CONFIGURED." 'OPTIONAL' 'Set VEDAGRAPH_LLM_PROVIDER and VEDAGRAPH_LLM_API_KEY in .env to enable Ask'
}

# ---------------------------------------------------------------------------
# 6. Audio catalog -- optional by design
# ---------------------------------------------------------------------------

$catalog = Join-Path $root 'data\product\audio_catalog.jsonl'
if (Test-Path $catalog) {
    $lines = (Get-Content -LiteralPath $catalog | Measure-Object -Line).Lines
    Add-Check 'audio-catalog' 'OK' "$lines catalogued recording(s)" 'OPTIONAL'
} else {
    Add-Check 'audio-catalog' 'WARN' 'No audio catalog. The reader omits the player; nothing else changes.' 'OPTIONAL' 'python scripts\audio\discover_vedic_heritage.py'
}

$cache = Join-Path $root 'data\audio\cache'
if (Test-Path $cache) {
    $cached = @(Get-ChildItem -LiteralPath $cache -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' })
    Add-Check 'audio-cache' 'OK' "$($cached.Count) file(s) cached locally; the rest stream from their publisher" 'OPTIONAL'
} else {
    Add-Check 'audio-cache' 'OK' 'No local cache. Audio streams from its publisher.' 'OPTIONAL'
}

# ---------------------------------------------------------------------------
# 7. Ports
# ---------------------------------------------------------------------------

function Test-PortFree {
    param([int]$Port)
    # Asks the OS which ports are listening rather than trying to bind one.
    #
    # The obvious implementation -- bind a TcpListener on 127.0.0.1 and see whether it
    # throws -- reports a port FREE while a server is serving on it. A process listening on
    # 0.0.0.0 or on the IPv6 wildcard does not conflict with a fresh loopback-only bind on
    # Windows, so the probe succeeds and the check lies. It did: this script reported port
    # 3000 free while Next.js was answering requests on it.
    $listening = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    return ($listening.Count -eq 0)
}

$apiPort = Get-Setting $envMap 'API_PORT'
if (-not $apiPort) { $apiPort = '8000' }
foreach ($entry in @(@{ Name = 'port-api'; Port = [int]$apiPort }, @{ Name = 'port-frontend'; Port = 3000 })) {
    if (Test-PortFree -Port $entry.Port) {
        Add-Check $entry.Name 'OK' "port $($entry.Port) is free" 'OPTIONAL'
    } else {
        # In use is not a failure: the most likely reason is that the product is already
        # running, which is the desired state rather than a broken one.
        Add-Check $entry.Name 'WARN' "port $($entry.Port) is in use -- VedaGraph may already be running" 'OPTIONAL'
    }
}

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

$failures = @($checks | Where-Object { $_.Severity -eq 'REQUIRED' -and $_.Status -ne 'OK' })

if ($Json) {
    [pscustomobject]@{
        checks   = $checks
        failures = $failures.Count
        ready    = ($failures.Count -eq 0)
    } | ConvertTo-Json -Depth 4
} else {
    Write-Host ''
    Write-Host 'VedaGraph doctor' -ForegroundColor Cyan
    Write-Host ''
    foreach ($check in $checks) {
        $colour = 'Green'
        if ($check.Status -eq 'WARN') { $colour = 'Yellow' }
        if ($check.Status -eq 'FAIL') { $colour = 'Red' }
        if ($check.Status -eq 'SKIP') { $colour = 'DarkGray' }
        Write-Host ("  [{0,-4}] {1,-18} {2}" -f $check.Status, $check.Name, $check.Detail) -ForegroundColor $colour
        if ($check.Fix -and $check.Status -ne 'OK') {
            Write-Host ("         -> {0}" -f $check.Fix) -ForegroundColor DarkGray
        }
    }
    Write-Host ''
    if ($failures.Count -eq 0) {
        Write-Host '  Ready. Start the product with scripts\start-product.ps1' -ForegroundColor Green
    } else {
        Write-Host ("  {0} required check(s) failed. Fix those and re-run." -f $failures.Count) -ForegroundColor Red
    }
    Write-Host ''
}

if ($failures.Count -gt 0) { exit 1 }
exit 0
