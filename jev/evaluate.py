# -*- coding: utf-8 -*-
"""Score Jev against the Polymarket price on resolved markets.

Reads dataset.jsonl + results_blind.jsonl (+ results_priced.jsonl if present).
Writes report.md and charts/*.png.
"""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)
RECENT = "2026-09"          # resolved after the jev-1.13.0 release (2026-09-10)
EPS = 1e-3


def load():
    ds = {}
    for l in (HERE / "dataset.jsonl").read_text(encoding="utf-8").splitlines():
        if l:
            r = json.loads(l)
            ds[r["id"]] = r
    for variant in ("blind", "priced"):
        p = HERE / f"results_{variant}.jsonl"
        if not p.exists():
            continue
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l:
                continue
            r = json.loads(l)
            if "error" in r or r["id"] not in ds:
                continue
            ds[r["id"]][f"jev_{variant}"] = r["p_yes"]
            if variant == "blind":
                ds[r["id"]]["jev_category"] = r["category"]
                ds[r["id"]]["jev_category_conf"] = r["category_conf"]
                ds[r["id"]]["latency_ms"] = r["latency_ms"]
                ds[r["id"]]["input_tokens"] = r["input_tokens"]
    rows = [r for r in ds.values() if "jev_blind" in r]
    return rows


def clip(p):
    return np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)


def brier(p, y):
    return float(np.mean((clip(p) - y) ** 2))


def logloss(p, y):
    p = clip(p)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(p, y):
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y)
    if y.min() == y.max():
        return float("nan")
    return float(roc_auc_score(y, p))


