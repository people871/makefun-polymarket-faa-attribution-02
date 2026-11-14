#!/usr/bin/env python3
"""Forecast Polymarket Yes prices minute by minute, 4 hours ahead.

Model (per market, independent): empirical h-step change quantiles blended
with the house baseline's persistence forecast.

Why this shape: Polymarket Yes prices are steppy -- most minutes they do not
move at all, then they jump. A normal random walk with a volatility estimated
from 1-minute returns is far too wide (the rare jumps inflate the standard
deviation), while the house baseline's fixed sigma 0.0025 is too wide in the
centre and too narrow in the tails. So for each horizon h we take the
empirical quantiles of the actual h-minute price changes seen in the last
12 hours of history (at a grid of horizons, interpolated in sqrt(h)), force
the median change to zero (past drift does not persist -- a market that
already fell does not keep falling; tested: keeping the empirical median
hurts), and blend 75/25 with the baseline. The blend keeps a minimum spread
even for a market that has not moved at all recently, which insures against
a jump out of a flat stretch.

Backtest on the kit's practice cases (my own harness, dev_eval.py):
  cross-checkpoint (official practice shape, 5 pairs p0k -> p0(k+1)):
      house baseline 0.3964 | this model 0.3512 pinball points
      (beats the baseline on all 5 pairs)
  within-history pseudo-checkpoints (105 per-market runs):
      house baseline 1.0482 | this model 0.9813 pinball points
  Official house baseline practice loss is 0.363589; my cross proxy for it
  is 0.3964, so the server practice score should land near ~0.32.

Deterministic: no randomness, no network, stdlib only. Reads every *.in in
$MAKEFUN_INPUT_DIR (else /input), writes /output/<id>.out (or
$MAKEFUN_OUTPUT_DIR). Runs in well under a second per case locally.
A market with no prices at all gets a flat 0.5 forecast so one bad market
cannot invalidate the whole case.
"""

import json
import math
import os
import sys

TAUS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z = (-1.644854, -0.67449, 0.0, 0.67449, 1.644854)
BASE_SIGMA = 0.0025      # house baseline spread, price units per sqrt(minute)
WINDOW = 720             # minutes of recent history used for empirical quantiles
BLEND = 0.25             # weight of the baseline in the final forecast
GRID = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 180, 240)


def clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def price6(x):
    v = round(clamp01(x), 6)
    return 0.0 if v == 0 else v  # never -0


def quantile(sorted_vals, tau):
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = lo + 1 if lo + 1 < n else n - 1
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def empirical_offsets(prices, horizon):
    """Grid of empirical h-step change quantiles, median recentered to 0."""
    n = len(prices)
    grid = []
    for h in GRID:
        start = n - h - WINDOW
        if start < 0:
            start = 0
        changes = sorted(prices[t + h] - prices[t] for t in range(start, n - h))
        if len(changes) < 10:
            # Too little history for this horizon: baseline spread instead.
            grid.append([z * BASE_SIGMA * math.sqrt(h) for z in Z])
            continue
        qs = [quantile(changes, tau) for tau in TAUS]
        med = qs[2]
        grid.append([q - med for q in qs])
    roots = [math.sqrt(h) for h in GRID]
    out = []
    for h in range(1, horizon + 1):
        s = math.sqrt(h)
        if s <= roots[0]:
            out.append(grid[0])
        elif s >= roots[-1]:
            out.append(grid[-1])
        else:
            k = 0
            while not (roots[k] <= s <= roots[k + 1]):
                k += 1
            f = (s - roots[k]) / (roots[k + 1] - roots[k])
            out.append([grid[k][j] * (1.0 - f) + grid[k + 1][j] * f
                        for j in range(5)])
    return out


def forecast_market(prices, horizon):
    x = prices[-1]
    emp = empirical_offsets(prices, horizon)
    rows = []
    for h in range(1, horizon + 1):
        s = math.sqrt(h)
        row = []
        for j in range(5):
            # Blend the two forecasts as prices, not as offsets: each side
            # is first clamped to [0, 1] on its own. That matters when the
            # empirical tail runs past a boundary (e.g. a -0.42 change for a
            # market now at 0.07): blending offsets then clamping would put
            # the 5% quantile at exactly 0, while blending clamped prices
            # keeps a small positive value -- the honest quantile for a
            # price that can fall to, but not below, zero.
            emp_price = price6(x + emp[h - 1][j])
            base_price = price6(x + Z[j] * BASE_SIGMA * s)
            row.append(price6((1.0 - BLEND) * emp_price
                              + BLEND * base_price))
        for j in range(1, 5):  # rounding must not break monotonicity
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def run_case(case):
    horizon = int(case["horizon_minutes"])
    forecasts = []
    for m in case["markets"]:
        prices = m["prices"]
        if not prices:
            # No price at all: there is no level to anchor on. Emit a flat
            # 0.5 forecast for this market instead of failing the whole
            # case (a failed case is scored as if every quantile were 0.5
            # for every market, so this keeps the other markets' scores).
            forecasts.append({"id": m["id"],
                              "q": [[0.5, 0.5, 0.5, 0.5, 0.5]] * horizon})
            continue
        forecasts.append({"id": m["id"],
                          "q": forecast_market(prices, horizon)})
    return {"forecasts": forecasts}


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(in_dir) if f.endswith(".in"))
    for name in names:
        case_id = name[:-3]
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        result = run_case(case)
        with open(os.path.join(out_dir, case_id + ".out"), "w",
                  encoding="utf-8") as fh:
            fh.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
