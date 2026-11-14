# Polymarket FAA outage attribution forecaster

Entry for the make.fun bounty
"Forecast Polymarket's FAA outage attribution prices minute by minute,
4 hours ahead" (`polymarket-faa-attribution-02`).

`main.py` (Python 3.13, stdlib only, no network, deterministic) reads every
`*.in` case in `$MAKEFUN_INPUT_DIR` (else `/input`) and writes
`/output/<id>.out` (`$MAKEFUN_OUTPUT_DIR`): for each market and each of the
240 minutes after the checkpoint, the 5%, 25%, 50%, 75% and 95% quantiles
of that minute's Yes price.

## Model

Per market, independently: empirical h-step change quantiles blended
75/25 with the house baseline's persistence forecast.

- Polymarket Yes prices are steppy: most minutes they do not move at all,
  then they jump. A normal random walk fed with 1-minute realised
  volatility is far too wide (rare jumps inflate the standard deviation),
  while the baseline's fixed sigma 0.0025 is too wide in the centre and
  too narrow in the tails.
- For each horizon h, take the empirical quantiles of the actual h-minute
  price changes in the last 12 hours of history (720 minutes), at a grid
  of horizons interpolated in sqrt(h), and force the median change to
  zero: past drift does not persist (a market that already fell does not
  keep falling; keeping the empirical median hurt in backtest).
- Blend 75% empirical / 25% baseline, blending the two forecasts as
  prices (each clamped to [0, 1] first). The baseline share keeps a
  minimum spread for a market that has not moved at all recently, and
  the clamp-first blend keeps a small positive 5% quantile when the
  empirical tail runs past zero for a market now near zero.

## Local backtest (practice cases, own harness)

Pinball loss in percentage points, mean over markets/minutes/quantiles:

| forecast | cross-checkpoint (5 pairs p0k -> p0(k+1)) | within-history pseudo-checkpoints (105 runs) |
|---|---|---|
| house baseline (sigma 0.0025) | 0.3964 | 1.0482 |
| this entry | **0.3512** | **0.9813** |

Beats the baseline on all 5 cross-checkpoint pairs. The official house
baseline practice loss is 0.363589; my cross proxy for it is 0.3964, so
the server practice score should land near ~0.32.

Rejected in testing: per-market realised-volatility normals (1.03 cross),
h-step-std normals (0.67), keeping the empirical median drift (+0.01),
tail widening x1.25/x1.5 (+0.01/+0.02), windows shorter than 720 min
(better cross, but blow-up risk on regime shifts in the within test).

Runs in ~0.1 s per case locally; two runs on the same case write
identical bytes.
