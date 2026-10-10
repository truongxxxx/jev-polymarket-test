"""Random subsample of a markets_*.jsonl file: python sample.py in.jsonl out.jsonl N [seed]"""
import json, random, sys
rows = [l for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
random.seed(int(sys.argv[4]) if len(sys.argv) > 4 else 7)
n = int(sys.argv[3])
keep = rows if len(rows) <= n else random.sample(rows, n)
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.writelines(keep)
print(len(rows), "->", len(keep))
