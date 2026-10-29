"""
Generate Study 1B-A choice tasks (stimuli) as JSONL.

Each task is fully pre-rendered, so every model sees byte-identical text.

Usage:
    python generate.py --m3 400 --m1 100 --seed 2026 --out data/tasks.jsonl
      --m3  M3 (controlled listing) tasks per category  (DOMINANT_SHARE of them are dominance tasks)
      --m1  M1 (parametric, names-only) tasks per category
"""
import argparse
import copy
import json
import os
import random

import design as D

CATEGORIES = list(D.SCENARIOS.keys())
MISSING_KEYS = ["cancellation", "review_recency", "review_volume"]   # hidden in "missing_keys" format


def round_price(x, cat):
    step = 10 if cat == "cabs" else 50
    return int(round(x / step) * step)


def sample_brands(rng, cat, tiers=None):
    """Assign a tier to each option (iid unless given) and draw distinct names within the task."""
    pools = {t: list(names) for t, names in D.BRANDS[cat].items()}
    if tiers is None:
        tiers = [rng.choice(D.COMMON_LEVELS["brand_tier"]) for _ in range(D.N_OPTIONS)]
    out = []
    for t in tiers:
        name = rng.choice(pools[t])
        pools[t].remove(name)
        out.append((t, name))
    return out


def random_attrs(rng, cat):
    a = {k: rng.choice(v) for k, v in D.COMMON_LEVELS.items() if k != "brand_tier"}
    a["channel"] = rng.choice(D.CHANNEL_LEVELS[cat])
    for k, v in D.CATEGORY_LEVELS[cat].items():
        a[k] = rng.choice(v)
    return a


def price_fields(a, cat):
    total = round_price(D.SCENARIOS[cat]["median_price"] * D.PRICE_MULT[a["price_level"]], cat)
    if a["fee_display"] == "partitioned":
        fees = round_price(total * D.FEE_SHARE, cat)
        return {"total_price": total, "headline_price": total - fees, "fees": fees}
    return {"total_price": total, "headline_price": total, "fees": 0}


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
def facts(o, cat):
    """Human-readable facts for one option, keyed by attribute."""
    f = {}
    if cat == "flights":
        dep = {"morning": "07:10", "evening": "18:40", "redeye": "23:55"}[o["departure"]]
        f["departure"] = f"Departs {dep}"
        f["stops"] = ("Non-stop, 2 h 10 min" if o["stops"] == "nonstop"
                      else "1 stop (via Ahmedabad), 5 h 05 min")
        f["on_time"] = "On-time performance last month: " + ("91%" if o["on_time"] == "high" else "68%")
        f["checked_bag"] = ("15 kg checked bag included" if o["checked_bag"] == "included"
                            else "Cabin bag only; checked bag extra")
    elif cat == "hotels":
        f["distance_km"] = f"{o['distance_km']} km from MG Road"
        f["breakfast"] = "Breakfast included" if o["breakfast"] == "included" else "Room only (no breakfast)"
    else:
        f["eta_min"] = f"Driver {o['eta_min']} min away"
        f["vehicle"] = "Sedan (4 seats, large boot)" if o["vehicle"] == "sedan" else "Mini hatchback"
        f["driver_rating"] = f"Driver rating {o['driver_rating']}"
        if o["surge"] == "1.6x":
            f["surge"] = "Surge pricing 1.6x in effect"
    f["rating"] = f"Rating {D.RATING_VALUE[o['rating']]}/5"
    f["review_volume"] = f"{D.VOLUME_VALUE[o['review_volume']]:,} reviews"
    f["review_recency"] = D.RECENCY_TEXT[o["review_recency"]]
    f["cancellation"] = D.CANCEL_TEXT[o["cancellation"]]
    f["channel"] = D.CHANNEL_TEXT[o["channel"]]
    return f


def price_text(o, cat):
    unit = D.SCENARIOS[cat]["unit"]
    if o["fee_display"] == "partitioned":
        return f"₹{o['headline_price']:,} ({unit}) + ₹{o['fees']:,} convenience fee & taxes added at checkout"
    return f"₹{o['total_price']:,} ({unit}, all taxes and fees included)"


def render_jsonld(o, cat, hide):
    f = facts(o, cat)
    item_type = {"flights": "Flight", "hotels": "Hotel", "cabs": "TaxiService"}[cat]
    prov_type = {"flights": "Airline", "hotels": "Organization", "cabs": "Organization"}[cat]
    offer = {
        "@context": "https://schema.org",
        "@type": "Offer",
        "itemOffered": {"@type": item_type,
                        "provider": {"@type": prov_type, "name": o["brand"],
                                     "description": D.COPY_TEXT[o["brand_copy"]]}},
        "price": o["headline_price"],
        "priceCurrency": "INR",
    }
    if o["fee_display"] == "partitioned":
        offer["priceSpecification"] = {"@type": "PriceSpecification",
                                       "description": f"+ ₹{o['fees']} convenience fee & taxes added at checkout"}
    else:
        offer["priceSpecification"] = {"@type": "PriceSpecification",
                                       "description": "All taxes and fees included"}
    rating = {"@type": "AggregateRating", "ratingValue": D.RATING_VALUE[o["rating"]]}
    if "review_volume" not in hide:
        rating["reviewCount"] = D.VOLUME_VALUE[o["review_volume"]]
    offer["itemOffered"]["aggregateRating"] = rating
    props = []
    for k, v in f.items():
        if k in ("rating", "review_volume") or k in hide:
            continue
        props.append({"@type": "PropertyValue", "name": k, "value": v})
    offer["additionalProperty"] = props
    return json.dumps(offer, ensure_ascii=False)


