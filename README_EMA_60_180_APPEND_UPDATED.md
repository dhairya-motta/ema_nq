## EMA 60/180 10R research status

> **Status: Research-stage only — robustness not yet established.** See [`EMA_60_180_FINAL_FINAL_REPORT.md`](EMA_60_180_FINAL_FINAL_REPORT.md) for the full evidence, assumptions, limitations, and test plan.

### Current hypothesis under test

- EMA 60/180 with a 10R target.
- Breakeven ON, reportedly triggered after a +5R move.
- Skip the first new signal after a winning trade (unvalidated hypothesis).
- One position at a time for prop-account survival tests.
- Dynamic integer-contract MNQ sizing for personal-account simulations.

### Current reported evidence (not independently recalculated in this workspace)

The supplied report states 210 baseline trades for BE ON, +5,926.5 net points, PF 1.46, and +946.3 points on its 106-trade OOS split (PF 1.11; Sharpe 0.13). The skip-after-win variant is reported at +6,497.2 points overall and +1,576.1 OOS. These are source-reported figures and require trade-ledger reconciliation and a genuinely untouched validation of the skip rule.

The report also describes a +$82,410.50 personal-account outcome for dynamic 1% equity risk on MNQ. Treat all dollar results as simulated until quantity rounding, costs, contract value, fills, and equity/drawdown calculations are independently reproduced.

### Stop-loss mechanics to verify

The research harness available in this project uses a proxy rule: initial stop distance `max(2 × ATR(14), 5 points)`, target at 10 times initial risk, breakeven trigger at +5R, and a BE stop at entry plus the configured friction allowance. It enters at the next bar's open and resolves same-bar ambiguity conservatively by checking the stop before the target. **Confirm this against the original strategy implementation before calling results an exact reproduction.**

### CFD 2010+ validation status

The research notes describe HistData NSXUSD one-minute files covering 2010–2024 plus a separate 2026 USTEC MT5 file. The raw CSVs and generated result ledger were not available in the workspace where the current report was assembled, so the complete CFD 2010+ rerun is still pending. Keep CFD feeds separate from CME futures and from one another until each feed's timestamps, gaps, schema, and costs have been audited.

### Must-pass robustness checklist

- [ ] Reconcile the original strategy rules and regenerate the trade ledger row-by-row.
- [ ] Run EMA 60/180 10R on every available CFD year from 2010 onward, feed-by-feed.
- [ ] Publish annual results and sequential walk-forward folds; no retuning on test folds.
- [ ] Validate BE ON/OFF and skip-after-win/no-skip using paired results and a final untouched lockbox.
- [ ] Stress spreads, commissions, slippage, gaps, and same-bar stop/target ambiguity.
- [ ] Run IID and block-bootstrap uncertainty analyses with fixed seeds and multiple block lengths.
- [ ] Rebuild prop-firm evaluation/funded simulation using minute-by-minute marked-to-market equity and exact current provider rules.
- [ ] Resolve conflicting reported Lucid pass-rate results before using them for risk decisions.
- [ ] Apply multiple-testing controls and retain a log of failed experiments.

**Do not describe the strategy as “proven not overfit” until these checks pass.**


### Weekend policy comparison (reported, not yet independently verified)

A supplied report dated 2026-11-01 claims that keeping trades open over weekends outperformed Friday flattening in the tested sample. For the BE-ON baseline, the report lists hold-weekend at 210 trades, PF 1.46, +5,926.5 points, +81.46R and 2,215-point max drawdown, versus Friday-flat at 235 trades, PF 1.12, +1,536.6 points, +43.33R and 3,249.1-point max drawdown. It reports similar directionality for BE-ON skip-win and BE-OFF variants. These numbers are **source-reported, not independently reproduced**: the raw datasets, trade ledger, run manifest, weekend-exit audit and named CSV outputs are not in this workspace.

The current comparison script passes Python syntax compilation, but has not been validated against the source data here. It currently models bullish crossovers only and assumes timestamps are New York-local naive timestamps; confirm that these match the intended strategy/feed. The two policies have different trade counts, so do not call results strict trade-by-trade paired deltas unless a common-signal ledger demonstrates that pairing.

