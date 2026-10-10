# -*- coding: utf-8 -*-
"""Ask Jev about every market in dataset.jsonl and store the answers.

Variant blind  : question + resolution rules.           -> results_blind.jsonl
Variant priced : the same plus the Yes price at T-24h.  -> results_priced.jsonl

Each request carries one Noul (will it resolve Yes?) and one Choice (category).
Resumable: a rerun only sends the samples that are still missing.

    python run_jev.py --variant blind --dry-run
    python run_jev.py --variant blind --limit 50
    python run_jev.py --variant blind
    python run_jev.py --variant priced
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_CANDIDATES = [HERE.parent / ".env", HERE.parent.parent / "test" / ".env"]
PRICE_PER_MTOK = 0.042

YES_INSTRUCTIONS = ("The prediction market described in the state resolves Yes, meaning the event asked "
                    "about in market_question happens according to resolution_rules.")
CATEGORY = {
    "sports": "A sports match, game, season, tournament or athlete result",
    "crypto_price": "The price of a cryptocurrency reaching, staying above or below a level",
    "politics": "Elections, governments, legislation, geopolitics, wars, officials",
    "economics": "Central banks, interest rates, macro data, companies, stocks, commodities",
    "entertainment": "Movies, music, awards, television, celebrities, culture",
    "science_tech": "Technology products, AI models, space launches, science, weather, health",
    "other": "Anything that does not fit the categories above",
}


def load_api_key():
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key.strip()
    for env in ENV_CANDIDATES:
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("TYPESAFE_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        os.environ["TYPESAFE_API_KEY"] = val
                        return val
    return None


def done_ids(path):
    ids = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "error" not in r:
                ids.add(r["id"])
    return ids


async def run(samples, variant, out_path, concurrency, model):
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, RetryPolicy, TypeSafeAPIError
    questions = {
        "yes": Noul(instructions=YES_INSTRUCTIONS),
        "category": Choice(instructions="Which category does market_question belong to?", criteria=CATEGORY),
    }
    sem, lock = asyncio.Semaphore(concurrency), asyncio.Lock()
    st = {"ok": 0, "err": 0, "tok": 0}
    t0 = time.time()
    async with AsyncTypeSafeClient(model=model, retry=RetryPolicy(max_retries=6, backoff_max=30),
                                   timeout=60.0) as client:
        async def one(s):
            async with sem:
                rec = {"id": s["id"], "variant": variant}
                try:
                    t = time.time()
                    resp = await client.system_one(s[f"state_{variant}"], questions)
                    cat = resp.choices["category"]
                    rec.update({"model": resp.model, "latency_ms": round((time.time() - t) * 1000),
                                "input_tokens": resp.usage.input_tokens,
                                "p_yes": resp.nouls["yes"].noul,
                                "category": cat.choice, "category_conf": cat.confidence,
                                "category_probs": dict(cat.probabilities)})
                    st["ok"] += 1
                    st["tok"] += resp.usage.input_tokens
                except TypeSafeAPIError as e:
                    rec["error"] = f"{type(e).__name__} status={getattr(e, 'status', None)}: {e}"
                    st["err"] += 1
                    if getattr(e, "status", None) in (401, 403):
                        raise
                except Exception as e:
                    rec["error"] = f"{type(e).__name__}: {e}"
                    st["err"] += 1
                async with lock:
                    with open(out_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n = st["ok"] + st["err"]
                    if n % 200 == 0 or n == len(samples):
                        print(f"  {n}/{len(samples)} ok={st['ok']} errors={st['err']} {st['tok']:,} tok "
                              f"~ ${st['tok'] / 1e6 * PRICE_PER_MTOK:.4f} {time.time() - t0:.0f}s", flush=True)
        await asyncio.gather(*(one(s) for s in samples))
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["blind", "priced"], required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    samples = [json.loads(l) for l in (HERE / "dataset.jsonl").read_text(encoding="utf-8").splitlines() if l]
    out = HERE / f"results_{a.variant}.jsonl"
    skip = done_ids(out)
    todo = [s for s in samples if s["id"] not in skip][: a.limit]
    est = sum(len(json.dumps(s[f"state_{a.variant}"])) + 900 for s in todo) / 3.2
    print(f"Samples: {len(samples)} (done {len(skip)}, to run {len(todo)}) variant={a.variant}")
    print(f"Estimate ~{est:,.0f} tokens ~ ${est / 1e6 * PRICE_PER_MTOK:.3f} -> {out.name}")
    if a.dry_run:
        s = todo[0]
        print(json.dumps({"model": a.model, "state": s[f"state_{a.variant}"],
                          "questions": {"yes": {"type": "noul", "instructions": YES_INSTRUCTIONS},
                                        "category": {"type": "choice", "criteria": CATEGORY}}},
                         indent=1, ensure_ascii=False))
        print(f"\nSample {s['id']}: y={s['y']} p_24h={s['p_24h']} window={s['window']}")
        return
    if not todo:
        print("Nothing left to run.")
        return
    if not load_api_key():
        raise SystemExit("Missing TYPESAFE_API_KEY.")
    st = asyncio.run(run(todo, a.variant, out, a.concurrency, a.model))
    print(f"Done: ok={st['ok']} errors={st['err']}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