def auc_ci(p, y, n_boot=400, seed=0):
    rng = np.random.default_rng(seed)
    p, y = np.asarray(p), np.asarray(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        vals.append(auc(p[idx], y[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def accuracy(p, y):
    return float(np.mean((np.asarray(p) >= 0.5) == (np.asarray(y) == 1)))


def logit(p):
    p = clip(p)
    return np.log(p / (1 - p))


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def f3(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.3f}"


def block_metrics(rows, key_p, name):
    y = np.array([r["y"] for r in rows])
    p = np.array([r[key_p] for r in rows])
    lo, hi = auc_ci(p, y)
    return [name, len(rows), f3(brier(p, y)), f3(logloss(p, y)), f"{f3(auc(p, y))} ({lo:.3f}–{hi:.3f})",
            f"{accuracy(p, y) * 100:.1f}%"]


def main():
    rows = load()
    out = []
    windows = sorted(set(r["window"] for r in rows))
    n_priced = sum(1 for r in rows if "jev_priced" in r)
    model = "jev-1.13.0"
    out.append("# Jev vs the Polymarket price on resolved markets\n")
    out.append(f"- Markets with a blind Jev answer: {len(rows):,}; with a priced answer: {n_priced:,}. Model: {model}.")
    out.append(f"- Windows (month the market's reference time falls in): {', '.join(windows)}. "
               f"`{RECENT}` = markets resolved after the jev-1.13.0 release on 2026-09-10.")
    out.append("- Market price = last traded Yes price at least 24 h before min(end date, resolution time).")
    lat = np.array([r["latency_ms"] for r in rows])
    tok = np.array([r["input_tokens"] for r in rows])
    out.append(f"- Latency median {np.median(lat):.0f} ms (p90 {np.percentile(lat, 90):.0f} ms); "
               f"{tok.mean():.0f} input tokens per request; total cost of the blind run ≈ "
               f"${tok.sum() / 1e6 * 0.042:.2f}.\n")

    # 1. headline: recent window
    rec = [r for r in rows if r["window"] == RECENT]
    out.append(f"## 1. Markets resolved after Jev's release ({RECENT}, n={len(rec):,})\n")
    y = np.array([r["y"] for r in rec])
    base = float(y.mean())
    trows = [["Always predict the base rate", len(rec), f3(brier(np.full(len(rec), base), y)),
              f3(logloss(np.full(len(rec), base), y)), "0.500", f"{max(base, 1 - base) * 100:.1f}%"],
             block_metrics(rec, "p_24h", "Market price, 24 h before"),
             block_metrics(rec, "jev_blind", "Jev, blind (question + rules)")]
    recp = [r for r in rec if "jev_priced" in r]
    if recp:
        trows.append(block_metrics(recp, "jev_priced", "Jev, told the market price"))
        trows.append(block_metrics(recp, "p_24h", "Market price (same markets as priced row)"))
    p7 = [r for r in rec if r.get("p_7d") is not None]
    if p7:
        trows.append(block_metrics(p7, "p_7d", f"Market price, 7 days before (n={len(p7)})"))
    out.append(table(["Method", "Markets", "Brier (lower = better)", "Log loss", "AUC (95% CI)", "Accuracy @0.5"], trows))
    pjr = np.array([r["jev_blind"] for r in rec])
    pmr = np.array([r["p_24h"] for r in rec])
    out.append(f"\nShare of markets that resolved Yes: {base:.3f}. "
               f"Spearman correlation between Jev (blind) and the market price: {spearman(pjr, pmr):.3f}.")
    out.append(f"\nWhere the answers sit: Jev median {np.median(pjr):.2f}, 5th–95th percentile "
               f"{np.percentile(pjr, 5):.2f}–{np.percentile(pjr, 95):.2f}, above 0.5 on {np.mean(pjr > 0.5) * 100:.1f}% "
               f"of markets; market median {np.median(pmr):.2f}, 5th–95th percentile "
               f"{np.percentile(pmr, 5):.2f}–{np.percentile(pmr, 95):.2f}, above 0.5 on {np.mean(pmr > 0.5) * 100:.1f}%.\n")

    # 2. by category (recent)
    out.append("## 2. By category (Jev's own classification, recent window)\n")
    cats = Counter(r["jev_category"] for r in rec)
    trows = []
    for c, n in cats.most_common():
        sub = [r for r in rec if r["jev_category"] == c]
        yy = np.array([r["y"] for r in sub])
        pm = np.array([r["p_24h"] for r in sub])
        pj = np.array([r["jev_blind"] for r in sub])
        trows.append([c, n, f"{yy.mean():.2f}", f3(brier(pm, yy)), f3(brier(pj, yy)), f3(auc(pm, yy)), f3(auc(pj, yy))])
    out.append(table(["Category", "Markets", "Yes rate", "Brier market", "Brier Jev", "AUC market", "AUC Jev"], trows))
    agree = [r for r in rec if r["regex_category"] != "other"]
    if agree:
        ag = np.mean([r["regex_category"] == r["jev_category"] for r in agree])
        out.append(f"\nJev's category agrees with a keyword rule on {ag * 100:.1f}% of the {len(agree)} markets "
                   f"the rule could label.\n")

    # 3. memorization curve: by window
    out.append("## 3. Does Jev know the past? Same test by resolution month\n")
    out.append("If Jev had memorised outcomes, its AUC would be far higher on old markets than on markets "
               "resolved after its release.\n")
    trows = []
    curve = []
    for w in windows:
        sub = [r for r in rows if r["window"] == w]
        yy = np.array([r["y"] for r in sub])
        pm = np.array([r["p_24h"] for r in sub])
        pj = np.array([r["jev_blind"] for r in sub])
        lo, hi = auc_ci(pj, yy)
        sp = np.array([r["jev_category"] == "sports" for r in sub])
        a_sp = auc(pj[sp], yy[sp]) if sp.sum() >= 30 else float("nan")
        a_ns = auc(pj[~sp], yy[~sp]) if (~sp).sum() >= 30 else float("nan")
        trows.append([w, len(sub), f"{yy.mean():.2f}", f3(auc(pm, yy)), f"{f3(auc(pj, yy))} ({lo:.3f}–{hi:.3f})",
                      f"{f3(a_sp)} (n={sp.sum()})", f"{f3(a_ns)} (n={(~sp).sum()})",
                      f3(brier(pm, yy)), f3(brier(pj, yy))])
        curve.append((w, auc(pm, yy), auc(pj, yy), lo, hi, len(sub)))
    out.append(table(["Window", "Markets", "Yes rate", "AUC market", "AUC Jev (95% CI)", "AUC Jev, sports",
                      "AUC Jev, not sports", "Brier market", "Brier Jev"], trows))
    out.append("")

    # 4. calibration (recent)
    out.append("## 4. Calibration (recent window)\n")
    bins = [0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95, 1.0001]
    cal = {}
    for name, key in (("market", "p_24h"), ("jev", "jev_blind")):
        pp = np.array([r[key] for r in rec])
        yy = np.array([r["y"] for r in rec])
        edges = bins if name == "market" else list(np.unique(np.quantile(pp, np.linspace(0, 1, 11))))
        if name != "market":
            edges[-1] += 1e-6
        pts = []
        for a, b in zip(edges[:-1], edges[1:]):
            m = (pp >= a) & (pp < b)
            if m.sum() >= 20:
                pts.append((pp[m].mean(), yy[m].mean(), int(m.sum())))
        cal[name] = pts
    trows = []
    for name in ("market", "jev"):
        for pm_, yr, n in cal[name]:
            trows.append([name, f"{pm_:.3f}", f"{yr:.3f}", n])
    out.append(table(["Source", "Mean predicted", "Realised Yes rate", "Markets"], trows))
    out.append("")

    # 5. blend
    out.append("## 5. Does adding Jev to the market price help? (5-fold CV, recent window)\n")
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import KFold
    Xm = logit([r["p_24h"] for r in rec]).reshape(-1, 1)
    Xj = logit([r["jev_blind"] for r in rec]).reshape(-1, 1)
    X2 = np.hstack([Xm, Xj])
    yy = np.array([r["y"] for r in rec])
    res = {}
    for name, X in (("market only (recalibrated)", Xm), ("market + Jev blind", X2)):
        pred = np.zeros(len(yy))
        coefs = []
        for tr, te in KFold(5, shuffle=True, random_state=0).split(X):
            m = LogisticRegression(C=10.0).fit(X[tr], yy[tr])
            pred[te] = m.predict_proba(X[te])[:, 1]
            coefs.append(m.coef_[0])
        res[name] = (brier(pred, yy), logloss(pred, yy), auc(pred, yy), np.mean(coefs, axis=0))
    trows = [["market price as is", f3(brier([r["p_24h"] for r in rec], yy)), f3(logloss([r["p_24h"] for r in rec], yy)),
              f3(auc([r["p_24h"] for r in rec], yy)), ""]]
    for name, (b, ll, a, c) in res.items():
        trows.append([name, f3(b), f3(ll), f3(a), ", ".join(f"{x:+.2f}" for x in c)])
    out.append(table(["Model", "Brier", "Log loss", "AUC", "Coefficients (logit market, logit Jev)"], trows))
    out.append("")

    # 6. longshots and disagreement trades
    out.append("## 6. Where Jev disagrees with the market (recent window)\n")
    pm = np.array([r["p_24h"] for r in rec])
    pj = np.array([r["jev_blind"] for r in rec])
    trows = []
    for lo_, hi_, label in ((0.0, 0.05, "Longshots, price < 5%"), (0.05, 0.15, "Price 5–15%"), (0.15, 0.35, "Price 15–35%"),
                            (0.35, 0.65, "Price 35–65%"), (0.65, 0.85, "Price 65–85%"), (0.85, 1.01, "Price > 85%")):
        m = (pm >= lo_) & (pm < hi_)
        if m.sum() < 30:
            continue
        med = np.median(pj[m])
        hi_j = m & (pj > med)
        lo_j = m & (pj <= med)
        trows.append([label, int(m.sum()), f"{pm[m].mean():.3f}", f"{yy[m].mean():.3f}",
                      f"{yy[hi_j].mean():.3f} (n={hi_j.sum()})", f"{yy[lo_j].mean():.3f} (n={lo_j.sum()})",
                      f3(auc(pj[m], yy[m]))])
    out.append(table(["Price bucket", "Markets", "Mean price", "Realised Yes", "Yes rate when Jev above its median",
                      "Yes rate when Jev below", "AUC of Jev inside bucket"], trows))
    out.append("")
    # trade simulation: buy the side Jev favours when it disagrees by > d
    out.append("### Paper trades: follow Jev when it disagrees with the market by more than a threshold\n")
    out.append("Buy one Yes share at the market price when Jev is higher by more than the threshold, one No share "
               "when lower. Profit per share = payout − price. No fees or spread. Random = same number of trades "
               "picked at random, both sides equally.\n")
    rng = np.random.default_rng(1)
    for label, mask in (("All prices", np.ones(len(pm), bool)), ("Only markets priced 10–90%", (pm >= 0.1) & (pm <= 0.9))):
        trows = []
        pm_, pj_, yy_ = pm[mask], pj[mask], yy[mask]
        for d in (0.1, 0.2, 0.3, 0.4):
            buy_yes = pj_ - pm_ > d
            buy_no = pm_ - pj_ > d
            n = int(buy_yes.sum() + buy_no.sum())
            if n == 0:
                continue
            pnl = np.concatenate([(yy_[buy_yes] - pm_[buy_yes]), ((1 - yy_[buy_no]) - (1 - pm_[buy_no]))])
            rnd = []
            for _ in range(300):
                idx = rng.integers(0, len(yy_), n)
                side = rng.integers(0, 2, n)
                rnd.append(np.mean(np.where(side == 1, yy_[idx] - pm_[idx], (1 - yy_[idx]) - (1 - pm_[idx]))))
            se = pnl.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
            trows.append([f"> {d:.1f}", n, int(buy_yes.sum()), int(buy_no.sum()),
                          f"{pnl.mean() * 100:+.1f}¢ ± {se * 100:.1f}", f"{(pnl > 0).mean() * 100:.0f}%",
                          f"{np.mean(rnd) * 100:+.1f}¢ ± {np.std(rnd) * 100:.1f}"])
        out.append(f"**{label}** (n={int(mask.sum())})\n")
        out.append(table(["Disagreement", "Trades", "Buy Yes", "Buy No", "Mean profit per share (± s.e.)", "Win rate",
                          "Random, same count"], trows))
        out.append("")

    # 7. priced variant behaviour
    if recp:
        out.append("## 7. When Jev is told the market price\n")
        pm2 = np.array([r["p_24h"] for r in recp])
        pj2 = np.array([r["jev_priced"] for r in recp])
        pb2 = np.array([r["jev_blind"] for r in recp])
        yy2 = np.array([r["y"] for r in recp])
        out.append(f"- Spearman(Jev priced, market) = {spearman(pj2, pm2):.3f}; Spearman(Jev blind, market) = {spearman(pb2, pm2):.3f}.")
        out.append(f"- Mean |Jev priced − market| = {np.mean(np.abs(pj2 - pm2)):.3f}; mean |Jev blind − market| = {np.mean(np.abs(pb2 - pm2)):.3f}.")
        moved_to = np.sign(pj2 - pm2)
        gain = (pm2 - yy2) ** 2 - (pj2 - yy2) ** 2
        out.append(f"- Jev's adjustment improved the squared error on {np.mean(gain > 0) * 100:.1f}% of markets, "
                   f"worsened it on {np.mean(gain < 0) * 100:.1f}%; net Brier change {-(gain.mean()):+.4f} "
                   f"(negative = Jev better than the market).")
        out.append("")

    # 8. examples
    out.append("## 8. Largest disagreements (recent window)\n")
    diffs = sorted(rec, key=lambda r: -abs(r["jev_blind"] - r["p_24h"]))[:12]
    trows = [[r["question"][:80].replace("|", "/"), f"{r['p_24h']:.2f}", f"{r['jev_blind']:.2f}", "Yes" if r["y"] else "No"] for r in diffs]
    out.append(table(["Market", "Price", "Jev", "Resolved"], trows))
    out.append("")

    (HERE / "report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    charts(rows, rec, recp, curve, cal)


def spearman(a, b):
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).correlation)


def charts(rows, rec, recp, curve, cal):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    C_MKT, C_JEV, C_GRY = "#1f5fbf", "#d1495b", "#8a8f98"

    # chart 1: AUC by window
    fig, ax = plt.subplots(figsize=(9, 5))
    xs = np.arange(len(curve))
    labels = [c[0] for c in curve]
    ax.plot(xs, [c[1] for c in curve], "o-", color=C_MKT, lw=2.5, label="Market price, 24 h before")
    ax.errorbar(xs, [c[2] for c in curve], yerr=[[c[2] - c[3] for c in curve], [c[4] - c[2] for c in curve]],
                fmt="s-", color=C_JEV, lw=2.5, capsize=4, label="Jev (question + rules only)")
    ax.axhline(0.5, color=C_GRY, ls="--", lw=1)
    ax.text(len(curve) - 0.5, 0.505, "coin flip", color=C_GRY, ha="right", va="bottom")
    ax.axvline(len(curve) - 1.5, color=C_GRY, ls=":", lw=1)
    ax.text(len(curve) - 1.45, 0.98, "Jev 1.13 released\n2026-09-10", color=C_GRY, va="top", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{l}\nn={c[5]:,}" for l, c in zip(labels, curve)])
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("AUC: can it rank Yes markets above No markets?")
    ax.set_title("Resolved Polymarket markets by month: market price vs Jev, jev-1.13.0")
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "auc-by-month.png", dpi=150)
    plt.close(fig)

    # chart 2: calibration
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.plot([0, 1], [0, 1], color=C_GRY, ls="--", lw=1, label="perfect calibration")
    for name, col, lab in (("market", C_MKT, "Market price"), ("jev", C_JEV, "Jev, blind")):
        pts = cal[name]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=col, lw=2, label=lab)
        for p in pts:
            ax.annotate(f"{p[2]}", (p[0], p[1]), textcoords="offset points", xytext=(4, -12), fontsize=7, color=col)
    ax.set_xlabel("Predicted probability of Yes")
    ax.set_ylabel("Share of markets that resolved Yes")
    ax.set_title(f"Calibration on {len(rec):,} markets resolved 10 Sep – 10 Oct 2026")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(CHARTS / "calibration.png", dpi=150)
    plt.close(fig)

    # chart 3: Jev vs market scatter, coloured by outcome
    fig, ax = plt.subplots(figsize=(7, 6))
    pm = np.array([r["p_24h"] for r in rec])
    pj = np.array([r["jev_blind"] for r in rec])
    yy = np.array([r["y"] for r in rec])
    ax.scatter(pm[yy == 0], pj[yy == 0], s=6, alpha=0.35, color=C_GRY, label="resolved No")
    ax.scatter(pm[yy == 1], pj[yy == 1], s=6, alpha=0.45, color="#2a9d8f", label="resolved Yes")
    ax.plot([0, 1], [0, 1], color="black", lw=0.8, ls="--")
    ax.set_xlabel("Market price of Yes, 24 h before")
    ax.set_ylabel("Jev's probability of Yes (blind)")
    ax.set_title("Jev barely moves while the market spans the whole range")
    ax.legend(frameon=False, markerscale=3)
    fig.tight_layout()
    fig.savefig(CHARTS / "jev-vs-market-scatter.png", dpi=150)
    plt.close(fig)

    # chart 4: distribution of answers
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(pm, bins=40, range=(0, 1), alpha=0.6, color=C_MKT, label="Market price")
    ax.hist(pj, bins=40, range=(0, 1), alpha=0.6, color=C_JEV, label="Jev, blind")
    if recp:
        ax.hist([r["jev_priced"] for r in recp], bins=40, range=(0, 1), histtype="step", lw=2, color="#e9a800",
                label="Jev, told the price")
    ax.set_xlabel("Probability of Yes")
    ax.set_ylabel("Markets")
    ax.set_title("Where the answers land")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "answer-distribution.png", dpi=150)
    plt.close(fig)
    print("charts ->", CHARTS)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
