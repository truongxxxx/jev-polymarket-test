"""Merge data/markets_*.priced.jsonl into jev/dataset.jsonl with the two Jev states.

Blind state  : question + resolution rules only.
Priced state : the same plus the Yes price one day before the market's reference time.
A regex category is attached for sanity checks against Jev's own classification.
"""
import collections
import glob
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
MAX_DESC = 1200

PRICE_NOTE = ("Price of one Yes share on the prediction market one day before the market's "
              "reference time, between 0 and 1. It is the traders' implied probability that "
              "the market resolves Yes.")


def regex_category(q, ev):
    s = f"{q} {ev or ''}"
    if re.search(r"\bvs\.?\b|win on \d{4}-\d{2}-\d{2}|end in a draw|Exact Score|Both Teams to Score|O/U|"
                 r"Over/Under|spread|\bNFL\b|\bNBA\b|\bMLB\b|\bNHL\b|\bUFC\b|Grand Prix|\bATP\b|\bWTA\b|"
                 r"Premier League|Champions League|La Liga|Serie A|Bundesliga|World Series|Cup\b", s, re.I):
        return "sports"
    if re.search(r"\b(Bitcoin|BTC|Ethereum|ETH|Solana|SOL|XRP|Dogecoin|DOGE|crypto|Hyperliquid|HYPE)\b.*"
                 r"(\$|above|below|dip|reach|hit|price|all[- ]time high)|"
                 r"(\$[\d,\.]+[kKmM]?|above|below|dip to|reach).*(Bitcoin|BTC|Ethereum|ETH|Solana|SOL|XRP)", s, re.I):
        return "crypto_price"
    if re.search(r"\b(election|president|presidential|senate|congress|parliament|prime minister|governor|mayor|"
                 r"vote|poll|Trump|Biden|Harris|Putin|Zelensky|minister|party|coalition|impeach|cabinet|nominee|"
                 r"ceasefire|invade|sanction|tariff|executive order|Supreme Court|bill|law)\b", s, re.I):
        return "politics"
    if re.search(r"\b(Fed|FOMC|interest rate|rate cut|rate hike|inflation|CPI|GDP|unemployment|jobs report|ECB|"
                 r"Bank of|central bank|S&P|Nasdaq|stock|shares|IPO|market cap|earnings|revenue|Tesla|Nvidia|"
                 r"Apple|Microsoft|OpenAI|Anthropic|gold|oil|recession|bps)\b", s, re.I):
        return "economics"
    if re.search(r"\b(Oscar|Grammy|Emmy|box office|album|song|Billboard|Netflix|movie|film|Spotify|"
                 r"Rotten Tomatoes|Taylor Swift|Drake|Kanye|celebrity|Time Person|Eurovision|Nobel)\b", s, re.I):
        return "entertainment"
    if re.search(r"\b(SpaceX|Starship|launch|NASA|rocket|GPT|Gemini|Claude|Grok|AI model|LLM|iPhone|release|"
                 r"earthquake|hurricane|temperature|weather|COVID|flu|vaccine|FDA)\b", s, re.I):
        return "science_tech"
    return "other"


def main():
    random.seed(7)
    rows = []
    for path in sorted(glob.glob(str(DATA / "markets_*.priced.jsonl"))):
        window = Path(path).name.replace("markets_", "").replace(".priced.jsonl", "")
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # file may still be written by fetch_prices.py
            desc = (r.get("description") or "").strip()
            if len(desc) > MAX_DESC:
                desc = desc[:MAX_DESC].rsplit(" ", 1)[0] + " ..."
            state_blind = {"market_question": r["question"], "resolution_rules": desc}
            state_priced = dict(state_blind)
            state_priced["market_price_yes"] = round(float(r["p_24h"]), 3)
            state_priced["market_price_note"] = PRICE_NOTE
            rows.append({
                "id": r["id"], "window": window, "question": r["question"],
                "event_title": r.get("event_title"), "created_at": r.get("created_at"),
                "ref_time": r["ref_time"], "age_days": r.get("age_days"), "volume": r["volume"],
                "p_24h": r["p_24h"], "p_7d": r.get("p_7d"), "p_1h": r.get("p_1h"),
                "y": int(r["resolved_yes"]),
                "regex_category": regex_category(r["question"], r.get("event_title")),
                "state_blind": state_blind, "state_priced": state_priced,
            })
    random.shuffle(rows)
    out = HERE / "dataset.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "samples ->", out)
    print("by window:", dict(collections.Counter(r["window"] for r in rows)))
    print("by regex category:", dict(collections.Counter(r["regex_category"] for r in rows)))
    print("yes rate:", round(sum(r["y"] for r in rows) / len(rows), 3))


if __name__ == "__main__":
    main()
