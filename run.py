"""
Run Study 1B-A tasks against LLMs and log every call.

Commands:
  python run.py check    --config config/models.yaml
      One tiny call per enabled model: confirms keys and model strings work.
  python run.py estimate --config config/models.yaml --tasks data/tasks.jsonl [--reps 1]
      Number of calls, approximate tokens and cost before you spend anything.
  python run.py run      --config config/models.yaml --tasks data/tasks.jsonl --out data/runs.jsonl
      [--models a,b] [--modes M3,M1] [--reps 1] [--limit N] [--workers 8]
      Safe to stop and restart: finished run_ids are skipped, failed ones retried.

API keys are read from environment variables named in the config (api_key_env).
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

try:  # load API keys from a local, git-ignored .env file
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
def load_models(path, only=None):
    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    d = cfg.get("defaults", {})
    out = []
    for m in cfg["models"]:
        mm = {**d, **m}
        if only:
            if mm["name"] not in only:
                continue
        elif not mm.get("enabled", False):
            continue
        if mm.get("model") == "FILL_ME":
            sys.exit(f"Model '{mm['name']}' has model: FILL_ME -- set the exact API string first.")
        out.append(mm)
    if not out:
        sys.exit("No models selected. Enable some in the config or pass --models.")
    return out


def load_tasks(path, modes=None):
    tasks = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if modes:
        tasks = [t for t in tasks if t["mode"] in modes]
    return tasks


# ----------------------------------------------------------------------------
# Providers. Each returns (text, input_tokens, output_tokens, meta_dict).
# ----------------------------------------------------------------------------
_clients, _clients_lock = {}, threading.Lock()


def _client(m):
    key = m["name"]
    with _clients_lock:
        if key in _clients:
            return _clients[key]
        p = m["provider"]
        if p == "anthropic":
            import anthropic
            c = anthropic.Anthropic(api_key=os.environ[m["api_key_env"]])
        elif p == "openai_compat":
            from openai import OpenAI
            c = OpenAI(api_key=os.environ[m["api_key_env"]], base_url=m.get("base_url"))
        elif p == "google":
            from google import genai
            c = genai.Client(api_key=os.environ[m["api_key_env"]])
        else:
            c = None
        _clients[key] = c
        return c


def call_anthropic(m, system, prompt, task):
    kw = dict(model=m["model"], max_tokens=m["max_tokens"],
              messages=[{"role": "user", "content": prompt}])
    if system:
        kw["system"] = system
    if m.get("temperature") is not None:
        # recent Anthropic SDKs no longer expose temperature; pass it raw only if configured
        kw["extra_body"] = {"temperature": m["temperature"]}
    r = _client(m).messages.create(**kw)
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return text, r.usage.input_tokens, r.usage.output_tokens, {"stop_reason": r.stop_reason, "model_returned": r.model}


def call_openai_compat(m, system, prompt, task):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    kw = dict(model=m["model"], messages=msgs)
    kw[m.get("max_tokens_param", "max_tokens")] = m["max_tokens"]
    if m.get("temperature") is not None:
        kw["temperature"] = m["temperature"]
    if m.get("extra_body"):
        kw["extra_body"] = m["extra_body"]
    r = _client(m).chat.completions.create(**kw)
    u = r.usage
    return (r.choices[0].message.content or "", getattr(u, "prompt_tokens", None),
            getattr(u, "completion_tokens", None),
            {"stop_reason": r.choices[0].finish_reason, "model_returned": r.model})


def call_google(m, system, prompt, task):
    from google.genai import types
    cfg = dict(max_output_tokens=m["max_tokens"])
    if system:
        cfg["system_instruction"] = system
    if m.get("temperature") is not None:
        cfg["temperature"] = m["temperature"]
    r = _client(m).models.generate_content(model=m["model"], contents=prompt,
                                           config=types.GenerateContentConfig(**cfg))
    um = r.usage_metadata
    return (r.text or "", getattr(um, "prompt_token_count", None), getattr(um, "candidates_token_count", None),
            {"stop_reason": str(r.candidates[0].finish_reason) if r.candidates else None,
             "model_returned": getattr(r, "model_version", None)})


def call_mock(m, system, prompt, task, rng=None):
    """Simulated agent: multinomial logit over planted weights. For pipeline checks only."""
    import design as D
    rng = rng or random.Random()
    w = m["weights"]
    pri = D.PERSONAS[task["persona_id"]]["priorities"][task["category"]]
    util = {}
    for o in task["options"]:
        u = w["brand_tier"].get(o["brand_tier"], 0) + w["position"].get(str(o["position"]), 0)
        if task["mode"] == "M3":
            for k in ["price_level", "rating", "review_volume", "review_recency", "cancellation",
                      "badge", "channel", "fee_display", "brand_copy", "info_format"]:
                u += w.get(k, {}).get(o.get(k), 0)
            u += w.get("persona_priority", 0) * sum(o.get(k) == v for k, v in pri.items())
        util[o["label"]] = u - math.log(-math.log(rng.random()))   # + Gumbel noise
    ranking = sorted(util, key=util.get, reverse=True)
    chosen = next(o for o in task["options"] if o["label"] == ranking[0])
    out = {"chosen_option": ranking[0], "ranking": ranking, "reason": "simulated"}
    if task["mode"] == "M3":
        out["total_price_inr"] = (chosen["headline_price"] if rng.random() < m.get("p_headline_error", 0)
                                  else chosen["total_price"])
    return json.dumps(out), len(prompt) // 4, 40, {"stop_reason": "mock", "model_returned": "mock"}


PROVIDERS = {"anthropic": call_anthropic, "openai_compat": call_openai_compat,
             "google": call_google, "mock": call_mock}


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------
def parse_response(text, labels):
    """Extract the JSON answer. Returns dict with parse_ok and fields."""
    t = re.sub(r"```(?:json)?", "", text or "")
    cands = re.findall(r"\{.*\}", t, flags=re.S)
    obj = None
    for c in cands:
        try:
            obj = json.loads(c)
            break
        except json.JSONDecodeError:
            # try the last balanced-looking object
            try:
                obj = json.loads(c[: c.rfind("}") + 1])
                break
            except Exception:
                continue
    if not isinstance(obj, dict):
        return {"parse_ok": 0}
    def lab(x):
        x = re.sub(r"(?i)option", "", str(x)).strip(" .:-()[]'\"").upper()
        return x[:1]
    ch = lab(obj.get("chosen_option", ""))
    rk = [lab(x) for x in (obj.get("ranking") or []) if lab(x)]
    price = obj.get("total_price_inr")
    try:
        price = float(str(price).replace(",", "").replace("₹", "")) if price is not None else None
    except ValueError:
        price = None
    return {"parse_ok": int(ch in labels), "chosen_option": ch if ch in labels else None,
            "ranking": rk, "stated_total_price": price, "rationale_text": obj.get("reason")}


# ----------------------------------------------------------------------------
# Running
# ----------------------------------------------------------------------------
def run_one(m, task, rep, seed):
    labels = [o["label"] for o in task["options"]]
    rec = {"run_id": f"{task['task_id']}|{m['name']}|r{rep}", "task_id": task["task_id"],
           "model_name": m["name"], "provider": m["provider"], "model_string": m["model"],
           "family": m.get("family"), "openness": m.get("openness"), "tier": m.get("tier"),
           "mode": task["mode"], "category": task["category"], "rep": rep,
           "temperature": m.get("temperature"), "max_tokens": m["max_tokens"],
           "system_prompt_id": task["system_prompt_id"], "persona_id": task["persona_id"],
           "template_id": task["template_id"], "option_order": ",".join(o["brand"] for o in task["options"])}
    fn = PROVIDERS[m["provider"]]
    last_err = None
    for attempt in range(6):
        t0 = time.time()
        try:
            kw = {"rng": random.Random(int(hashlib.md5(f"{seed}|{rec['run_id']}".encode()).hexdigest()[:12], 16))} if m["provider"] == "mock" else {}
            text, tin, tout, meta = fn(m, task["system"], task["prompt"], task, **kw)
            rec.update({"timestamp_ist": dt.datetime.now(IST).isoformat(timespec="seconds"),
                        "latency_ms": int((time.time() - t0) * 1000), "input_tokens": tin,
                        "output_tokens": tout, "raw_response": text, "error": None, **meta})
            rec.update(parse_response(text, labels))
            return rec
        except Exception as e:  # rate limits, timeouts, 5xx
            last_err = f"{type(e).__name__}: {e}"
            if "FILL_ME" in str(e) or isinstance(e, KeyError):
                break
            time.sleep(min(60, 2 ** attempt + random.random()))
    rec.update({"timestamp_ist": dt.datetime.now(IST).isoformat(timespec="seconds"),
                "error": last_err, "parse_ok": 0})
    return rec


def cmd_run(args):
    models = load_models(args.config, args.models.split(",") if args.models else None)
    tasks = load_tasks(args.tasks, args.modes.split(",") if args.modes else None)
    if args.limit:
        tasks = tasks[: args.limit]
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out, encoding="utf-8"):
            r = json.loads(l)
            if not r.get("error"):
                done.add(r["run_id"])
    jobs = [(m, t, rep) for rep in range(1, args.reps + 1) for t in tasks for m in models
            if f"{t['task_id']}|{m['name']}|r{rep}" not in done]
    random.Random(args.seed).shuffle(jobs)   # interleave models over time (block randomisation)
    print(f"{len(jobs)} calls to make ({len(done)} already done) across {len(models)} models")
    sems = {m["name"]: threading.Semaphore(m.get("max_concurrency", 4)) for m in models}
    lock = threading.Lock()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    n_ok = n_err = n_bad = 0

    def work(job):
        m, t, rep = job
        with sems[m["name"]]:
            return run_one(m, t, rep, args.seed)

    with open(args.out, "a", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            with lock:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                fh.flush()
            n_err += bool(r.get("error"))
            n_bad += (not r.get("error")) and not r.get("parse_ok")
            n_ok += bool(r.get("parse_ok"))
            if i % 50 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)}  ok={n_ok} unparsed={n_bad} errors={n_err}")
    if n_err:
        print("Some calls failed; re-run the same command to retry them. First error:")
        for l in open(args.out, encoding="utf-8"):
            r = json.loads(l)
            if r.get("error"):
                print("  ", r["model_name"], r["error"][:300])
                break


def cmd_check(args):
    models = load_models(args.config, args.models.split(",") if args.models else None)
    fake = {"task_id": "CHECK", "mode": "M1", "category": "flights", "persona_id": "P1_budget_student",
            "options": [{"label": "A", "brand": "x", "brand_tier": "low", "position": 1}],
            "system": None, "prompt": 'Reply with JSON only: {"chosen_option": "A", "ranking": ["A"], "reason": "ok"}'}
    for m in models:
        try:
            text, tin, tout, meta = PROVIDERS[m["provider"]](m, None, fake["prompt"], fake)
            print(f"OK   {m['name']:<22} {m['model']:<40} -> {text.strip()[:60]!r} ({meta.get('model_returned')})")
        except Exception as e:
            print(f"FAIL {m['name']:<22} {m['model']:<40} -> {type(e).__name__}: {str(e)[:200]}")


def cmd_estimate(args):
    models = load_models(args.config, args.models.split(",") if args.models else None)
    tasks = load_tasks(args.tasks, args.modes.split(",") if args.modes else None)
    tin = sum(len(t["prompt"]) + len(t["system"] or "") for t in tasks) / 3.5   # rough chars->tokens
    tout = 120 * len(tasks)
    print(f"{len(tasks)} tasks x {args.reps} reps; ~{tin/len(tasks):.0f} input tokens per call")
    total = 0
    for m in models:
        c = args.reps * (tin * m.get("price_in", 0) + tout * m.get("price_out", 0)) / 1e6
        total += c
        print(f"  {m['name']:<22} {len(tasks)*args.reps:>7} calls  ~{tin*args.reps/1e6:.2f}M in / "
              f"{tout*args.reps/1e6:.2f}M out tokens  ~${c:.2f}" + ("" if m.get("price_in") else "  (set price_in/out)"))
    print(f"Total ~${total:.2f} (reasoning models can use many more output tokens)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["run", "check", "estimate"])
    ap.add_argument("--config", default="config/models.yaml")
    ap.add_argument("--tasks", default="data/tasks.jsonl")
    ap.add_argument("--out", default="data/runs.jsonl")
    ap.add_argument("--models", default=None, help="comma-separated names (overrides 'enabled')")
    ap.add_argument("--modes", default=None, help="M3,M1")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    {"run": cmd_run, "check": cmd_check, "estimate": cmd_estimate}[args.command](args)


if __name__ == "__main__":
    main()