**Interpretation:** the reported sample suggests Friday flattening can protect against weekend gap-through-stop losses but may truncate large 10R trend runners. This is a trade-off, not a universal rule. A prop-firm account must follow the specific account's current official weekend-holding rules. Do not treat reported Monte Carlo pass rates or personal-account equity results as verified until rerun from the actual files. The full CFD 2010+ rerun remains pending. See the weekend prompt and the final report for the audit requirements.


## Final Friday/weekend policy comparison — source-reported pending reproduction

**Decision under review:** compare four frozen policies for EMA 60/180, 10R: `allow_all` (baseline; weekend holds allowed), `flatten_friday` (force-close before the weekend), `no_friday_entries` (no new Friday entries), and `no_friday_pm` (no new entries from Friday 12:00 ET onward). The final script is `ema_60_180_final_friday_policy_audit.py`; the run instructions are in `EMA_60_180_FINAL_FRIDAY_POLICY_PROMPT.md`.

### Results supplied by the user (not independently reproduced here)

| Variant / metric | `allow_all` | `flatten_friday` | `no_friday_entries` | `no_friday_pm` |
|---|---:|---:|---:|---:|
| **V3 skip-after-win, BE ON — trades** | 187 | 199 | 166 | 180 |
| Win rate | 12.8% | 18.1% | 12.7% | 12.2% |
| Profit factor | 1.56 | 1.16 | **1.63** | 1.51 |
| Net points | +6,497.2 | +1,832.2 | +6,275.8 | +5,645.7 |
| Max closed DD (points) | 2,155.5 | 2,921.9 | 2,183.9 | 2,062.1 |
| 10R targets hit | 24 | 13 | 21 | 22 |
| Reported gap-stop breaches | 1 | 1 | 0 | 1 |
| **V1 normal, BE ON — trades** | 210 | 235 | 186 | 201 |
| Profit factor | 1.46 | 1.12 | **1.52** | 1.41 |
| Net points | +5,926.5 | +1,536.6 | +5,779.4 | +5,113.8 |
| Max closed DD (points) | 2,215.0 | 3,249.1 | 2,183.9 | 2,121.7 |

These figures are **source-reported claims**, not results independently recalculated from the input data in this workspace. The preliminary interpretation is that `no_friday_entries` may preserve much of the reported runner-driven return while removing Friday-origin entries; forced Friday flattening appears to sacrifice more long-running winners. The final run must determine whether this persists with the exact source implementation, validated timezone, real session closes, and identical costs.

### Critical risk qualifications

- `no_friday_entries` does **not** eliminate all weekend gap risk: a trade entered Monday–Thursday can still be open at Friday close. “Zero gap breaches in this sample” is not a guarantee of future safety.
- The supplied report lists a worst V3 no-Friday loss of `-1.05R` and `-560.8 points`; those figures may be inconsistent with the stated initial risk and must be reconciled from the row-level ledger.
- A hard-coded Friday 16:45 bar can be absent on early-close sessions. The final script must use and log the actual last available pre-weekend bar, with source timezone/DST verified.
- The report's 1 NQ prop-firm conclusion is not safe to generalize: the supplied table says the no-Friday 1 NQ path still breaches trailing drawdown. A Friday filter does not make NQ contract sizing safe.
- Do not treat any reported prop PASS rate as decision-grade without intraday marked-to-market equity, exact trailing-drawdown ratchets, daily-loss checks, integer-contract sizing, and verified current firm rules. CFD dollar PnL requires broker-specific contract specs and costs.

### Frozen final-run outputs

Run `ema_60_180_final_friday_policy_audit.py` using `EMA_60_180_FINAL_FRIDAY_POLICY_PROMPT.md`. Expected output folder: `ema_60_180_final_friday_audit/`, containing `data_quality_audit.csv`, `trade_ledger_all_policies.csv`, `friday_entry_filters_comparison.csv`, `paired_policy_deltas.csv`, `friction_stress.csv`, `run_manifest.json`, and `RUN_ASSUMPTIONS.txt`. Add `FINAL_REPORT.md` after the local run. Until those artifacts exist and the data/code are reconciled, keep all pasted numbers marked **previously reported / pending reproduction**.

