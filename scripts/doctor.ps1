$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python runtime not found.' }
Push-Location $Root
try { & $Python -c "from src.config import load_config; from src.tools.doctor import print_diagnostics; raise SystemExit(print_diagnostics(load_config('config.toml')))" }
finally { Pop-Location }

