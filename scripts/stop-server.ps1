# @fileoverview Stop this checkout's backend and its reloader children on one port.
# @license Apache-2.0
# @copyright 2026 Timothy Mallory
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8004
)

$ErrorActionPreference = 'Stop'
$ledgerRoot = Split-Path -Parent $PSScriptRoot
$ledgerPythonPaths = @(
    (Join-Path $ledgerRoot '.venv\Scripts\python.exe'),
    (Join-Path $ledgerRoot 'backend\.venv\Scripts\python.exe')
)
$ledgerCommandPatterns = @($ledgerPythonPaths | ForEach-Object {
    '^\s*"?' + [regex]::Escape($_) + '"?\s+-m\s+uvicorn\s+app\.main:app(?:\s|$)'
})
$ledgerPortPattern = '(?:^|\s)--port(?:\s+|=)"?' + $Port + '"?(?:\s|$)'

try {
    # Match this checkout's server command, including its configured port.
    # Killing the reloader tree also removes its worker and resource tracker.
    $ledgerServers = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
        Where-Object {
            $commandLine = $_.CommandLine
            $matchesCheckout = @($ledgerCommandPatterns | Where-Object { $commandLine -match $_ }).Count -gt 0
            $matchesCheckout -and $commandLine -match $ledgerPortPattern
        })
    $ledgerServerIds = @($ledgerServers | ForEach-Object { $_.ProcessId })
    $ledgerRoots = @($ledgerServers | Where-Object { $_.ParentProcessId -notin $ledgerServerIds })

    foreach ($ledgerServer in $ledgerRoots) {
        $ledgerCurrent = Get-CimInstance Win32_Process -Filter "ProcessId = $($ledgerServer.ProcessId)"
        if (-not $ledgerCurrent) { continue }
        if ($ledgerCurrent.CreationDate -ne $ledgerServer.CreationDate -or
            $ledgerCurrent.CommandLine -ne $ledgerServer.CommandLine) {
            throw "Process $($ledgerServer.ProcessId) changed while checking it; stopping nothing further."
        }

        Write-Host "Stopping existing Tim's Ledger backend on port $Port (PID $($ledgerServer.ProcessId))..."
        & taskkill.exe /PID $ledgerServer.ProcessId /T /F
        if ($LASTEXITCODE -ne 0) {
            throw "Could not stop Tim's Ledger backend PID $($ledgerServer.ProcessId)."
        }
    }

    # Refuse to launch over another program, or a server that did not stop.
    $ledgerListeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq $Port })
    if ($ledgerListeners.Count -gt 0) {
        throw "Port $Port is still in use (PID $($ledgerListeners[0].OwningProcess)). No unrelated process was stopped."
    }

    if ($ledgerRoots.Count -eq 0) {
        Write-Host "No existing Tim's Ledger backend on port $Port."
    } else {
        Write-Host "Tim's Ledger backend stopped; port $Port is free."
    }
    exit 0
} catch {
    Write-Host "Tim's Ledger shutdown failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