def render_prose(o, cat):
    f = facts(o, cat)
    parts = [f"{o['brand']}. {D.COPY_TEXT[o['brand_copy']]}", price_text(o, cat) + "."]
    for k, v in f.items():
        parts.append(v + ".")
    return " ".join(parts)


def render_option(o, cat):
    head = f"Option {o['label']}"
    if D.BADGE_TEXT[o["badge"]]:
        head += f"  [{D.BADGE_TEXT[o['badge']]}]"
    fmt = o["info_format"]
    if fmt == "prose":
        body = render_prose(o, cat)
    else:
        hide = MISSING_KEYS if fmt == "missing_keys" else []
        body = render_jsonld(o, cat, hide)
    return head + "\n" + body


def render_listing(options, cat):
    return "\n\n".join(render_option(o, cat) for o in options)


# ----------------------------------------------------------------------------
# Task builders
# ----------------------------------------------------------------------------
def fill(template, **kw):
    for k, v in kw.items():
        template = template.replace("{" + k + "}", v)
    return template


def finalize(options, rng):
    rng.shuffle(options)
    for i, o in enumerate(options):
        o["position"] = i + 1
        o["label"] = "ABCDEFGH"[i]
    return options


def build_m3(rng, cat, task_id, dominant):
    persona_id = rng.choice(list(D.PERSONAS))
    brands = sample_brands(rng, cat)
    options = []
    for (tier, name) in brands:
        a = random_attrs(rng, cat)
        a.update({"brand_tier": tier, "brand": name})
        options.append(a)

    dom_idx = None
    if dominant:
        best = dict(D.DOMINANCE_BASE)
        best.update(D.PERSONAS[persona_id]["priorities"][cat])
        dom_idx = rng.randrange(D.N_OPTIONS)
        for i, o in enumerate(options):
            if o["info_format"] == "missing_keys":
                o["info_format"] = rng.choice(["jsonld_full", "prose"])
            if i == dom_idx:
                o.update(best)
                o["price_level"] = "minus15"
                o["is_dominant"] = 1
            else:
                o["price_level"] = rng.choice(["median", "plus15"])
                # degrade at least one relevant attribute below the dominant level
                k = rng.choice(list(best))
                levels = D.COMMON_LEVELS.get(k) or D.CATEGORY_LEVELS[cat][k]
                o[k] = rng.choice([l for l in levels if l != best[k]])
                o["is_dominant"] = 0
    for o in options:
        o.update(price_fields(o, cat))
        o.setdefault("is_dominant", 0)
    options = finalize(options, rng)

    template_id = rng.choice(list(D.M3_TEMPLATES))
    sp_id = rng.choice(list(D.SYSTEM_PROMPTS))
    prompt = fill(D.M3_TEMPLATES[template_id], persona=D.PERSONAS[persona_id]["text"],
                  need=D.SCENARIOS[cat]["need"], listing=render_listing(options, cat))
    dom_label = next((o["label"] for o in options if o["is_dominant"]), None)
    return {"task_id": task_id, "mode": "M3", "task_type": "dominant" if dominant else "random",
            "category": cat, "persona_id": persona_id, "template_id": template_id,
            "system_prompt_id": sp_id, "system": D.SYSTEM_PROMPTS[sp_id], "prompt": prompt,
            "dominant_label": dom_label, "options": options}


def build_m1(rng, cat, task_id):
    persona_id = rng.choice(list(D.PERSONAS))
    brands = sample_brands(rng, cat)
    options = finalize([{"brand_tier": t, "brand": n} for t, n in brands], rng)
    listing = "\n".join(f"Option {o['label']}: {o['brand']}" for o in options)
    template_id = rng.choice(list(D.M1_TEMPLATES))
    sp_id = rng.choice(list(D.SYSTEM_PROMPTS))
    prompt = fill(D.M1_TEMPLATES[template_id], persona=D.PERSONAS[persona_id]["text"],
                  need=D.SCENARIOS[cat]["need"], listing=listing)
    return {"task_id": task_id, "mode": "M1", "task_type": "random", "category": cat,
            "persona_id": persona_id, "template_id": template_id, "system_prompt_id": sp_id,
            "system": D.SYSTEM_PROMPTS[sp_id], "prompt": prompt, "dominant_label": None,
            "options": options}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m3", type=int, default=400)
    ap.add_argument("--m1", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--categories", default=",".join(CATEGORIES))
    ap.add_argument("--out", default="data/tasks.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    tasks = []
    code = {"flights": "FLT", "hotels": "HTL", "cabs": "CAB"}
    for cat in args.categories.split(","):
        n_dom = round(args.m3 * D.DOMINANT_SHARE)
        for i in range(args.m3):
            tasks.append(build_m3(rng, cat, f"1B-A-{code[cat]}-S3-M3-{i+1:04d}", dominant=i < n_dom))
        for i in range(args.m1):
            tasks.append(build_m1(rng, cat, f"1B-A-{code[cat]}-S3-M1-{i+1:04d}"))
    rng.shuffle(tasks)   # so a partial run still covers all cells

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    n3 = sum(t["mode"] == "M3" for t in tasks)
    print(f"Wrote {len(tasks)} tasks ({n3} M3, {len(tasks) - n3} M1) to {args.out} (seed {args.seed})")


if __name__ == "__main__":
    main()
