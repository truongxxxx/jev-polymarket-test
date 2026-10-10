# -*- coding: utf-8 -*-
"""Explanatory figures for the write-up: the pipeline, the memorisation test design,
and Jev's AUC on sports vs non-sports markets by window. Writes to charts/."""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"
INK, MUTED, GRID = "#1f2430", "#6b7280", "#d7dbe0"
C_MKT, C_JEV, C_CODE, C_WARN = "#1f5fbf", "#d1495b", "#2a9d8f", "#e9a800"
plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})


def box(ax, x, y, w, h, title, body, color, title_color="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.25",
                                linewidth=0, facecolor=color, alpha=0.12))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.55), w, 0.55, boxstyle="round,pad=0.02,rounding_size=0.25",
                                linewidth=0, facecolor=color))
    ax.text(x + w / 2, y + h - 0.27, title, ha="center", va="center", color=title_color, fontsize=11, weight="bold")
    ax.text(x + w / 2, y + (h - 0.55) / 2, body, ha="center", va="center", color=INK, fontsize=9.2, linespacing=1.45)


def arrow(ax, x0, y0, x1, y1, color=MUTED):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, lw=1.6, color=color))


def pipeline():
    fig, ax = plt.subplots(figsize=(12, 6.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    ax.text(0.2, 6.15, "How the test runs: code gathers, Jev judges, code scores", fontsize=14, weight="bold", color=INK)
    ax.text(0.2, 5.8, "Every box is a script in the repo. Nothing in the loop is done by hand.", fontsize=10, color=MUTED)
    # row 1: data
    box(ax, 0.2, 3.6, 2.6, 1.9, "1  Resolved markets", "Polymarket Gamma API\nYes/No, volume ≥ $10k\n6 monthly windows\n26,174 markets", C_CODE)
    box(ax, 3.3, 3.6, 2.6, 1.9, "2  Price snapshot", "CLOB price history\nlast Yes price ≥ 24 h\nbefore min(end date,\nresolution time)", C_CODE)
    box(ax, 6.4, 3.6, 2.6, 1.9, "3  State for Jev", "{ market_question,\n  resolution_rules }\n+ market_price_yes\nin the priced variant", C_CODE)
    box(ax, 9.5, 3.6, 2.3, 1.9, "4  Jev, jev-1.13.0", "Noul: resolves Yes?\nChoice: category\n0.28 s, 722 tokens\n52,348 requests", C_JEV)
    arrow(ax, 2.8, 4.55, 3.3, 4.55)
    arrow(ax, 5.9, 4.55, 6.4, 4.55)
    arrow(ax, 9.0, 4.55, 9.5, 4.55)
    # row 2: scoring
    box(ax, 0.2, 0.5, 3.6, 2.2, "5  Score against the resolution", "Brier · log loss · AUC\ncalibration curves\nmarket price vs Jev vs\nlogistic blend (5-fold CV)", C_MKT)
    box(ax, 4.2, 0.5, 3.6, 2.2, "6  Trade it on paper", "follow Jev when it disagrees\nwith the price by > 0.1 … 0.4\nprofit per share vs the same\nnumber of random trades", C_MKT)
    box(ax, 8.2, 0.5, 3.6, 2.2, "7  Memorisation check", "same test on markets resolved\nJan 2025 … Jul 2026, before\nthe model's release: a higher\nAUC there = it knows the past", C_WARN, title_color=INK)
    arrow(ax, 10.65, 3.6, 10.0, 2.7)
    arrow(ax, 10.65, 3.6, 6.0, 2.7)
    arrow(ax, 10.65, 3.6, 2.0, 2.7)
    ax.text(6.0, 0.15, "Baseline throughout: the market's own price one day before. Jev has to beat that, not a coin flip.",
            ha="center", fontsize=9.5, color=MUTED, style="italic")
    fig.tight_layout()
    fig.savefig(CHARTS / "pipeline.png", dpi=150)
    plt.close(fig)


def design():
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    ax.text(0.2, 4.3, "The memorisation test: same question, six resolution months, one release date", fontsize=14, weight="bold", color=INK)
    # timeline
    y = 2.2
    ax.plot([0.4, 11.6], [y, y], color=GRID, lw=3, solid_capstyle="round")
    months = [("Jan 2025", 1102, 0.676), ("Jul 2025", 1696, 0.586), ("Jan 2026", 9511, 0.661),
              ("Apr 2026", 2340, 0.625), ("Jul 2026", 2387, 0.636), ("Sep–Oct 2026", 9138, 0.615)]
    xs = [0.9, 2.8, 4.9, 6.3, 7.7, 10.6]
    for (lab, n, a), x in zip(months, xs):
        col = C_WARN if x < 9 else C_JEV
        ax.plot(x, y, "o", ms=16, color=col, mec="white", mew=2, zorder=3)
        ax.text(x, y - 0.55, lab, ha="center", fontsize=10, color=INK, weight="bold")
        ax.text(x, y - 0.9, f"n = {n:,}", ha="center", fontsize=9, color=MUTED)
        ax.text(x, y + 0.5, f"AUC {a:.3f}", ha="center", fontsize=10.5, color=col, weight="bold")
    rx = 9.2
    ax.plot([rx, rx], [1.0, 3.6], ls="--", color=INK, lw=1.4)
    ax.text(rx + 0.08, 3.62, "jev-1.13.0 released 10 Sep 2026", fontsize=9.5, color=INK, va="bottom")
    ax.add_patch(FancyBboxPatch((0.4, 3.0), 8.4, 0.55, boxstyle="round,pad=0.02,rounding_size=0.2", lw=0, facecolor=C_WARN, alpha=0.18))
    ax.text(4.6, 3.27, "outcomes were in the news before the model was trained: if Jev memorised them, AUC should be high here",
            ha="center", va="center", fontsize=9.5, color=INK)
    ax.add_patch(FancyBboxPatch((9.4, 3.0), 2.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.2", lw=0, facecolor=C_JEV, alpha=0.18))
    ax.text(10.5, 3.27, "cannot be memorised", ha="center", va="center", fontsize=9.5, color=INK)
    ax.text(6.0, 0.35, "Found: the same AUC on both sides of the line. Jev did not learn the outcomes.",
            ha="center", fontsize=11, color=INK, weight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS / "memorisation-design.png", dpi=150)
    plt.close(fig)


def sports_chart():
    from sklearn.metrics import roc_auc_score
    ds = {}
    for l in (HERE / "dataset.jsonl").read_text(encoding="utf-8").splitlines():
        if l:
            r = json.loads(l)
            ds[r["id"]] = r
    for l in (HERE / "results_blind.jsonl").read_text(encoding="utf-8").splitlines():
        if l:
            r = json.loads(l)
            if "error" not in r and r["id"] in ds:
                ds[r["id"]]["pj"] = r["p_yes"]
                ds[r["id"]]["cat"] = r["category"]
    groups = defaultdict(lambda: {"sports": ([], []), "other": ([], []), "mkt": ([], [])})
    for r in ds.values():
        if "pj" not in r:
            continue
        g = groups[r["window"]]
        k = "sports" if r["cat"] == "sports" else "other"
        g[k][0].append(r["pj"]); g[k][1].append(r["y"])
        g["mkt"][0].append(r["p_24h"]); g["mkt"][1].append(r["y"])
    wins = sorted(groups)
    labels = {"2025-01": "Jan 2025", "2025-07": "Jul 2025", "2026-01": "Jan 2026", "2026-04s": "Apr 2026",
              "2026-07s": "Jul 2026", "2026-09": "Sep–Oct 2026\n(after release)"}
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(wins))
    wdt = 0.27
    for i, (k, col, lab) in enumerate((("mkt", C_MKT, "Market price, all markets"), ("sports", C_JEV, "Jev, sports markets"),
                                        ("other", "#f0a3ad", "Jev, everything else"))):
        vals = [roc_auc_score(groups[w][k][1], groups[w][k][0]) for w in wins]
        ns = [len(groups[w][k][1]) for w in wins]
        bars = ax.bar(x + (i - 1) * wdt, vals, wdt - 0.03, color=col, label=lab)
        for b, v, n in zip(bars, vals, ns):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.2f}", ha="center", fontsize=8.5, color=INK)
    ax.axhline(0.5, color=MUTED, ls="--", lw=1)
    ax.set_ylim(0.4, 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([labels[w] for w in wins])
    ax.set_ylabel("AUC")
    ax.set_title("Only sports hints at memory: Jev's AUC on 2025 sports markets is higher, nothing else moves")
    ax.legend(frameon=False, loc="upper right", ncol=3, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS / "auc-sports-vs-rest.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    design()
    sports_chart()
    print("ok ->", CHARTS)
