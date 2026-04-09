$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

& $python (Join-Path $root 'launch.py') --mode cli
exit $LASTEXITCODE
