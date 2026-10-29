# Handoff: where the project stands (from the claude.ai chat, 29 Oct 2026)

Read this first when continuing in Claude Code. It summarises everything decided in the
original claude.ai conversation, so no context is lost.

## Who and what
- Aditya (IIM Mumbai MBA) owns **Study 1B: experiences/services** (booking flights,
  hotels, cabs) in a group marketing-research project on bias in AI/LLM agents, targeting
  publication. A teammate owns Study 1 (products); see `docs/study1_products.md`.
- The aim: test across many LLMs (Claude, GPT, Gemini, open-weight) and cover scenarios
  MECE-style.

## Decided so far
1. **Framework** (`docs/framework.md`, also a live doc on claude.ai): 4 bias benchmarks
   (Optimality, Invariance, Representativeness, Fidelity); 16 bias codes in 3 families
   (A supply side, B demand side, C process); 6 pipeline stages where bias enters; 5 agent
   modes (M1 parametric, M2 live search, M3 controlled listings, M4 agentic execution,
   M5 integrated partner apps); 5 sub-studies (1B-A conjoint, 1B-B persona invariance,
   1B-C live audit, 1B-D agentic dark-pattern sandbox, 1B-E disruption/advocacy);
   hypotheses HE1–HE11; analysis plan; MECE coverage matrix.
2. **Run 1B-A first**: it is the main causal test, and the fastest way to show results.
3. **Experiment kit built and validated** (this repo): generator, multi-provider runner,
   analysis. Dry run with 2 simulated agents recovered 24/24 planted weights inside 95%
   CIs. Re-verified on a fresh clone from GitHub.
4. **Design choices in the kit:** 4 options per task; 20% dominance tasks (one option best
   on every stated need and cheapest); M1 names-only and M3 full-listing modes; 3 prompt
   paraphrases; 2 system-prompt levels; 6 personas; categories flights (Mumbai–Delhi),
   hotels (Bengaluru, MG Road, 2 nights), cabs (Mumbai T2 → Bandra West); calls interleaved
   across models; standard errors clustered by task.
5. **Repo hygiene:** keys only in `.env` (git-ignored, auto-loaded); each teammate writes to
   their own run file; `CLAUDE.md` holds the rules.

## Not done yet (next steps, in order)
1. [ ] Set up on the laptop (see `SETUP_DESKTOP.md`): venv, requirements, `.env` with keys,
       re-run the dry run.
2. [ ] Fill the `FILL_ME` model strings in `config/models.yaml` from each provider's current
       model list; enable the pilot set (Claude Haiku, a GPT mini model, a Gemini Flash model,
       one open-weight model); fill `price_in`/`price_out`; run `python run.py check`.
3. [ ] Screen the fictitious brand names in `design.py` (no web presence, no sound-alikes) and
       confirm the high/low equity tiers with the Study 1 team (Brand Finance / Kantar /
       YouGov). Emirates/Singapore Airlines sit oddly on a domestic route; swap or change route.
4. [ ] Pilot: `generate.py --m3 60 --m1 20 --seed 101`, estimate, run, analyse. Gate: usable
       answers ≥ 95% per model; read raw answers by hand. Pilot numbers are not findings.
5. [ ] Freeze `design.py`; pre-register on OSF (hypotheses, sample sizes, analysis).
6. [ ] Confirmatory: `--m3 400 --m1 100 --seed 2026` (1,500 tasks/model) + stability arm
       (150 tasks × 5 reps); add flagship and more open-weight models; two-week drift rerun.
7. [ ] Later sub-studies: 1B-B persona invariance (needs ethics approval and name pre-tests
       with Indian raters), 1B-C live audit, 1B-D agentic sandbox, 1B-E advocacy rubric
       (verify DGCA passenger-rights and Consumer Protection (E-Commerce) Rules first).

## Known caveats
- Current Claude API/SDK does not expose temperature; keep `temperature: null` for Claude
  and use reruns to measure stability.
- Reasoning models may need `max_tokens` of 2,000+ or answers get cut off (unparsed).
- Related prior work to position against: Baig et al. 2026 (12-model hotel conjoint;
  rating and price dominate; list position ≈ $12/night), Allouah et al. 2025 (ACES,
  position bias), Pitenin 2026 (Bali census: documentation drives entry, rating drives rank),
  Ren et al. 2024 (identity bias in travel planning). Full list in `docs/framework.md` §15.
