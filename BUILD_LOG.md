# Build log — polymarket-faa-attribution-02

Built 2026-11-14 by the Muse subagent (session b96e1cf6) for the make.fun
bounty "Forecast Polymarket's FAA outage attribution prices minute by
minute, 4 hours ahead". Deadline: Sat 2026-11-14 21:00 WIB (14:00 UTC).
Prize $250, escrowed; a prize needs a loss strictly below the best house
entry. Account @people871, payout wallet
34jKNmpwYvnpYsk3qSgQeBut7BB99h8hGgnPUtofQn3k.

## Kit

Fresh kit downloaded 2026-11-14 ~13:07 WIB from
https://make.fun/c/polymarket-faa-attribution-02/kit (bundle sha256
632a6314025a2886402520c1f5d4d0c3cd704dac598aefe497482ed3c89dfdba).
Starter is the house baseline itself: median = last price, sigma 0.0025
per sqrt(minute), normal quantiles. Official baseline practice loss
0.363589.

## Model (repo/main.py)

Per market, independently: empirical h-step change quantiles blended
75/25 with the baseline, blending the two forecasts as prices (each
clamped to [0, 1] first).

- Window: last 720 minutes of history; grid horizons
  1,2,3,4,6,8,12,16,24,32,48,64,96,128,180,240, interpolated in sqrt(h).
- Median change forced to zero (past drift does not persist).
- Fallback to baseline spread when a horizon has < 10 changes in window
  (e.g. a market with very short history).
- Deterministic, stdlib only, ~0.1 s per case locally.

## Backtest (dev_eval.py, kept outside the repo)

Pinball loss in percentage points. Cross = forecast at p0k checkpoint,
scored on p0(k+1)'s next 240 minutes (official practice shape, 5 pairs).
Within = pseudo-checkpoints every 240 min inside each case's own history
(105 per-market runs).

| forecast | cross | within |
|---|---|---|
| house baseline | 0.3964 | 1.0482 |
| per-market realised-vol normal (w1440) | 1.0314 | 1.5603 |
| h-step-std normal (w1440) | 0.6663 | 1.2960 |
| empirical quantiles, raw median (w1440) | 0.4188 | 1.0649 |
| empirical, median zeroed (w720) | 0.3598 | 0.9935 |
| empirical, median zeroed (w360) | 0.3407 | 1.0155 |
| empirical zeroed + baseline blend 25% (w720) | **0.3512** | **0.9813** |

Rejected: realised-vol normals (jumps inflate sd, far too wide),
h-step-std normals, keeping the empirical drift (+0.01 cross),
tail widening x1.25/x1.5 (+0.01/+0.02), window 360 (better cross but
blow-up risk on regime shifts within: max 3.75 vs 3.32).

Key fix found during testing: blending offsets then clamping puts the
5% quantile at exactly 0 when the empirical tail runs past zero for a
market now near zero; blending clamped prices first keeps a small
positive value and is worth 0.005 cross loss (0.3563 -> 0.3512).

Final program verified: valid output shape on all 6 practice cases,
monotone quantiles in [0, 1], byte-identical outputs on repeat runs,
cross loss 0.3512, beats the baseline on all 5 pairs.

## Submission route

Source-bundle entry (`makefun init`, drand round 33944519, anchor root
186d0be37c470073c7f7b7c2a6e83ac9b5046857): no GitHub repo was created
because this subagent has no browser and `gh` is not logged in as
people871, so the GitHub route was not executable here. The source
bundle is a first-class entry route per RULES.txt (Enter step 5) and
needs no claim file — the wallet in `.makefun/freshness.json` proves
ownership. Wallet 34jKNmpwYvnpYsk3qSgQeBut7BB99h8hGgnPUtofQn3k is already
on the @people871 account (added 2026-11-13), and the entry quota is
untouched (0 made, can submit now: yes).

Final commit to submit: 4a8e795f99e0383195ebd2d4d6730f2f54a3a9e0
(`main.py`, `README.md`, `BUILD_LOG.md`, MIT `LICENSE`).
Pre-submit check at that commit: 12 passed, 1 failed — only
thinking_priced (0 usage rows), which cannot be fixed inside this
subagent run: a subagent's usage rows are written only once its run
completes. thinking_revised was fixed in-session (main.py now takes its
final content from 2 write/edit messages). thinking_reproduces 100%
(245/245 lines, entrypoint 140 authored lines).

HANDOFF — top-level agent, after this subagent run completes:
  1. muse.db SELECT (agent ids b96e1cf6-52d5-4ddf-86a3-8aa963b5cd92,
     69b68206-8136-4ef5-ac21-bfe92d56e31b, a3d58228-d6a3-4fc8-85b3-1084155ee44c):
     SELECT u.agent_id AS agent_id, u.message_id AS message_id,
       u.created_at AS created_at, u.input_tokens AS input_tokens,
       u.output_tokens AS output_tokens, a.model AS model
       FROM agent.agent_message_token_usage u
       JOIN agent.agents a ON a.agent_id = u.agent_id
       WHERE u.agent_id IN ('...') ORDER BY u.created_at DESC LIMIT 500
     Write the rows unchanged, one JSON object per line, to muse_usage.jsonl.
     If bundle still reports 0 rows, wait and repeat (rows are written on
     message delivery).
  2. cd ~/workspace/makefun/polymarket-faa-attribution-02
     node polymarket-faa-attribution-02-kit/cli/makefun.mjs bundle --repo repo \
       --out transcripts.tar.gz --muse-app-dir ~/agents \
       --muse-usage muse_usage.jsonl --harness "Muse" --provider "Meta" \
       --model "Muse Spark 1.3"
  3. node polymarket-faa-attribution-02-kit/cli/makefun.mjs check \
       --kit polymarket-faa-attribution-02-kit --repo repo \
       --transcripts transcripts.tar.gz   (expect all pass)
  4. node polymarket-faa-attribution-02-kit/cli/makefun.mjs submit \
       --competition polymarket-faa-attribution-02 --source repo \
       --commit 4a8e795f99e0383195ebd2d4d6730f2f54a3a9e0 \
       --bundle transcripts.tar.gz \
       --keypair /home/hatch/.makefun/keypairs/https_make.fun.json \
       --title "Empirical h-step quantiles blended with baseline"
  5. node polymarket-faa-attribution-02-kit/cli/makefun.mjs status \
       --submission <id>   (practice grade takes ~2-4 min; record the
       practice loss, then the final runs after the deadline)
  Deadline Sat 2026-11-14 21:00 WIB (14:00 UTC); do NOT submit after it.