**Stop-testing rule:** after this frozen four-policy comparison and its audit, do not add more parameter/filter variants. Only reopen the research if this run reveals a material data, timestamp, or implementation defect.


# Consolidated research ledger and final cross-history validation plan

**Purpose:** This section consolidates the research claims gathered through 2026-11-01, including the original EMA/NQ audit, weekend-hold comparison, and four-policy Friday-filter results. Unless explicitly labelled independently reproduced from the current raw inputs and run artifacts, the figures below are **source-reported**. A README is a record of evidence, not proof that the strategy is robust.

## A. Desired final question

Can the frozen EMA 60/180 10R system demonstrate repeatable positive net expectancy across the longest available history—from 2010 where the actual CFD data begins through the latest available timestamp—across separate CFD feeds and CME NQ futures, under all four Friday/weekend policies?

The final run is a robustness audit, not a parameter hunt. Keep EMA 60/180, ATR(14), `max(2 × ATR, 5 points)` initial risk, 10R target, BE +5R, 0.5-point baseline friction, and the causal skip-after-win variant fixed. Test normal/skip-after-win × BE on/off across `allow_all`, `flatten_friday`, `no_friday_entries`, and `no_friday_pm`. After this frozen run, stop optimization unless a material data or code defect invalidates the audit.

**Critical methodology rule:** Do not physically mix CFD OHLC bars with CME NQ futures or merge separate CFD brokers into a synthetic price series. Run each source independently. Cross-feed conclusions should use normalized R-based metrics and consistency measures, not pooled raw points or dollars. CME futures coverage must be reported honestly; the available NQ files previously described begin in 2022, so they do not establish NQ coverage back to 2010.

## B. Dataset coverage and audit claims gathered so far

| Dataset / feed | Previously reported coverage | Reported size | Evidence status in this workspace |
|---|---|---:|---|
| HistData NSXUSD / US Tech 100 CFD, M1 | 2010–2024 | 4,694,242 1-minute bars; 326,304 resampled 15-minute bars in an earlier audit | Source-reported audit claim; raw data not available here for rerun |
| CME NQ futures M1 | 2022-12-26 to 2026-09-29 | 93,946 15-minute bars in the supplied Friday-policy report | Source-reported; input CSVs and exact run ledger not available here |
| NQ M1 files described in earlier work | `Dataset_NQ_1min_2022_2025.csv` and `Dataset_NQ_1min_2025_2026.csv` | 1,048,575 and 350,423 rows in earlier file inspection | Previously reported local-file inventory; must be rescanned and hashed in final run |
| Separate USTEC MT5 / CFD feed | A separate 2026 file was mentioned | Exact coverage depends on the actual file | Pending file scan; do not stitch across missing years or feeds |

Every final run must output a per-file inventory: actual first/last timestamp, rows, provider/instrument, timestamp timezone and bar-open/bar-close convention, SHA-256, duplicates, invalid OHLC, gaps, overlap, missing calendar years, and costs available. If the timestamp timezone cannot be verified, mark that feed blocked for Friday policy evaluation instead of assuming New York time.

## C. Fixed strategy specification used by the current research harness

- EMA 60/180 crossover, with the available weekend/Friday script implementing **long-only bullish crossovers** unless original source reconciliation establishes otherwise.
- Signal confirmed on a 15-minute bar; entry at the next bar's open.
- ATR(14), Wilder-style/RMA-like smoothing; initial risk distance `max(2 × ATR(14), 5 index points)`.
- 10R take-profit target.
- BE ON variant: activation at +5R; the available proxy moves the stop to entry plus configured friction. Confirm this against the original source before treating it as exact.
- BE OFF variant.
- Normal signal-taking and causal skip-first-signal-after-a-net-winning-trade.
- Baseline friction: 0.5 index points per trade in the current harness; test the declared sensitivity levels. For CFD feeds, broker-specific spread, commission, swap/financing and contract size must be used where verified; otherwise dollar results remain blocked or sensitivity-only.
- Conservative same-bar ambiguity: stop before target. Gap-through-stop fills must use the next available executable price assumption rather than pretending the stop price was guaranteed.
- One position at a time in the current Friday comparison. Do not present it as a concurrent-position result.

## D. Four-policy Friday/weekend results supplied on 2026-11-01

