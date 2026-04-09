# Wrapper for scripts/infer_simple.py
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$parent = Split-Path -Parent $root
$python = Join-Path $parent ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $root "infer_simple.py") $args
exit $LASTEXITCODE
