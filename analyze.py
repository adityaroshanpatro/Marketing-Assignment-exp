"""
Analyse Study 1B-A runs.

Usage:
    python analyze.py --tasks data/tasks.jsonl --runs data/runs.jsonl --out results/
    python analyze.py ... --validate config/models_mock.yaml   # dry run: compare to planted weights

Outputs (in --out):
    report.md                  headline numbers, written for the team
    amce_pooled.csv            per-model AMCEs, all categories pooled (M3 random tasks)
    amce_by_category.csv       per-model x category AMCEs incl. category-only attributes
    rupee_equivalents.csv      what brand / position / badges are worth in INR
    brand_m1_vs_m3.csv         brand effect with no evidence (M1) vs with listings (M3)
    dominance.csv              hit rate on tasks with one strictly dominant option
    fee_fidelity.csv           does the stated total include partitioned fees?
    parse_rates.csv            share of calls that returned a usable answer
    fig_*.png                  charts
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

import design as D

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

REFS = {"brand_tier": "fictitious", "brand_copy": "weak", "price_level": "median",
        "fee_display": "all_in", "rating": "low", "review_volume": "low",
        "review_recency": "older", "cancellation": "nonrefundable", "badge": "none",
        "info_format": "jsonld_full", "channel_std": "direct", "position": "1"}
CAT_REFS = {"departure": "morning", "stops": "nonstop", "on_time": "low", "checked_bag": "not_included",
            "distance_km": "5", "breakfast": "not_included", "eta_min": "12", "vehicle": "mini",
            "surge": "none", "driver_rating": "4.5", "channel": "direct"}
NICE = {
    "brand_tier[high]": "Brand: real high-equity", "brand_tier[low]": "Brand: real low-equity",
    "brand_copy[strong]": "Strong brand copy", "price_level[minus15]": "Price -15%",
    "price_level[plus15]": "Price +15%", "fee_display[partitioned]": "Fees shown only at checkout",
    "rating[high]": "Rating 4.6 (vs 3.6)", "review_volume[high]": "Many reviews",
    "review_recency[recent]": "Recent reviews", "cancellation[partial]": "Partial refund",
    "cancellation[free]": "Free cancellation", "badge[sponsored]": "Badge: Sponsored",
    "badge[bestseller]": "Badge: Best seller", "badge[scarcity]": "Badge: Only 2 left",
    "info_format[prose]": "Prose only (vs JSON-LD)", "info_format[missing_keys]": "Key attributes missing",
    "channel_std[intermediary]": "Sold via intermediary", "position[2]": "Listed 2nd (vs 1st)",
    "position[3]": "Listed 3rd", "position[4]": "Listed 4th",
}


# ----------------------------------------------------------------------------
def load(tasks_path, runs_path):
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(tasks_path, encoding="utf-8")}
    runs = [json.loads(l) for path in runs_path.split(",") for l in open(path, encoding="utf-8") if l.strip()]
    runs = pd.DataFrame(runs)
    # keep the latest record per run_id (retries append)
    runs = runs.drop_duplicates("run_id", keep="last")
    rows = []
    for r in runs.itertuples():
        if not r.parse_ok:
            continue
        t = tasks[r.task_id]
        pri = D.PERSONAS[t["persona_id"]]["priorities"][t["category"]]
        rank = r.ranking if isinstance(r.ranking, list) else []
        for o in t["options"]:
            row = {k: v for k, v in o.items()}
            row.update({"run_id": r.run_id, "task_id": r.task_id, "model": r.model_name,
                        "provider": r.provider, "mode": t["mode"], "task_type": t["task_type"],
                        "category": t["category"], "persona_id": t["persona_id"],
                        "template_id": t["template_id"], "system_prompt_id": t["system_prompt_id"],
                        "rep": r.rep, "chosen": int(o["label"] == r.chosen_option),
                        "rank": rank.index(o["label"]) + 1 if o["label"] in rank else np.nan,
                        "n_priorities_met": sum(o.get(k) == v for k, v in pri.items()),
                        "stated_total_price": r.stated_total_price if o["label"] == r.chosen_option else np.nan})
            rows.append(row)
    long = pd.DataFrame(rows)
    long["position"] = long["position"].astype(str)
    if "channel" in long:
        long["channel_std"] = np.where(long["channel"] == "direct", "direct", "intermediary")
    return tasks, runs, long


def term(var, ref):
    return f"C({var}, Treatment('{ref}'))"


def tidy(fit, model, extra=None):
    ci = fit.conf_int()
    out = []
    for name in fit.params.index:
        if name == "Intercept" or "category" in name:
            continue
        var = name.split("(")[1].split(",")[0]
        lvl = name.split("[T.")[1].rstrip("]")
        key = f"{var}[{lvl}]"
        out.append({"model": model, "term": key, "label": NICE.get(key, key),
                    "amce": fit.params[name], "se": fit.bse[name],
                    "ci_low": ci.loc[name, 0], "ci_high": ci.loc[name, 1], "p": fit.pvalues[name],
                    **(extra or {})})
    df = pd.DataFrame(out)
    if len(df):
        df["q_bh"] = multipletests(df["p"], method="fdr_bh")[1]
    return df


def lpm(df, terms, extra_fe=""):
    f = "chosen ~ " + " + ".join(term(v, REFS.get(v, CAT_REFS.get(v))) for v in terms) + extra_fe
    return smf.ols(f, data=df).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df["task_id"])[0]})


COMMON = ["brand_tier", "brand_copy", "price_level", "fee_display", "rating", "review_volume",
          "review_recency", "cancellation", "badge", "info_format", "channel_std", "position"]


# ----------------------------------------------------------------------------
def analyse(long, runs, out):
    res = {}
    m3 = long[(long["mode"] == "M3") & (long["task_type"] == "random")]
    m1 = long[long["mode"] == "M1"]
    models = sorted(long["model"].unique())

    # parse rates
    pr = runs.groupby("model_name").agg(calls=("run_id", "size"), usable=("parse_ok", "mean"),
                                        errors=("error", lambda s: s.notna().mean())).reset_index()
    pr.to_csv(f"{out}/parse_rates.csv", index=False)
    res["parse"] = pr

    # pooled AMCEs per model
    pooled = pd.concat([tidy(lpm(m3[m3.model == m], COMMON, " + C(category)"), m) for m in models])
    pooled.to_csv(f"{out}/amce_pooled.csv", index=False)
    res["pooled"] = pooled

    # by category, incl. category-only attributes and raw channel
    bycat, rupee = [], []
    for m in models:
        for cat in D.SCENARIOS:
            d = m3[(m3.model == m) & (m3.category == cat)]
            if d["run_id"].nunique() < 30:
                continue
            terms = [v for v in COMMON if v != "channel_std"] + ["channel"] + list(D.CATEGORY_LEVELS[cat])
            fit = lpm(d, terms)
            tb = tidy(fit, m, {"category": cat})
            bycat.append(tb)
            # rupee equivalents: pp per INR from the -15% vs +15% contrast
            p_lo = tb.set_index("term")["amce"].get("price_level[minus15]", np.nan)
            p_hi = tb.set_index("term")["amce"].get("price_level[plus15]", np.nan)
            per_inr = (p_lo - p_hi) / (0.30 * D.SCENARIOS[cat]["median_price"])
            for k in ["brand_tier[high]", "brand_tier[low]", "position[4]", "badge[sponsored]",
                      "badge[scarcity]", "cancellation[free]", "rating[high]", "brand_copy[strong]"]:
                if k in set(tb["term"]) and per_inr > 0:
                    a = tb.set_index("term").loc[k, "amce"]
                    rupee.append({"model": m, "category": cat, "term": k, "label": NICE.get(k, k),
                                  "amce": a, "inr_equivalent": a / per_inr})
    bycat = pd.concat(bycat) if bycat else pd.DataFrame()
    bycat.to_csv(f"{out}/amce_by_category.csv", index=False)
    rupee = pd.DataFrame(rupee)
    rupee.to_csv(f"{out}/rupee_equivalents.csv", index=False)
    res["rupee"] = rupee

    # brand effect without evidence (M1) vs with listings (M3)
    b = []
    for m in models:
        for mode, d, terms in [("M1 names only", m1[m1.model == m], ["brand_tier", "position"]),
                               ("M3 full listings", m3[m3.model == m], COMMON)]:
            if not len(d):
                continue
            tb = tidy(lpm(d, terms, " + C(category)"), m).set_index("term")
            for lvl in ["high", "low"]:
                k = f"brand_tier[{lvl}]"
                b.append({"model": m, "mode": mode, "term": k, "amce": tb.loc[k, "amce"],
                          "ci_low": tb.loc[k, "ci_low"], "ci_high": tb.loc[k, "ci_high"]})
    brand = pd.DataFrame(b)
    brand.to_csv(f"{out}/brand_m1_vs_m3.csv", index=False)
    res["brand"] = brand

    # dominance tasks
    dom = long[(long["mode"] == "M3") & (long["task_type"] == "dominant")]
    if len(dom):
        dd = dom[dom.is_dominant == 1]
        hit = dd.groupby("model")["chosen"].agg(["mean", "size"]).reset_index()
        hit.columns = ["model", "hit_rate", "tasks"]
        hit["se"] = np.sqrt(hit.hit_rate * (1 - hit.hit_rate) / hit.tasks)
        by_brand = dd.groupby(["model", "brand_tier"])["chosen"].mean().unstack().add_prefix("hit_when_dominant_is_")
        hit = hit.merge(by_brand.reset_index(), on="model")
        # when the agent misses, what did it pick?
        miss = dom[(dom.is_dominant == 0) & (dom.chosen == 1)]
        if len(miss):
            share = miss.groupby("model")["brand_tier"].value_counts(normalize=True).unstack().add_prefix("miss_picks_")
            hit = hit.merge(share.reset_index(), on="model", how="left")
        hit.to_csv(f"{out}/dominance.csv", index=False)
        res["dom"] = hit

    # fee fidelity
    ch = long[(long["mode"] == "M3") & (long.chosen == 1)].copy()
    ch["stated_ok"] = (abs(ch["stated_total_price"] - ch["total_price"]) <= 0.02 * ch["total_price"]).astype(int)
    ch["stated_headline"] = ((ch["fee_display"] == "partitioned") &
                             (abs(ch["stated_total_price"] - ch["headline_price"]) <= 0.02 * ch["headline_price"])).astype(int)
    fee = ch.groupby(["model", "fee_display"]).agg(runs=("run_id", "size"), total_correct=("stated_ok", "mean"),
                                                   reported_pre_fee_price=("stated_headline", "mean")).reset_index()
    fee.to_csv(f"{out}/fee_fidelity.csv", index=False)
    res["fee"] = fee

    # stability across reps
    if runs["rep"].max() > 1:
        ok = runs[runs.parse_ok == 1]
        multi = ok.groupby(["model_name", "task_id"])["rep"].transform("size") > 1
        ok = ok[multi]
        st = ok.groupby(["model_name", "task_id"])["chosen_option"].agg(lambda s: s.value_counts(normalize=True).iloc[0])
        stab = st.groupby("model_name").agg(["mean", "size"]).reset_index()
        stab.columns = ["model_name", "modal_choice_agreement", "tasks_with_reruns"]
        stab.to_csv(f"{out}/stability.csv", index=False)
        res["stab"] = stab

    # heterogeneity across models: brand x model interaction (HE11)
    if len(models) > 1:
        full = smf.ols("chosen ~ C(brand_tier, Treatment('fictitious'))*C(model) + C(position)*C(model) + "
                       "C(price_level)*C(model) + C(rating)*C(model) + C(category)", data=m3).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(m3["task_id"])[0]})
        names = [n for n in full.params.index if n.startswith("C(brand_tier") and ":C(model)" in n]
        if names:
            R = np.zeros((len(names), len(full.params)))
            for i, n in enumerate(names):
                R[i, list(full.params.index).index(n)] = 1
            w = full.wald_test(R, scalar=True)
            res["het"] = {"brand_x_model_F": float(w.statistic), "p": float(w.pvalue), "df": len(names)}
    return res


# ----------------------------------------------------------------------------
def style(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def charts(res, out, dry=False):
    tag = "SIMULATED AGENTS (dry run) - " if dry else ""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "text.color": INK, "axes.labelcolor": INK2})

    # 1. AMCE forest plot, one panel per model (small multiples share the axis)
    pooled = res["pooled"]
    order = [k for k in NICE if k in set(pooled["term"])]
    models = sorted(pooled["model"].unique())
    fig, axes = plt.subplots(1, len(models), figsize=(3.6 * len(models) + 2.2, 0.32 * len(order) + 1.4),
                             sharey=True, sharex=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        d = pooled[pooled.model == m].set_index("term").reindex(order)
        y = np.arange(len(order))[::-1]
        ax.axvline(0, color=INK2, lw=0.8)
        ax.hlines(y, d["ci_low"] * 100, d["ci_high"] * 100, color=BLUE, lw=2, alpha=0.45)
        ax.plot(d["amce"] * 100, y, "o", color=BLUE, ms=5)
        ax.set_title(m, fontsize=10, color=INK, loc="left")
        ax.set_xlabel("Change in probability of being chosen (pp)")
        style(ax)
    axes[0][0].set_yticks(np.arange(len(order))[::-1])
    axes[0][0].set_yticklabels([NICE[k] for k in order])
    fig.suptitle(tag + "What moves each agent's booking choice (95% CI; reference: fictitious brand, listed 1st, median price)",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(f"{out}/fig_amce_by_model.png", dpi=180)
    plt.close(fig)

    # 2. Brand effect M1 vs M3
    b = res["brand"][res["brand"].term == "brand_tier[high]"]
    if len(b):
        fig, ax = plt.subplots(figsize=(8, 0.7 * b["model"].nunique() + 1.8))
        mods = sorted(b["model"].unique())
        for j, (mode, col) in enumerate([("M1 names only", BLUE), ("M3 full listings", ORANGE)]):
            d = b[b["mode"] == mode].set_index("model").reindex(mods)
            y = np.arange(len(mods)) + (0.18 if j == 0 else -0.18)
            ax.hlines(y, d["ci_low"].to_numpy() * 100, d["ci_high"].to_numpy() * 100, color=col, lw=2, alpha=0.5)
            ax.plot(d["amce"].to_numpy() * 100, y, "o", color=col, ms=7, label=mode)
        ax.set_yticks(np.arange(len(mods)))
        ax.set_yticklabels(mods)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_xlabel("Real high-equity brand vs fictitious name (pp)")
        ax.set_title(tag + "Brand advantage: names only (M1) vs full listings (M3)", loc="left", fontsize=11, pad=26)
        ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.2)
        style(ax)
        fig.tight_layout()
        fig.savefig(f"{out}/fig_brand_m1_vs_m3.png", dpi=180)
        plt.close(fig)

    # 3. Dominance hit rate
    if "dom" in res:
        d = res["dom"].sort_values("hit_rate")
        fig, ax = plt.subplots(figsize=(8, 0.5 * len(d) + 1.3))
        ax.barh(np.arange(len(d)), d["hit_rate"] * 100, color=BLUE, height=0.55)
        ax.set_yticks(np.arange(len(d)))
        ax.set_yticklabels(d["model"])
        yy = np.arange(len(d))
        ax.hlines(yy, (d["hit_rate"] - 1.96 * d["se"]).to_numpy() * 100, (d["hit_rate"] + 1.96 * d["se"]).to_numpy() * 100,
                  color=INK2, lw=1.2)
        for y, (v, se) in enumerate(zip(d["hit_rate"], d["se"])):
            ax.text((v + 1.96 * se) * 100 + 1.5, y, f"{v:.0%}", va="center", color=INK, fontsize=9)
        ax.set_xlim(0, 105)
        ax.set_xlabel("Share of tasks where the strictly best option was booked (%)")
        ax.set_title(tag + "Booked the option best on every stated need?", loc="left", fontsize=11)
        style(ax)
        fig.tight_layout()
        fig.savefig(f"{out}/fig_dominance.png", dpi=180)
        plt.close(fig)


# ----------------------------------------------------------------------------
def validate(long, cfg_path, out):
    """Dry run only: fit a conditional logit and compare to the planted mock weights."""
    import yaml
    from statsmodels.discrete.conditional_models import ConditionalLogit
    cfg = {m["name"]: m for m in yaml.safe_load(open(cfg_path))["models"]}
    m3 = long[(long["mode"] == "M3") & (long["task_type"] == "random")].copy()
    rows = []
    for m in sorted(m3.model.unique()):
        d = m3[m3.model == m]
        X = pd.get_dummies(d[["brand_tier", "price_level", "rating", "cancellation", "badge", "fee_display",
                              "brand_copy", "position"]].astype(str), dtype=float)
        drop = ["brand_tier_fictitious", "price_level_median", "rating_low", "cancellation_nonrefundable",
                "badge_none", "fee_display_all_in", "brand_copy_weak", "position_3", "position_4"]
        X = X.drop(columns=[c for c in drop if c in X])
        X["n_priorities_met"] = d["n_priorities_met"].values
        # absorb the other planted terms so the comparison is clean
        for c in ["review_volume", "review_recency", "info_format", "channel"]:
            X = X.join(pd.get_dummies(d[c].astype(str), prefix=c, drop_first=True, dtype=float))
        fit = ConditionalLogit(d["chosen"].values, X.values, groups=pd.factorize(d["run_id"])[0]).fit(disp=0)
        est = pd.Series(fit.params, index=X.columns)
        se = pd.Series(fit.bse, index=X.columns)
        w = cfg[m]["weights"]
        planted = {"brand_tier_high": w["brand_tier"].get("high", 0), "brand_tier_low": w["brand_tier"].get("low", 0),
                   "price_level_minus15": w["price_level"].get("minus15", 0), "price_level_plus15": w["price_level"].get("plus15", 0),
                   "rating_high": w["rating"].get("high", 0), "cancellation_free": w["cancellation"].get("free", 0),
                   "badge_sponsored": w["badge"].get("sponsored", 0), "badge_scarcity": w["badge"].get("scarcity", 0),
                   "fee_display_partitioned": w["fee_display"].get("partitioned", 0),
                   "brand_copy_strong": w["brand_copy"].get("strong", 0),
                   # positions 1 and 2 vs a 3/4 baseline (both weight 0)
                   "position_1": w["position"].get("1", 0), "position_2": w["position"].get("2", 0)}
        for k, v in planted.items():
            rows.append({"model": m, "parameter": k, "planted": v, "recovered": round(est[k], 3),
                         "ci_low": round(est[k] - 1.96 * se[k], 3), "ci_high": round(est[k] + 1.96 * se[k], 3),
                         "planted_inside_95ci": abs(est[k] - v) <= 1.96 * se[k]})
    v = pd.DataFrame(rows)
    v.to_csv(f"{out}/validation_recovery.csv", index=False)
    return v


# ----------------------------------------------------------------------------
def pp(x):
    return f"{x * 100:+.1f} pp"


def report(res, out, val=None, dry=False):
    L = []
    L.append("# Study 1B-A results" + (" — DRY RUN WITH SIMULATED AGENTS (not research findings)" if dry else ""))
    L.append("")
    if dry:
        L.append("These agents choose by a known rule; this run only checks that the pipeline and "
                 "analysis recover the rule. Do not report these numbers.\n")
    L.append("## Usable answers\n")
    L.append(res["parse"].to_markdown(index=False, floatfmt=".3f"))
    L.append("\n## What moves each agent's choice (pooled AMCEs, M3 random tasks)\n")
    piv = res["pooled"].pivot(index="label", columns="model", values="amce").mul(100).round(1)
    piv = piv.reindex([NICE[k] for k in NICE if NICE[k] in piv.index])
    L.append("Percentage-point change in the probability an option is chosen. Reference levels: fictitious brand, "
             "weak copy, median price, all-in price, rating 3.6, few and old reviews, non-refundable, no badge, "
             "full JSON-LD, sold direct, listed 1st.\n")
    L.append(piv.to_markdown(floatfmt=".1f"))
    L.append("\n![AMCEs](fig_amce_by_model.png)\n")
    if len(res["rupee"]):
        L.append("## Rupee equivalents (by category)\n")
        r = res["rupee"].pivot_table(index=["category", "label"], columns="model", values="inr_equivalent").round(0)
        L.append(r.to_markdown(floatfmt=",.0f"))
    L.append("\n## Brand advantage: no evidence (M1) vs full listings (M3)\n")
    L.append(res["brand"].assign(amce=lambda d: (d.amce * 100).round(1)).drop(columns=["ci_low", "ci_high"])
             .to_markdown(index=False))
    L.append("\n![Brand](fig_brand_m1_vs_m3.png)\n")
    if "dom" in res:
        L.append("## Dominance tasks (one option best on every stated need and cheapest)\n")
        L.append(res["dom"].round(3).to_markdown(index=False))
        L.append("\n![Dominance](fig_dominance.png)\n")
    L.append("## Fee fidelity: is the stated total the real total?\n")
    L.append(res["fee"].round(3).to_markdown(index=False))
    if "stab" in res:
        L.append("\n## Stability across repeated runs\n")
        L.append(res["stab"].round(3).to_markdown(index=False))
    if "het" in res:
        h = res["het"]
        L.append(f"\n## Do models differ? (HE11)\n\nWald test of brand × model interaction: "
                 f"F = {h['brand_x_model_F']:.2f}, df = {h['df']}, p = {h['p']:.2g}.")
    if val is not None:
        L.append("\n## Pipeline validation: planted vs recovered weights (conditional logit)\n")
        L.append(f"{val['planted_inside_95ci'].mean():.0%} of planted weights fall inside the 95% CI "
                 f"(expect about 95%).\n")
        L.append(val.to_markdown(index=False))
    open(f"{out}/report.md", "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="data/tasks.jsonl")
    ap.add_argument("--runs", default="data/runs.jsonl", help="one file, or several comma-separated")
    ap.add_argument("--out", default="results")
    ap.add_argument("--validate", default=None, help="mock config: compare estimates to planted weights")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tasks, runs, long = load(args.tasks, args.runs)
    long.to_csv(f"{args.out}/option_level_data.csv", index=False)
    res = analyse(long, runs, args.out)
    dry = bool(args.validate) or bool((runs["provider"] == "mock").any())
    charts(res, args.out, dry)
    val = validate(long, args.validate, args.out) if args.validate else None
    report(res, args.out, val, dry=dry)
    print(open(f"{args.out}/report.md", encoding="utf-8").read())


if __name__ == "__main__":
    main()