These tables are copied from the user's supplied empirical report and are **not independently reproduced in this workspace**. Treat them as hypotheses to audit from the actual trade ledger.

### V3: skip-after-win, BE ON

| Metric | `allow_all` | `flatten_friday` | `no_friday_entries` | `no_friday_pm` |
|---|---:|---:|---:|---:|
| Trades | 187 | 199 | 166 | 180 |
| Win rate | 12.8% | 18.1% | 12.7% | 12.2% |
| Profit factor | 1.56 | 1.16 | **1.63** | 1.51 |
| Net points after 0.5 friction | +6,497.2 | +1,832.2 | +6,275.8 | +5,645.7 |
| Max reported drawdown (points) | 2,155.5 | 2,921.9 | 2,183.9 | 2,062.1 |
| 10R targets | 24 | 13 | 21 | 22 |
| BE exits | 18 | 15 | 17 | 19 |
| SL exits | 145 | 146 | 128 | 139 |
| Reported gap-stop breaches | 1 | 1 | 0 | 1 |
| Personal account: 1 NQ PnL | +$129,944.39 | +$36,643.70 | +$125,516.54 | +$112,913.47 |
| Personal account: 1 NQ max DD | $43,109.53 | $58,438.10 | $43,678.23 | $41,242.19 |

### V1: normal strategy, BE ON

| Metric | `allow_all` | `flatten_friday` | `no_friday_entries` | `no_friday_pm` |
|---|---:|---:|---:|---:|
| Trades | 210 | 235 | 186 | 201 |
| Win rate | 11.9% | 17.9% | 11.8% | 11.4% |
| Profit factor | 1.46 | 1.12 | **1.52** | 1.41 |
| Net points | +5,926.5 | +1,536.6 | +5,779.4 | +5,113.8 |
| Max reported drawdown (points) | 2,215.0 | 3,249.1 | 2,183.9 | 2,121.7 |
| 10R targets | 25 | 15 | 22 | 23 |
| Reported gap-stop breaches | 1 | 1 | 0 | 1 |
| Personal account: 1 NQ PnL | +$118,530.00 | +$30,732.04 | +$115,587.58 | +$102,276.64 |

### Preliminary interpretation, not a final verdict

In the supplied sample, `no_friday_entries` appears to preserve most of the reported full-weekend net points while reducing the number of Friday-origin entries; it has the highest reported PF for V1 and V3. `flatten_friday` has higher reported win rates but much lower net points and fewer 10R targets, consistent with truncating multi-day runners. `no_friday_pm` is a middle option. These comparisons must be recalculated from raw data before a winner is declared.

### Reported event and known inconsistency

The supplied report describes a Friday 2026-09-11 entry at 12:00 ET and a Sunday reopen labelled `2026-09-12 20:00 ET`, with a 230-point gap through the stop and an adverse fill. **2026-09-12 was a Saturday, not Sunday.** Do not repeat the exact event as verified until the raw CME timestamps identify the true Sunday reopen (likely a different calendar date) and reproduce the trade. The report also lists a worst V3 no-Friday loss of `-1.05R` alongside `-560.8 points`; reconcile this against the actual initial risk and exit fill.

`no_friday_entries` does not guarantee zero weekend gap risk: existing positions opened Monday–Thursday can remain open across the weekend. Zero observed gap breaches in a sample is not a guarantee of future safety. The Friday-flat policy must exit at the actual final available pre-weekend bar; never assume a 16:45 bar exists on an early-close session.

## E. Earlier weekend-hold vs Friday-flat results (source-reported)

| Variant | Weekend policy | Trades | PF | Net points | Net R | Max DD points | 10R hits |
|---|---|---:|---:|---:|---:|---:|---:|
| BE ON, normal | Hold weekend | 210 | 1.46 | +5,926.5 | +81.46R | 2,215.0 | 25 |
| BE ON, normal | Flatten Friday | 235 | 1.12 | +1,536.6 | +43.33R | 3,249.1 | 15 |
| BE ON, skip-win | Hold weekend | 187 | 1.56 | +6,497.2 | +91.66R | 2,155.5 | 24 |
| BE ON, skip-win | Flatten Friday | 199 | 1.16 | +1,832.2 | +43.03R | 2,921.9 | 13 |
| BE OFF, normal | Hold weekend | 204 | 1.42 | +5,898.2 | +89.34R | 2,303.7 | 27 |
| BE OFF, normal | Flatten Friday | 230 | 1.15 | +2,049.3 | +61.09R | 3,452.2 | 17 |

