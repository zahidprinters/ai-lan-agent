# Wrapper for scripts/export_model.py
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$parent = Split-Path -Parent $root
$python = Join-Path $parent ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $root "export_model.py") --model (Join-Path $parent "models\char_model_best.pt") --export (Join-Path $parent "models\char_model_weights.pt")
exit $LASTEXITCODE
