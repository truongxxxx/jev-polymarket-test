"""Download resolved Polymarket markets (Gamma API) in date windows.

Usage: python fetch_markets.py 2026-09-10 2026-10-10 out.jsonl [min_volume]
Pages day by day (offset cap on the API), keeps every market with
umaResolutionStatus == resolved and a 0/1 outcome price.
"""
import json, sys, time, datetime as dt, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (research script)"}

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 422:
                return None  # offset too large
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * (i + 1)); continue
            raise
        except Exception:
            time.sleep(2 * (i + 1))
    return None

def main():
    a = dt.date.fromisoformat(sys.argv[1]); b = dt.date.fromisoformat(sys.argv[2])
    out = sys.argv[3]; minvol = float(sys.argv[4]) if len(sys.argv) > 4 else 10000
    seen = set(); n = 0
    with open(out, "w", encoding="utf-8") as f:
        d = a
        while d < b:
            e = d + dt.timedelta(days=1)
            off = 0; got = 0
            while True:
                url = ("https://gamma-api.polymarket.com/markets?closed=true&limit=100"
                       f"&offset={off}&end_date_min={d}T00:00:00Z&end_date_max={e}T00:00:00Z"
                       f"&volume_num_min={minvol}")
                res = get(url)
                if not res or not isinstance(res, list):
                    break
                for m in res:
                    if m["id"] in seen: continue
                    seen.add(m["id"])
                    try:
                        prices = json.loads(m.get("outcomePrices") or "[]")
                        outcomes = json.loads(m.get("outcomes") or "[]")
                        toks = json.loads(m.get("clobTokenIds") or "[]")
                    except Exception:
                        continue
                    if m.get("umaResolutionStatus") != "resolved": continue
                    if len(prices) != 2 or set(prices) != {"0", "1"}: continue
                    if outcomes != ["Yes", "No"]: continue
                    ev = (m.get("events") or [{}])[0]
                    rec = {
                        "id": m["id"], "question": m["question"],
                        "description": m.get("description", ""),
                        "slug": m.get("slug"), "event_title": ev.get("title"),
                        "event_slug": ev.get("slug"), "series": bool(ev.get("series")),
                        "created_at": m.get("createdAt"), "start_date": m.get("startDate"),
                        "end_date": m.get("endDate"), "closed_time": m.get("closedTime"),
                        "volume": float(m.get("volumeNum") or 0),
                        "yes_token": toks[0] if toks else None,
                        "resolved_yes": 1 if prices[0] == "1" else 0,
                        "neg_risk": m.get("negRisk"),
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n"); n += 1; got += 1
                if len(res) < 100: break
                off += 100
            print(d, "kept", got, "total", n, flush=True)
            d = e
    print("done", n)

if __name__ == "__main__":
    main()