These are historical claims from supplied report text. Trade counts differ across policies, so the comparison is not automatically a trade-by-trade paired test. Any paired claim needs shared signal identifiers and event-level audit. Reported personal account sizing and prop Monte Carlo values also remain unverified until rebuilt from the ledger and exact sizing/rule configuration.

## F. Personal-account results supplied earlier (source-reported)

For a $100,000 starting balance, the supplied weekend report stated:

| Sizing model | Hold weekend ending equity / return | Hold max DD | Friday flat ending equity / return | Friday-flat max DD |
|---|---:|---:|---:|---:|
| Fixed 1 NQ | $218,530 (+118.5%) | $44,301 / 20.1% | $130,732 (+30.7%) | $64,982 / 43.8% |
| Fixed 1 MNQ | $111,853 (+11.9%) | $4,430 / 4.0% | $103,073 (+3.1%) | $6,498 / 6.2% |
| Fixed $1,000 risk MNQ | $172,813 (+72.8%) | $21,072 / 11.9% | $140,898 (+40.9%) | $30,953 / 19.6% |
| Dynamic 1% MNQ | $182,410 (+82.4%) | $11,240 / 8.9% | $141,924 (+41.9%) | $49,354 / 28.5% |
| Skip-win dynamic 1% MNQ | $215,815 (+115.8%) | $33,128 / 15.1% | $138,753 (+38.8%) | $35,333 / 23.1% |

All figures are simulated source claims, not verified investment returns. Confirm integer contract sizing, risk caps, point value, costs, equity marking, gap fills, and drawdown calculations.

## G. Prop-firm results and constraints gathered so far (source-reported)

Earlier reported Monte Carlo pass estimates:

| Model | Risk | Weekend hold: IID / block 5 / block 20 | Friday flat: IID / block 5 / block 20 |
|---|---:|---:|---:|
| Lucid $100K Daily | 0.25% | 49.7% / 54.7% / 57.7% | 44.8% / 46.4% / 48.2% |
| Lucid $100K Daily | 0.50% | 33.8% / 42.8% / 44.3% | 34.1% / 36.3% / 38.9% |
| CFD $100K Classic | 0.25% | 84.8% / 90.4% / 90.7% | 78.2% / 80.4% / 82.1% |

These pass rates are not decision-grade until the raw sequence, simulation code, seed, open equity, daily loss, trailing drawdown, fees, consistency, and account-stage transitions are reproduced. A weekend-hold strategy is ineligible if the exact account rules prohibit it. CFD dollar/lot PnL cannot be inferred from NQ/MNQ point values. The latest supplied four-policy table says 1 NQ can breach the trailing drawdown even with no-Friday entries; a Friday filter does not make 1 NQ safe.

## H. Earlier code/data audit findings (source-reported, must reconcile)

An earlier audit note described a HistData 2010–2024 CFD backtest and reported:
- 60/180 10R baseline: 15-minute net PnL about $533,649; 1-minute replay about $530,711; win rate around 14.90% in the reported baseline.
- BE-on results differed across 15-minute and 1-minute versions; reported net PnL was $474,041 versus $482,067, with small execution mismatches.
- A latency indexing defect was reported: the code evaluated exit bars before delayed entry, a time-travel/look-ahead execution bug. The supplied correction summary reported control PnL +$500,014, flawed-latency +$270,879, corrected delayed-entry +$350,525. These numbers require reproduction against the original code and dataset.
- The audit described approximately 25% of 60/180 10R trades crossing weekends and a large profit reduction under mandatory Friday flat. This supports investigating weekend exposure but does not establish the correct policy for every account.
- The original repository is described as long-only; do not add short trades unless the source confirms them.

Do not silently reconcile different reports by choosing the most favorable metric. Store each prior report as a separate source claim and identify which source code, dataset hash, cost model, and trade ledger produced it.

## I. Final decision criteria and stopping rule

