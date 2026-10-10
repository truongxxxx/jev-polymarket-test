"""Attach market-price snapshots to markets_*.jsonl using the CLOB price history.

ref time  = min(end_date, closed_time)         (the event / resolution moment)
p_24h     = last YES price at or before ref - 24 h
p_7d      = last YES price at or before ref - 7 d
p_mid     = last YES price at or before the midpoint between creation and ref
Writes <in>.priced.jsonl. Skips markets whose history has no point before ref - 24 h.

    python fetch_prices.py data/markets_2026-09.jsonl [workers]
"""
import json, sys, time, datetime as dt, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (research script)"}

def parse_ts(s):
    if not s: return None
    s = s.replace("Z", "+00:00")
    if " " in s and "T" not in s: s = s.replace(" ", "T")
    try:
        return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc)
    except ValueError:
        return None

def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (i + 1)); continue
            return {"error": e.code}
        except Exception:
            time.sleep(1.5 * (i + 1))
    return {"error": "timeout"}

def last_before(hist, t):
    p = None
    for h in hist:
        if h["t"] <= t: p = h["p"]
        else: break
    return p

def work(rec):
    end = parse_ts(rec.get("end_date")); closed = parse_ts(rec.get("closed_time"))
    created = parse_ts(rec.get("created_at"))
    cands = [x for x in (end, closed) if x]
    if not cands or not rec.get("yes_token"): return None
    ref = min(cands)
    if created and ref <= created: return None
    ref_ts = int(ref.timestamp())
    start_ts = ref_ts - 9 * 86400
    url = (f"https://clob.polymarket.com/prices-history?market={rec['yes_token']}"
           f"&startTs={start_ts}&endTs={ref_ts}&fidelity=60")
    r = get(url)
    hist = r.get("history") if isinstance(r, dict) else None
    if not hist: return None
    hist.sort(key=lambda h: h["t"])
    p24 = last_before(hist, ref_ts - 86400)
    p7 = last_before(hist, ref_ts - 7 * 86400)
    p1 = last_before(hist, ref_ts - 3600)
    if p24 is None: return None
    out = dict(rec)
    out.update({"ref_time": ref.isoformat(), "p_24h": p24, "p_7d": p7, "p_1h": p1,
                "n_hist": len(hist),
                "age_days": round((ref - created).total_seconds() / 86400, 2) if created else None})
    return out

def main():
    src = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    dst = src.replace(".jsonl", ".priced.jsonl")
    rows = [json.loads(l) for l in open(src, encoding="utf-8")]
    done = set()
    try:
        for l in open(dst, encoding="utf-8"): done.add(json.loads(l)["id"])
    except FileNotFoundError: pass
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} markets, {len(done)} already priced, {len(todo)} to do", flush=True)
    kept = 0; t0 = time.time()
    with open(dst, "a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for i, fu in enumerate(as_completed(futs), 1):
            res = fu.result()
            if res:
                f.write(json.dumps(res, ensure_ascii=False) + "\n"); kept += 1
            if i % 200 == 0:
                print(f"  {i}/{len(todo)} kept {kept} ({time.time()-t0:.0f}s)", flush=True)
    print("done, kept", kept)

if __name__ == "__main__":
    main()
