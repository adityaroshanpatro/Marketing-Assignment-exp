# Study 1 (products) — teammate's design, for alignment

Copied from the team's "STUDY 1" document and "project details" note so Study 1B stays
aligned with it. The Study 1 team owns this design; do not edit it here.

## Project-level design note ("project details")
- Approach: automated audit / algorithmic auditing experiment in Python.
- Factorial: 2 (architecture: open-source/Llama vs closed GPT-4o/Claude) × 2 (retrieval:
  parametric memory vs search-augmented/RAG) × 3 (category: high-equity utilitarian,
  high-equity hedonic, low-equity commodity).
- Stimuli: synthetic and real brand profiles as JSON-LD (attribute specificity, schema
  completeness, ratings, volume, recency); Python scripts calling LLM APIs, 1,000+ runs per
  condition across 50 simulated buying personas and categories.

## Research questions
- **RQ1 (machine side):** which brand signals drive AI agents' recommendations and choices:
  brand equity encoded in training, reviews (rating, volume, recency), structured product
  data (schema completeness, attribute specificity); do weights vary across LLMs and between
  parametric and search-augmented answers?
- **RQ2 (consumer side):** does delegating the decision weaken brand premium (WTP), incumbent
  choice and repurchase intention? Mechanisms: agency, psychological ownership, brand salience.
- **RQ3 (interface):** when agent and consumer preferences diverge, whose prevails, and what
  restores brand influence (transparency, "prefer X" constraints, hedonic vs utilitarian
  category, trust in the agent)?

## Thesis and central construct
AI agents may shift brand advantage from consumer-held brand knowledge toward
machine-readable, retrievable evidence. Central construct: **agent-mediated brand advantage**,
the advantage a brand gets when an agent evaluates, ranks or selects on a consumer's behalf,
distinct from **consumer-side equity**. Agents are studied as market actors, not as
"silicon samples". Positioned against delegation research (2024 Decision Support Systems)
and conversational accompanied-shopping research.

## Study 1 design: machine conjoint in a synthetic marketplace
- Factors: brand (real high-equity / real low-equity / fictitious on an identical product,
  counterbalanced); contextual brand associations (strong vs weak copy); reviews
  (rating × volume × recency, high/low each); structured data (full schema.org JSON-LD /
  prose only / key attributes missing; specificity high/low within full schema); price
  (2–3 levels around category median). Held constant: quality, availability, persona fit.
- Environment: 5–7 models across providers (GPT, Claude, Gemini, Llama, Mistral, Grok,
  Qwen) with version, snapshot and settings recorded; parametric-only, search-augmented,
  structured-data and optional hybrid retrieval; identical retrieved evidence across models;
  budget / quality-seeker / novice personas; 3–5 prompt paraphrases; 2–3 categories
  (utilitarian to hedonic, Indian and global brands); randomised listing order.
- DVs: selection, ranking, choice share, recommendation strength, evidence use, attribute
  fidelity, stability, search behaviour. Stated rationale is not evidence of causal weights.
- Analysis: per-model conditional logit or hierarchical Bayes part-worths ("machine utility
  function"); pooled logit with brand, reviews, structured data, retrieval mode and
  brand × retrieval, plus model and task effects; rank-ordered logit; AMEs with CIs.
- Hypotheses H1a–H1e: brand matters at equal quality; reviews and structured data matter
  independently; weights differ by retrieval mode; structured data matters more with
  retrieval; effects vary across LLMs.
- Scale: 1,500–4,000+ model–task–product observations.
- Study 1a (appendix): real-brand audit across 5–10 categories, brand mentions and rank vs
  equity proxies (Brand Finance, Kantar BrandZ, YouGov, Google Trends, market share);
  concentration (HHI, Gini) vs actual market concentration.