The final robustness run must output per-feed full-period and yearly metrics, all four Friday policies, normal/skip-win × BE on/off, costs, weekend exposure, gap fills, and coverage gaps. Compare feeds using normalized R statistics while keeping every series separate. Include sequential walk-forward/yearly folds and a final verdict that can be **robust, mixed, fragile, or blocked**.

Do not declare the system a “tank” just because the aggregate curve rises. Require positive net expectancy after realistic costs across a broad majority of usable years and feeds, no single year/feed dominating results, acceptable drawdown, and correct behavior under negative controls and execution stress. If the evidence fails those standards, say so plainly. After this frozen final run, stop optimization; reopen testing only to repair a material data/code defect or to validate a genuinely new external dataset that was not available in the frozen run.

## J. Canonical final-run files

- Script: `ema_60_180_final_friday_policy_audit.py`
- Prompt: `EMA_60_180_FINAL_FRIDAY_POLICY_PROMPT.md`
- Output folder: `ema_60_180_final_friday_audit/`
- Required outputs: `data_quality_audit.csv`, `trade_ledger_all_policies.csv`, `friday_entry_filters_comparison.csv`, `paired_policy_deltas.csv`, `friction_stress.csv`, `annual_stability_by_feed.csv`, `cross_feed_normalized_summary.csv`, `run_manifest.json`, `RUN_ASSUMPTIONS.txt`, `FINAL_REPORT.md`, plus coverage and walk-forward outputs where implemented.
- Evidence status as of this README update: final script syntax-compiled; full run **not executed in this workspace** because the actual Windows data files and the claimed generated audit outputs are not present here.

## Monthly trade frequency — required final output
The final audit must report how many trades the strategy takes each month, with the month assigned from the **entry timestamp in America/New_York time**. Counts must be broken down by dataset/feed, strategy variant, and Friday policy; raw CFD and CME observations must not be pooled.

Required generated files:
- `monthly_trade_counts_and_metrics.csv` — long-format monthly trade counts plus monthly performance metrics.
- `monthly_trade_count_matrix.csv` — wide monthly count matrix for quick inspection.

Also report average, median, minimum, maximum, and zero-trade months. These values remain **pending** until the final script is run against verified local datasets; do not infer monthly counts from total trade counts or the supplied summary tables.
---

# K. Research session update — 2026-11-01: Friday-policy audit and reconciliation notes

**Purpose of this addition:** Preserve the latest analysis on top of the existing README material. This section does not replace or rewrite earlier findings. The figures below are **source-reported from the supplied audit/report**, not independently reproduced from the underlying Windows CSVs in this workspace. Keep that evidence label until the raw ledgers and source data are available and reconciled.

## K1. Frozen strategy proxy and Friday policies

The supplied final-policy report evaluates a long-only 15-minute EMA 60/180 bullish-crossover proxy:

- Signal on a confirmed 15-minute bar close; enter at the next 15-minute bar open.
- Initial risk distance: `max(2 × ATR(14), 5 index points)`.
- Take-profit: `10R`.
- Breakeven-on variant: trigger at `+5R`; the harness uses its configured stop-to-entry/friction rule where the original implementation is not yet proven identical.
- Baseline friction: `0.5 point`; conservative same-bar ambiguity handling checks stop before target.
- Variants in the supplied final audit: `V1_normal_BE_ON`, `V3_skip_after_win_BE_ON`, `V1_normal_BE_OFF`, `V3_skip_after_win_BE_OFF`.

Four execution policies are compared:

- `allow_all`: allow entries on all days and permit weekend holds.
- `flatten_friday`: force-close open positions at the actual last available Friday bar before the weekend gap; record the real bar/fill, not a hard-coded timestamp.
- `no_friday_entries`: reject new Friday entries but continue managing earlier trades normally.
- `no_friday_pm`: reject Friday entries at/after 12:00 ET; do not forcibly close existing positions.

**Important:** `no_friday_entries` does not eliminate weekend exposure or gap risk for a position opened Monday–Thursday. The final report’s zero gap-breach count for that policy is a sample result, not a guarantee.

## K2. CME NQ files, overlap, and the stitched-ledger discrepancy

The report describes two local CME NQ M1 files:

