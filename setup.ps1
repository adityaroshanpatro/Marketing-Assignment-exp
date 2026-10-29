# One-shot local setup (Windows PowerShell). Run from inside the cloned repo:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { Write-Host "Python 3.10+ not found. Install it from python.org (tick 'Add python.exe to PATH')."; exit 1 }
python --version
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env - open it and paste your API keys." }
Write-Host "Running the dry run (simulated agents, no API cost)..."
python run.py run --config config/models_mock.yaml --tasks data/dryrun/tasks.jsonl --out data/dryrun/runs_check.jsonl | Select-Object -Last 1
python analyze.py --tasks data/dryrun/tasks.jsonl --runs data/dryrun/runs_check.jsonl --out data/dryrun/results_check --validate config/models_mock.yaml | Select-String "planted weights"
Remove-Item -Recurse -Force data/dryrun/runs_check.jsonl, data/dryrun/results_check
Write-Host ""
Write-Host "Setup OK. Next: put your keys in .env, fill FILL_ME model strings in config/models.yaml,"
Write-Host "then run:  .\.venv\Scripts\Activate.ps1 ; python run.py check"
