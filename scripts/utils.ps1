function Set-ProjectTempEnvironment {
    param([string]$Root)

    $tempRoot = Join-Path $Root 'temp'
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $env:TMP = $tempRoot
    $env:TEMP = $tempRoot
    $env:TMPDIR = $tempRoot
    return $tempRoot
}

function Show-ModuleHeader {
    param(
        [string]$Title,
        [string]$Task,
        [string]$PythonPath = '',
        [string]$TempPath = ''
    )

    Write-Host ('=' * 64) -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ('=' * 64) -ForegroundColor Cyan
    if ($PythonPath) { Write-Host "[INFO] Python: $PythonPath" -ForegroundColor DarkCyan }
    Write-Host "[INFO] Device: CPU" -ForegroundColor DarkCyan
    Write-Host "[INFO] Task:   $Task" -ForegroundColor DarkCyan
    if ($TempPath) { Write-Host "[INFO] Temp:   $TempPath" -ForegroundColor DarkCyan }
    Write-Host ('-' * 64) -ForegroundColor DarkCyan
}

function Get-ProjectPython {
    param([string]$Root)

    $python = Join-Path $Root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw "Missing virtual environment python at $python"
    }
    return $python
}