| File | Reported rows | Reported coverage |
|---|---:|---|
| `Dataset_NQ_1min_2022_2025.csv` | 1,048,575 | Ends 2025-12-11 20:52 ET |
| `Dataset_NQ_1min_2025_2026.csv` | 350,423 | Begins 2025-12-10 19:00 ET; ends 2026-09-29 19:59 ET |

The reported overlap is approximately 25 hours 52 minutes. Separate-file runs for `V3_skip_after_win_BE_ON` plus `allow_all` total 186 trades (139 + 47), while the stitched/deduplicated run is reported as 187 trades and +6,497.2 points. The report attributes the one-trade difference to a trade spanning the overlap seam. This is plausible but **not yet verified**: reconcile exact bar deduplication, timestamps, signal state, and the row-level ledgers before accepting the stitched total. Do not add separate-file trade totals and treat them as an independent stitched result.

## K3. Reported paired CME results for `V3_skip_after_win_BE_ON`

The supplied report lists these point outcomes for each file independently:

| Dataset | Policy | Trades | Net points |
|---|---|---:|---:|
| `Dataset_NQ_1min_2022_2025.csv` | `allow_all` | 139 | +5,555.7233 |
| same | `flatten_friday` | 151 | +107.4985 |
| same | `no_friday_entries` | 124 | +4,579.8862 |
| same | `no_friday_pm` | 132 | +4,706.9371 |
| `Dataset_NQ_1min_2025_2026.csv` | `allow_all` | 47 | +1,032.1134 |
| same | `flatten_friday` | 46 | +1,207.9902 |
| same | `no_friday_entries` | 41 | +1,786.5579 |
| same | `no_friday_pm` | 45 | +1,497.3769 |

These numbers are **reported, not independently reproduced**. The policy comparison is not a simple universal ranking: `flatten_friday` substantially reduces reported first-file profit, while it improves the second-file point total relative to `allow_all`. The filter’s effect varies by period and must be assessed on reconciled ledgers, not by selecting whichever sample looks best.

The cross-file summary reports (for this same variant) `allow_all`: 186 trades, 93.3013 summed net R, 0.5016 trade-weighted expectancy R; `flatten_friday`: 197 trades, 37.8452 summed net R, 0.1921 expectancy R; `no_friday_entries`: 165 trades, 82.2801 summed net R, 0.4987 expectancy R; `no_friday_pm`: 177 trades, 83.1990 summed net R, 0.4701 expectancy R. **Do not treat these as a clean continuous-history result** because the source files overlap and the reported aggregates are built from separate-file observations. Raw points must never be pooled across CFD and CME feeds.

## K4. Annual stability and an explicit contradiction in the supplied report

For `V3_skip_after_win_BE_ON`, the supplied annual table reports the following for `no_friday_entries`:

| Input file | Year | Trades | Net points | Net R |
|---|---:|---:|---:|---:|
| `Dataset_NQ_1min_2022_2025.csv` | 2022 | 1 | -53.56 | -1.01R |
| same | 2023 | 45 | +412.33 | +23.43R |
| same | 2024 | 35 | +3,018.62 | +34.72R |
| same | 2025 | 43 | +1,202.50 | +7.38R |
| `Dataset_NQ_1min_2025_2026.csv` | 2025 | 2 | -192.11 | -2.01R |
| same | 2026 | 39 | +1,978.67 | +19.76R |

**Correction to the supplied report’s headline:** its claim that “every calendar year is positive under `no_friday_entries`” is false as written. The table includes a negative 2022 result and a negative two-trade 2025 result in the second file. The second-file 2025 observations overlap the first file’s late-2025 period, so they must not be treated as a separate, independent calendar-year estimate. The reconciled continuous ledger must define one canonical 2025 result.

For context, the same table reports `allow_all` on the first file as 2 trades/-2.02R in 2022, 50/+40.41R in 2023, 37/+43.70R in 2024, and 50/+0.34R in 2025. `flatten_friday` reports 2/-1.03R in 2022, 49/+12.58R in 2023, 48/+28.36R in 2024, and 52/-16.85R in 2025. In the second file, `allow_all` reports 2 trades/-2.01R in 2025 and 45/+12.89R in 2026; `flatten_friday` reports 2/-2.01R in 2025 and 44/+16.81R in 2026. These are still source-reported, and the overlapping 2025 segment needs reconciliation.

