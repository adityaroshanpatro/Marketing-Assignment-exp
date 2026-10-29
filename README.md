# Study 1B-A: machine conjoint for booking agents (flights, hotels, cabs)

This kit runs the core causal test from the Study 1B framework: LLM agents book one
of 4 options whose brand, price, fees, reviews, cancellation terms, badges, sales
channel, information format and list position are randomised independently. It
estimates what each signal is worth to each model, in percentage points and rupees.

```
design.py            brand sets, personas, attribute levels, prompt wordings  <- edit here
generate.py          builds the tasks (identical text for every model)
run.py               calls the models, logs every call, resumes after a stop
analyze.py           AMCEs, rupee equivalents, dominance, fee fidelity, charts, report.md
config/models.yaml   your model roster (exact API strings, keys, prices)
config/models_mock.yaml   two simulated agents for a dry run
data/dryrun/results/      output of the dry run (SIMULATED, not findings)
```

What each run tests:

| Output | Bias codes | Hypotheses |
| --- | --- | --- |
| Pooled and per-category AMCEs | A1 brand, A2 channel, A3 position/badges/format, A4 price, fees, terms | HE1, HE4, HE5, HE6 |
| Brand effect M1 (names only) vs M3 (full listings) | A1 | HE3 |
| Dominance hit rate, and which brand it picks when it misses | A1, A4 | HE1, HE5 |
| Fee fidelity (does the stated total include checkout fees?) | C2 | HE5 |
| Brand x model Wald test, per-model panels | all | HE11 |
| Stability across reruns | C6 | noise floor |

## 1. Set up (10 minutes)

```bash
git clone <repo-url> && cd <repo-folder>
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # Windows: copy .env.example .env
```

Open `.env` and paste your keys. `run.py` loads it automatically. `.env` is listed in
`.gitignore`, so it stays on your laptop and is never pushed; each teammate keeps their
own. Before every push, `git status` should not show `.env`.

Keys: one OpenRouter key reaches closed and open-weight models alike and is the
fastest way to start. Direct keys (Anthropic, OpenAI, Google) are cheaper at volume.

**Working together on git.** Commit `config/`, `design.py` changes and `data/*/runs.jsonl`
so both of you analyse the same data. Use different `--out` files when you run in
parallel (for example `data/main/runs_aditya.jsonl`, `data/main/runs_<teammate>.jsonl`),
then pass both to `analyze.py` with `--runs file1,file2` to avoid merge conflicts.

## 2. Pick models and check them

1. Open `config/models.yaml`. For each model you want, replace `FILL_ME` with the exact
   API string from the provider's model list and set `enabled: true`.
2. Pilot set (4 models, one per family): Claude Haiku, a GPT mini model, Gemini Flash,
   one open-weight model (Llama, Qwen or DeepSeek).
3. Fill `price_in` / `price_out` (USD per million tokens) from each pricing page.
4. Run:

```bash
python run.py check
```

Every line must say `OK`. Record the `model_returned` string; that is the snapshot you report.

## 3. Pilot (one evening)

```bash
python generate.py --m3 60 --m1 20 --seed 101 --out data/pilot/tasks.jsonl
python run.py estimate --tasks data/pilot/tasks.jsonl
python run.py run --tasks data/pilot/tasks.jsonl --out data/pilot/runs.jsonl
python analyze.py --tasks data/pilot/tasks.jsonl --runs data/pilot/runs.jsonl --out results/pilot
```

240 tasks per model, about 840 input tokens each. Then check, before anything else:

- `results/pilot/parse_rates.csv`: usable >= 0.95 for every model. If not, read
  `raw_response` in `runs.jsonl` for the failures and fix the prompt or `max_tokens`
  (reasoning models may need 2000+).
- Read 10 raw answers per model by hand. Do they understand the listings?
- Look at `report.md`. Pilot effects are noisy; use them only to confirm the
  instrument works and to fix sample sizes. Do not report them.

## 4. Freeze and pre-register

After the pilot: no more edits to `design.py`. Write the hypotheses, sample sizes and
analysis (this README + framework doc Sections 11-12) into an OSF pre-registration.

## 5. Confirmatory run

```bash
python generate.py --m3 400 --m1 100 --seed 2026 --out data/main/tasks.jsonl
python run.py run --tasks data/main/tasks.jsonl --out data/main/runs.jsonl
# stability arm: 150 tasks re-run to 5 reps
python run.py run --tasks data/main/tasks.jsonl --out data/main/runs.jsonl --modes M3 --limit 150 --reps 5
python analyze.py --tasks data/main/tasks.jsonl --runs data/main/runs.jsonl --out results/main
```

1,500 tasks per model (1,200 listings, of which 240 dominance tasks; 300 names-only),
about 1.3M input and 0.2M output tokens per model. Stop any time with Ctrl+C and re-run
the same command; finished calls are skipped and failed ones retried. Calls are
interleaved across models so no model is tied to one time of day.

Repeat the stability arm two weeks later into a new `--out` file to check drift.

## 6. Read the results

`results/main/report.md` has every table and chart. The headline exhibits:

- `fig_amce_by_model.png`: what moves each model's choice, side by side
- `fig_brand_m1_vs_m3.png`: does brand matter less once evidence is supplied?
- `fig_dominance.png`: how often each model books the objectively best option
- `rupee_equivalents.csv`: e.g. "a famous name is worth ₹X per night to model Y"
- `fee_fidelity.csv`: share of answers that quote the pre-fee price as the total

## Dry run (already done)

`data/dryrun/` holds a full run with two simulated agents whose decision weights are
known. All 24 planted weights fell inside the estimated 95% intervals
(`validation_recovery.csv`), so the generator, parser and analysis are wired correctly.
Re-run it any time with:

```bash
python run.py run --config config/models_mock.yaml --tasks data/dryrun/tasks.jsonl --out data/dryrun/runs_mock.jsonl
python analyze.py --tasks data/dryrun/tasks.jsonl --runs data/dryrun/runs_mock.jsonl --out data/dryrun/results --validate config/models_mock.yaml
```

## Notes

- Current Claude models do not take a temperature setting through the SDK, so leave
  `temperature: null` for them; reruns measure their randomness instead.
- Screen the fictitious brand names (no web presence, no sound-alikes) and confirm
  high/low equity tiers before the confirmatory run; they are in `design.py`.
- Never edit `data/*/tasks.jsonl` by hand. Change `design.py` and regenerate with a new seed.
- Rows in `runs.jsonl` keep the raw response, token counts, latency and model string
  returned by the API; that file is the audit trail for the paper.
