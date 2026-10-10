# Jev vs the Polymarket price on resolved markets

- Markets with a blind Jev answer: 26,174; with a priced answer: 26,174. Model: jev-1.13.0.
- Windows (month the market's reference time falls in): 2025-01, 2025-07, 2026-01, 2026-04s, 2026-07s, 2026-09. `2026-09` = markets resolved after the jev-1.13.0 release on 2026-09-10.
- Market price = last traded Yes price at least 24 h before min(end date, resolution time).
- Latency median 284 ms (p90 319 ms); 722 input tokens per request; total cost of the blind run ≈ $0.79.

## 1. Markets resolved after Jev's release (2026-09, n=9,138)

| Method | Markets | Brier (lower = better) | Log loss | AUC (95% CI) | Accuracy @0.5 |
|---|---|---|---|---|---|
| Always predict the base rate | 9138 | 0.227 | 0.647 | 0.500 | 65.1% |
| Market price, 24 h before | 9138 | 0.152 | 0.450 | 0.844 (0.836–0.852) | 77.0% |
| Jev, blind (question + rules) | 9138 | 0.220 | 0.630 | 0.615 (0.603–0.627) | 65.8% |
| Jev, told the market price | 9138 | 0.190 | 0.556 | 0.794 (0.785–0.803) | 68.1% |
| Market price (same markets as priced row) | 9138 | 0.152 | 0.450 | 0.844 (0.836–0.852) | 77.0% |
| Market price, 7 days before (n=5229) | 5229 | 0.170 | 0.498 | 0.773 (0.761–0.786) | 73.9% |

Share of markets that resolved Yes: 0.349. Spearman correlation between Jev (blind) and the market price: 0.311.

Where the answers sit: Jev median 0.32, 5th–95th percentile 0.20–0.44, above 0.5 on 2.4% of markets; market median 0.27, 5th–95th percentile 0.00–0.94, above 0.5 on 23.0%.

## 2. By category (Jev's own classification, recent window)

| Category | Markets | Yes rate | Brier market | Brier Jev | AUC market | AUC Jev |
|---|---|---|---|---|---|---|
| sports | 4194 | 0.38 | 0.186 | 0.220 | 0.774 | 0.656 |
| science_tech | 2102 | 0.35 | 0.193 | 0.235 | 0.742 | 0.516 |
| crypto_price | 1071 | 0.37 | 0.063 | 0.223 | 0.971 | 0.698 |
| politics | 882 | 0.32 | 0.080 | 0.207 | 0.956 | 0.633 |
| entertainment | 536 | 0.21 | 0.070 | 0.182 | 0.949 | 0.508 |
| economics | 319 | 0.31 | 0.083 | 0.215 | 0.954 | 0.575 |
| other | 34 | 0.09 | 0.001 | 0.139 | 1.000 | 0.430 |

Jev's category agrees with a keyword rule on 98.6% of the 8105 markets the rule could label.

## 3. Does Jev know the past? Same test by resolution month

If Jev had memorised outcomes, its AUC would be far higher on old markets than on markets resolved after its release.

| Window | Markets | Yes rate | AUC market | AUC Jev (95% CI) | AUC Jev, sports | AUC Jev, not sports | Brier market | Brier Jev |
|---|---|---|---|---|---|---|---|---|
| 2025-01 | 1102 | 0.24 | 0.942 | 0.676 (0.638–0.714) | 0.786 (n=377) | 0.626 (n=725) | 0.081 | 0.175 |
| 2025-07 | 1696 | 0.24 | 0.918 | 0.586 (0.556–0.618) | 0.787 (n=432) | 0.525 (n=1264) | 0.094 | 0.184 |
| 2026-01 | 9511 | 0.28 | 0.924 | 0.661 (0.649–0.673) | 0.668 (n=2857) | 0.645 (n=6654) | 0.099 | 0.192 |
| 2026-04s | 2340 | 0.28 | 0.853 | 0.625 (0.599–0.648) | 0.605 (n=680) | 0.590 (n=1660) | 0.133 | 0.196 |
| 2026-07s | 2387 | 0.26 | 0.860 | 0.636 (0.613–0.660) | 0.688 (n=889) | 0.584 (n=1498) | 0.127 | 0.189 |
| 2026-09 | 9138 | 0.35 | 0.844 | 0.615 (0.603–0.627) | 0.656 (n=4194) | 0.571 (n=4944) | 0.152 | 0.220 |

## 4. Calibration (recent window)

| Source | Mean predicted | Realised Yes rate | Markets |
|---|---|---|---|
| market | 0.013 | 0.024 | 2176 |
| market | 0.072 | 0.112 | 624 |
| market | 0.148 | 0.193 | 918 |
| market | 0.271 | 0.342 | 1822 |
| market | 0.423 | 0.447 | 1400 |
| market | 0.558 | 0.609 | 1118 |
| market | 0.710 | 0.762 | 395 |
| market | 0.851 | 0.886 | 158 |
| market | 0.927 | 0.973 | 111 |
| market | 0.985 | 0.995 | 416 |
| jev | 0.188 | 0.169 | 883 |
| jev | 0.236 | 0.242 | 528 |
| jev | 0.255 | 0.298 | 954 |
| jev | 0.283 | 0.287 | 1263 |
| jev | 0.310 | 0.312 | 400 |
| jev | 0.326 | 0.390 | 1443 |
| jev | 0.340 | 0.380 | 848 |
| jev | 0.350 | 0.358 | 670 |
| jev | 0.370 | 0.469 | 1136 |
| jev | 0.470 | 0.479 | 1013 |

## 5. Does adding Jev to the market price help? (5-fold CV, recent window)

| Model | Brier | Log loss | AUC | Coefficients (logit market, logit Jev) |
|---|---|---|---|---|
| market price as is | 0.152 | 0.450 | 0.844 |  |
| market only (recalibrated) | 0.150 | 0.444 | 0.844 | +0.93 |
| market + Jev blind | 0.150 | 0.444 | 0.844 | +0.92, +0.20 |

## 6. Where Jev disagrees with the market (recent window)

| Price bucket | Markets | Mean price | Realised Yes | Yes rate when Jev above its median | Yes rate when Jev below | AUC of Jev inside bucket |
|---|---|---|---|---|---|---|
| Longshots, price < 5% | 2176 | 0.013 | 0.024 | 0.017 (n=1056) | 0.030 (n=1120) | 0.480 |
| Price 5–15% | 1084 | 0.094 | 0.138 | 0.131 (n=489) | 0.145 (n=595) | 0.504 |
| Price 15–35% | 2280 | 0.252 | 0.316 | 0.324 (n=974) | 0.309 (n=1306) | 0.512 |
| Price 35–65% | 2518 | 0.483 | 0.519 | 0.541 (n=1126) | 0.501 (n=1392) | 0.536 |
| Price 65–85% | 465 | 0.727 | 0.776 | 0.761 (n=184) | 0.786 (n=281) | 0.475 |
| Price > 85% | 615 | 0.959 | 0.979 | 0.972 (n=287) | 0.985 (n=328) | 0.379 |

### Paper trades: follow Jev when it disagrees with the market by more than a threshold

Buy one Yes share at the market price when Jev is higher by more than the threshold, one No share when lower. Profit per share = payout − price. No fees or spread. Random = same number of trades picked at random, both sides equally.

**All prices** (n=9138)

| Disagreement | Trades | Buy Yes | Buy No | Mean profit per share (± s.e.) | Win rate | Random, same count |
|---|---|---|---|---|---|---|
| > 0.1 | 6800 | 3999 | 2801 | +1.2¢ ± 0.4 | 20% | +0.0¢ ± 0.5 |
| > 0.2 | 4098 | 2309 | 1789 | +0.2¢ ± 0.5 | 14% | -0.0¢ ± 0.6 |
| > 0.3 | 2042 | 879 | 1163 | -1.4¢ ± 0.6 | 9% | +0.0¢ ± 0.9 |
| > 0.4 | 991 | 188 | 803 | -2.3¢ ± 0.7 | 5% | +0.0¢ ± 1.1 |

**Only markets priced 10–90%** (n=5815)

| Disagreement | Trades | Buy Yes | Buy No | Mean profit per share (± s.e.) | Win rate | Random, same count |
|---|---|---|---|---|---|---|
| > 0.1 | 3510 | 1232 | 2278 | +1.1¢ ± 0.8 | 36% | +0.0¢ ± 0.8 |
| > 0.2 | 1512 | 246 | 1266 | -1.1¢ ± 1.2 | 32% | +0.0¢ ± 1.2 |
| > 0.3 | 669 | 27 | 642 | -3.8¢ ± 1.6 | 24% | -0.1¢ ± 1.7 |
| > 0.4 | 299 | 6 | 293 | -5.0¢ ± 2.1 | 15% | -0.2¢ ± 2.8 |

## 7. When Jev is told the market price

- Spearman(Jev priced, market) = 0.845; Spearman(Jev blind, market) = 0.311.
- Mean |Jev priced − market| = 0.147; mean |Jev blind − market| = 0.213.
- Jev's adjustment improved the squared error on 26.8% of markets, worsened it on 72.6%; net Brier change +0.0380 (negative = Jev better than the market).

## 8. Largest disagreements (recent window)

| Market | Price | Jev | Resolved |
|---|---|---|---|
| Google Maps renames Lake Ontario to "Lake America" by September 30, 2026? | 0.94 | 0.05 | Yes |
| Next US-Iran senior diplomatic meeting by September 30, 2026? | 0.05 | 0.93 | No |
| Will Hunter Biden launch a coin by September 9? | 0.94 | 0.07 | Yes |
| Will Kyler Murray be the Vikings' Week 1 starting QB? | 0.97 | 0.10 | Yes |
| Will Xi Jinping visit US by September 24? | 1.00 | 0.14 | Yes |
| Will "Patient Zero - Taylor Swift" be the #1 song this week? | 1.00 | 0.15 | Yes |
| Will "Westside Whimsy - Jhené Aiko" be the Billboard 200 #1 album for the week o | 0.99 | 0.16 | Yes |
| Next US-Iran senior diplomatic meeting by October 5, 2026? | 0.01 | 0.84 | No |
| Will Xi Jinping visit US by September 30? | 1.00 | 0.17 | Yes |
| Google Maps renames Lake Ontario to "Lake America" by September 15, 2026? | 0.88 | 0.05 | Yes |
| Will Xi Jinping visit US by September 23? | 0.98 | 0.17 | Yes |
| Israel closes its airspace by September 30? | 0.99 | 0.19 | Yes |