## K5. Reported weekend gap event — September 11, 2026

The supplied report describes trade #38 in the second NQ file under `V3_skip_after_win_BE_ON` / `allow_all`:

- Signal: 2026-09-11 11:45 ET; entry: 12:00 ET Friday.
- Entry: 29,427.875; initial stop: 29,303.255.
- Next reopen: 29,073.387; the market reopened beyond the stop.
- Reported gross PnL: -354.488 points; net after 0.5-point friction: -354.988 points, approximately -2.85R.
- The report flags weekend crossing and a gap-through-stop breach. Under `no_friday_entries`, this Friday entry would be skipped.

This example demonstrates a real *type* of execution risk that ordinary bar-based stop logic can understate. It does not prove that avoiding Friday entries makes the full system safer in all dimensions, nor does it remove weekend gap risk from positions already open before Friday. Gap-fill assumptions, source timestamps, and this row must be verified against the raw bars and trade ledger.

## K6. Timezone, data-quality, and execution caveats

The report’s configured timezone mapping is source-dependent: CME NQ feeds are treated as `America/New_York`; `USATECHIDXUSD` as UTC; `USTEC` as UTC; `NSXUSD` as fixed `EST` (UTC-5, no DST); and `nasdaq` as `America/New_York`. These are **configuration claims requiring source/vendor verification**, not proof that every file’s timestamp convention is correct. Timezone-naive inputs without a verified mapping must remain blocked. DST transitions, early closes, session gaps, duplicate bars, overlap boundaries, and the actual last Friday bar must be audited explicitly.

Other important limits:

- `max_closed_dd_points` is closed-trade drawdown, not intrabar mark-to-market equity drawdown.
- The reported block-bootstrap intervals use five-trade block resampling and are descriptive; they are not calendar-aligned paired confidence intervals.
- The final harness is a research proxy until reconciled with the original `ema_nq` source code and its actual entry/exit state machine.
- The audit does not generate an official prop-firm pass rate. That requires a separately verified event-driven simulator with open-equity drawdown, exact daily/trailing loss rules, integer-contract sizing, costs, and account-stage transitions.
- Do not convert CFD points to dollars without verified broker contract specifications, spreads, commissions, financing, and fill assumptions.

## K7. Current verdict — evidence, not a final strategy endorsement

The best candidate for *further validation*, not a declared winner, remains `V3_skip_after_win_BE_ON` with `no_friday_entries`, because the supplied first-file annual results are positive in 2023–2025, the supplied 2026 result is positive, and the reported September 2026 Friday-entry gap loss would have been avoided. Against that, 2022 is negative with only one trade, 2025 is contaminated by overlapping input files, the filter sacrifices profit in the first-file aggregate, and the claimed stitched ledger has a one-trade discrepancy. The present evidence therefore supports **promising but unverified / not proven robust**, not “safe,” “tank,” or guaranteed prop-firm viability.

## K8. One remaining reconciliation pass, then stop

Do not add more filters or parameter variants. Resume only to resolve the data/code issues already identified. The next audit pass should:

1. Reconcile the two CME input files into a documented deduplicated continuous bar series, retaining source-file provenance and verifying the 25h52m overlap.
2. Re-run the frozen strategy and all four policies from a clean state on the stitched series; compare each trade against both separate-file ledgers around the seam.
3. Produce one canonical monthly and annual table from the reconciled ledger, including zero-trade months and clear ET timestamps.
4. Verify timezone/DST/session handling, actual Friday liquidation bars, and the September 11 gap-through-stop row against raw M1 data.
5. Reconcile proxy rules with the original repository implementation and calculate marked-to-market drawdown before any prop-firm claim.
6. Publish the final run manifest, hashes, assumptions, and outputs; then stop research unless a material defect or genuinely new dataset requires reopening it.

**Evidence status:** All K-section performance figures are **previously reported / pending independent reproduction**. This workspace did not contain the original Windows CSVs or full row-level trade ledger when this section was prepared. Do not relabel these figures as independently verified until the reproducible run artifacts exist.
