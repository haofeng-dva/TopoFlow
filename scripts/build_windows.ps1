$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Project virtual environment not found.' }
Push-Location $Root
try {
    & $Python -m unittest discover -p 'test_*.py'
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    & $Python -m PyInstaller --noconfirm --clean topoflow.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    Copy-Item -LiteralPath 'config.toml.example' -Destination 'dist\TopoFlow\config.toml.example' -Force
    Compress-Archive -Path 'dist\TopoFlow\*' -DestinationPath 'dist\TopoFlow-Windows-x64.zip' -Force
} finally { Pop-Location }

