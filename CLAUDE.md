# Study 1B-A: LLM booking-agent bias experiment

Marketing research project (IIM Mumbai), targeting publication. Study 1 (a teammate)
covers products; this repo is Study 1B, experiences and services. It runs a
randomised conjoint: LLM agents choose 1 of 4 flight, hotel or cab options whose brand,
price, fees, reviews, cancellation terms, badges, sales channel, information format
and list position are randomised independently. The analysis estimates what each
signal is worth to each model (AMCEs in percentage points and rupee equivalents).
The full design rationale is in the team's framework doc; README.md has the run steps; SETUP_DESKTOP.md covers first-time setup in the Claude desktop app.

## Files
- `design.py`: brands, personas, attribute levels, prompt wordings. The only place to change the experiment.
- `generate.py`: builds `tasks.jsonl` (pre-rendered prompts, identical for every model).
- `run.py`: `check` / `estimate` / `run`. Calls models, logs to `runs.jsonl`, resumes after a stop.
- `analyze.py`: report.md, AMCE / rupee / dominance / fee-fidelity tables, charts.
- `config/models.yaml`: real model roster. `config/models_mock.yaml`: simulated agents for dry runs.
- `data/dryrun/`: validated dry run with SIMULATED agents. Never present it as findings.

## Commands
```bash
pip install -r requirements.txt
python run.py check                                    # verify keys + model strings
python generate.py --m3 60 --m1 20 --seed 101 --out data/pilot/tasks.jsonl
python run.py estimate --tasks data/pilot/tasks.jsonl
python run.py run --tasks data/pilot/tasks.jsonl --out data/pilot/runs_<name>.jsonl
python analyze.py --tasks data/pilot/tasks.jsonl --runs data/pilot/runs_<name>.jsonl --out results/pilot
# dry run / pipeline check (no API keys needed)
python run.py run --config config/models_mock.yaml --tasks data/dryrun/tasks.jsonl --out data/dryrun/runs_mock.jsonl
python analyze.py --tasks data/dryrun/tasks.jsonl --runs data/dryrun/runs_mock.jsonl --out data/dryrun/results --validate config/models_mock.yaml
```

## Rules
- API keys live only in `.env` (git-ignored; `run.py` loads it). Never print, log, echo or
  commit a key, and never write one into any other file. Check `git status` before every commit.
- Never invent model API strings. `FILL_ME` entries must be set from the provider's model
  list, then confirmed with `python run.py check`.
- Never fabricate, edit or "clean" rows in `runs.jsonl`; it is the audit trail. Failed calls
  are retried by re-running the same command.
- Results from `provider: mock` are simulated. Label them that way everywhere.
- After the pilot the design is FROZEN: do not change `design.py`, prompts or seeds without
  the team agreeing and recording it as a deviation from the pre-registration.
- Each teammate writes runs to their own file (`runs_<name>.jsonl`); combine at analysis
  with `--runs a.jsonl,b.jsonl` to avoid merge conflicts.
- Pilot numbers check the instrument only. They are never reported as findings.
- Keep run outputs reproducible: fixed seeds, the model string returned by the API logged
  per call, and no hand-edited tasks.
