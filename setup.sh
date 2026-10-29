#!/usr/bin/env bash
# One-shot local setup (macOS / Linux). Run from inside the cloned repo:  bash setup.sh
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
[ -z "$PY" ] && { echo "Python 3.10+ not found. Install it from python.org first."; exit 1; }
echo "Using $($PY --version)"
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Created .env - open it and paste your API keys."; }
echo "Running the dry run (simulated agents, no API cost)..."
python run.py run --config config/models_mock.yaml --tasks data/dryrun/tasks.jsonl --out data/dryrun/runs_check.jsonl | tail -1
python analyze.py --tasks data/dryrun/tasks.jsonl --runs data/dryrun/runs_check.jsonl --out data/dryrun/results_check --validate config/models_mock.yaml | grep "planted weights"
rm -rf data/dryrun/runs_check.jsonl data/dryrun/results_check
echo
echo "Setup OK. Next: put your keys in .env, fill FILL_ME model strings in config/models.yaml,"
echo "then run:  source .venv/bin/activate && python run.py check"
