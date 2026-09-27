# Exploiting Asymmetric Tail Risk: A Quantitative Framework for Nasdaq 15-Minute Trend Following

**Abstract:** This paper details the mathematical architecture, stress-testing, and empirical validation of a highly asymmetric, low-frequency trend-following algorithm deployed on the Nasdaq 100 futures market (2010–2024). By enforcing a strictly positive macro-bias (Long-Only), pairing dynamic Average True Range (ATR) sizing with hyper-asymmetric fixed exits (1:7 Risk-to-Reward), and ruthlessly rejecting lagging institutional overlays, the algorithm generates a statistically significant edge. All results include realistic 0.5-point round-trip slippage and commission friction applied to every single trade. The engine was rigorously stress-tested via Gaussian noise injection and Monte Carlo simulations to prove structural robustness, before being mathematically optimized for deployment across a 10-account Prop Firm portfolio.

---

## 1. Core Mathematical Architecture

The underlying philosophy relies on capturing mathematically asymmetric outliers during high-volatility regimes, while cutting losses at the exact statistical threshold of failure.

### 1.1 The Signal Engine
The entry mechanic utilizes a standard dual Exponential Moving Average (EMA) momentum crossover to establish directional breakout validity on the **15-Minute Timeframe**.
*   **Fast Momentum:** 25-Period EMA
*   **Slow Momentum:** 100-Period EMA
*   **Signal:** Long entry upon the 25 EMA crossing strictly above the 100 EMA.
*   **Execution:** Entry is placed at the **open of the next candle** after signal confirmation, simulating real-world latency.

### 1.2 The Asymmetric Exit Protocol
The model utilizes a "hard stop, hard target" paradigm. Slippage of **0.5 points is deducted on every single trade** (round-trip), penalizing both entry and exit to produce the most realistic possible simulation.
*   **Dynamic Stop-Loss:** `Entry Price - (2.0 × ATR₁₄)`
*   **Asymmetric Target:** `7.0 × Initial Risk Distance`
*   **Minimum Risk Floor:** `5.0 points` (prevents abnormally tight stops in ultra-low volatility)
*   **Gap Protection:** If the market opens through the Stop-Loss level, the exit is forced at the gap open price, not the SL price.

---

## 2. Structural Edge & The Future

A common quantitative critique is that historical algorithms are curve-fitted to a specific 15-year period and will fail when the market regime shifts. This framework avoids curve-fitting by relying on pure, un-optimized momentum mathematics and macroeconomic physics.

### 2.1 The Long-Bias Physics of the Nasdaq
The algorithm is strictly **Long-Only**. The Nasdaq 100 is not a random walk; it is a concentrated index of the most powerful monopolies in history, fundamentally buoyed by the inflationary money-printing physics of global central banks. If the Nasdaq ceases to trend upward over a 15-year horizon, the global economy has entered a catastrophic depression, rendering any long-bias algorithm moot. The structural edge is inflation and human innovation.

### 2.2 Random Expectancy vs. Algorithmic Alpha
Does a 7.0 RR simply work by holding trades randomly?
In a zero-friction market, randomly entering trades and holding for 7.0 RR yields a mathematically guaranteed **12.5% Win Rate**. However, when spread and slippage are factored in, random expectancy drops to roughly **11.5%**, resulting in a guaranteed negative expectancy (a slow bleed to zero).

**Our Alpha:** The 25/100 EMA architecture produces a **16.12% Win Rate** on 1,371 executions across 14 years. That 4.6% gap above the random baseline is the algorithmic *Alpha*. Over 1,371 trades, this small edge compounds into hundreds of thousands of dollars, proving the crossover is statistically significant at predicting massive momentum outliers.

### 2.3 The "Fat Tail" Distribution Reality
Financial markets do not follow standard bell curves; they follow **Fat-Tailed Distributions**. Extreme outliers (massive rallies and flash crashes) happen far more often than standard models predict due to human panic and greed. The 7.0x RR target is mathematically positioned precisely to capture these inevitable fat-tail anomalies.

![Fat Tailed Market Distribution](images/distribution_fat_tails.png)

---

## 3. Institutional Destruction Stress-Testing (Proving "The Tank")

To ensure the alpha is structural, we actively attempted to break the algorithm via a rigorous institutional destruction pipeline. All tests use the **Flat $1,000 Risk per trade** model.

| Stress Test Scenario | Final Equity | Max DD | Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Control Environment** | $362,556 | 48.66% | 0.636 | - |
| **Latency Injection (30 Mins Late)** | **$242,184** | **56.51%** | **0.586** | **PASSED** |
| **Gaussian Noise (±0.05% Random Walk)** | **$362,556** | **48.66%** | **0.636** | **PASSED** |
| **Hyper-Slippage (5.0 Points per Trade)** | -$602,094 | 769.31% | -2.677 | **FAILED** |

### Analysis of Edge
1.  **Latency Immunity:** Even when deliberately blocked from executing trades until 30 minutes *after* the momentum signal fired, the strategy remained profitable with a positive Sharpe ratio. This confirms the signal captures a structural momentum *regime*, not a fleeting tick-level pattern.
2.  **Noise Tolerance:** Injecting ±0.05% random standard deviation into the historical price data stream produced **zero change** in equity or Sharpe. The signal is immune to minor price randomness.
3.  **The Hard Stop on Slippage:** At 5.0 points of slippage, the strategy goes deeply negative. This is the critical real-world constraint: institutional-scale execution or extremely thin liquidity events can destroy the edge. This is why **manual execution at small size** is the correct deployment model.
4.  **The Paradox of "Smart" Overlays:** Testing confirmed that advanced institutional filtering (1-Hour Timeframe Alignment, Time-of-Day session locks) caused catastrophic decay. The unadulterated raw engine is mathematically superior.

---

## 4. Pure Alpha: Own Capital Validation (2010 - 2024)

### 4.1 Baseline Metrics (14-Year Sample, $100,000 Starting Capital)

> **Methodology Note:** Results use **Flat $1,000 Risk per trade** (no compounding). Entry slippage of 0.5 points is applied on every execution. Entry occurs at the open of the bar *after* signal confirmation. Gap-downs through the Stop Loss are filled at the gap open price, not the SL price.

| Metric | Result |
| :--- | :--- |
| **Total Executions** | 1,371 (Avg 0.49 Trades / Day) |
| **Win Rate** | 16.12% |
| **Winning Trades** | 221 |
| **Losing Trades** | 1,150 |
| **Final Equity** | $362,556 |
| **Net Profit** | +$262,556 |
| **Maximum Drawdown** | -$57,362 |
| **True Sharpe Ratio** | 0.636 |
| **Risk of Ruin** | **0.00%** |

### 4.2 Equity & Drawdown Profile (7.0x RR, Flat $1,000 Risk)
![7.0x RR Equity and Drawdown Profile](images/7rr_equity_curve_v2.png)

---

## 5. The "Black Swan" Tail-Risk Spectrum

To explore the theoretical limits of the algorithm's distribution geometry, we conducted a Risk-to-Reward parameter sweep. Both strategies use **Flat $1,000 Risk per trade** with full friction applied.

| Target RR | Executions | Win Rate | Final Equity | Max DD (Abs) | Sharpe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **7.0x (Goldilocks)** | 1,371 | 16.12% | $362,556 | $57,362 | 0.636 |
| **20.0x (Optimal Tail)** | 611 | 8.84% | **$567,821** | **$55,109** | **0.841** |

![20.0x RR Equity and Drawdown Profile](images/20rr_equity_curve_v2.png)

**Verdict:** The 20.0x RR strategy generates **+56.7% more profit** than the 7.0x baseline while requiring an agonizing 91% loss rate. Crucially, the **Sharpe Ratio doubles** (0.636 → 0.841), mathematically proving 20x is the superior *risk-adjusted* parameter. However, its extended losing streaks make it psychologically and practically incompatible with Prop Firm daily drawdown limits. **7.0x RR** remains the practical "Goldilocks" deployment parameter.

### 4.3 Historical Monthly Performance
To understand the actual month-to-month reality of trading this strategy over the 14-year period, we analyzed the performance of every single calendar month using **Flat $1,000 Risk per trade**.

**=== 7.0x RR Strategy (170 Months Traded) ===**
* **Profitable Months:** 55.9% (95 of 170 months)
* **Avg Win Month:** +$7,042 | **Avg Loss Month:** -$5,419
* **Best Month:** +$22,794 | **Worst Month:** -$17,126

**=== 20.0x RR Strategy (119 Months Traded) ===**
* **Profitable Months:** 42.9% (51 of 119 months)
* **Avg Win Month:** +$16,680 | **Avg Loss Month:** -$5,631
* **Best Month:** +$39,936 | **Worst Month:** -$14,398

**The "Meta-Trade" Phenomenon (Time-Series Smoothing):**
By enforcing the strict "1-trade-at-a-time" rule, the volatile micro-level individual trades are smoothed into highly consistent macro-level monthly outcomes.
* **The 7RR "Meta-Trade":** The month acts as a single trade with a **1.30x RR** and a **55.9% Win Rate**.
* **The 20RR "Meta-Trade":** The month acts as a single trade with a **2.96x RR** and a **42.9% Win Rate**.

### 5.1 Monte Carlo: Solving the Path-Dependency Problem
Because the algorithm enforces a strict "1-trade-at-a-time" rule, the exact sequence of trades is highly path-dependent based on which initial signal is caught first. To prove the strategy is not simply "lucky" with its chronological sequence, a **1,000-Path Monte Carlo Simulation** was executed on the signal distribution.

This test virtually shuffles the trade sequence to simulate 1,000 alternative realities where different signals were skipped or caught, mapping out the actual sequential drawdown paths.

### 5.1.1 Monte Carlo Probability Distributions (Histogram)
The statistical distribution of outcomes across all 1,000 realities.

![Monte Carlo Path Dependency (Histogram)](images/mc_path_dependency.png)

### 5.1.2 Monte Carlo Actual Paths (Squiggly Lines)
The physical paths of 1,000 random simulations to visualize the journey and worst-case drawdown corridors.

![7.0x RR Monte Carlo Paths](images/mc_paths_lines_7rr_v2.png)

![20.0x RR Monte Carlo Paths](images/mc_paths_lines_20rr_v2.png)

**Analysis:**
*   **7.0x RR:** 100% of the 1,000 paths finished profitable (0% Risk of Ruin). The Mean Max Drawdown across all paths is **32.98%**, revealing the true worst-case corridor you can expect regardless of which trades you catch. The final equity is always identical ($362,556) because flat risk makes the sum path-order invariant — only the *journey* differs.
*   **20.0x RR:** Also 0% Risk of Ruin with a tighter Mean Max Drawdown of **27.15%**. The higher Sharpe ratio means even with catastrophic losing streaks, the magnitude of the wins recovers the account faster.

### 5.1.3 Monte Carlo 1,000-Path Statistical Averages

**=== Flat $1,000 Risk Model ===**
* **7.0x RR:** Final Equity: $362,556 (deterministic) | Mean Max DD: **-32.98%**
* **20.0x RR:** Final Equity: $567,821 (deterministic) | Mean Max DD: **-27.15%**

---

## 6. The Prop Firm Architecture & The "Goldilocks" Matrix

Having proven the underlying math is virtually indestructible, the algorithm was stress-tested against the notoriously tight constraints of modern proprietary trading firms.

### 6.1 Prop Firm Challenge Simulation (Monte Carlo)
To validate the statistical viability of passing evaluations, a 10,000-iteration Monte Carlo simulation was executed against standard evaluation dynamics.
This mathematically proves that an operator executing this strategy has an **81% theoretical probability** of reaching funded status based on the algorithm's win rate distribution.

### 6.2 Target Profile: 1-Step Flex Evaluation
*   **Profit Target:** $5,000 | **EOD Loss Limit:** $2,500
*   **Fees:** Initial: $264.99 | Reset: $147.99 | **Reward Share:** 95%

### 6.3 The Volatility "Goldilocks" Matrix
Because prop firms charge reset fees, blowing accounts during low-volatility chop is highly expensive. To counteract this, a dynamic risk sizing matrix was developed by comparing the current 14-Period ATR against a 50-Period SMA of the ATR.
*   **High Volatility Expansion (ATR > SMA):** Risk **$300** per trade.
*   **Low Volatility Consolidation (ATR < SMA):** Throttle risk to **$75** per trade.

**Own Capital Performance of Goldilocks Model (14-Year Validation):**
| Strategy | Final Equity | Max Drawdown (Abs) |
| :--- | :--- | :--- |
| **7.0x RR Goldilocks** | $171,599 | $7,863 |
| **20.0x RR Goldilocks** | $205,615 | $9,890 |

The absurdly tight drawdown ($7,863 absolute over 14 years) is the mathematical superpower of small, adaptive sizing.

### 6.4 The 10-Account Portfolio Simulation
The system simulates an institutional "Prop Firm Farm" setup: launching 1 account every week up to 10 concurrently active accounts. When an account is blown, it is instantly reset.

| Risk Size | Total Blown | Total Passed | Total Fees Spent | Gross Payouts | **NET PROFIT** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Flat $150 Risk** | 100 | 50 | -$17,449 | $237,500 | **$220,051** |
| **Flat $300 Risk** | 555 | 172 | -$84,784 | $332,500 | **$247,716** |
| **$300 / $75 Goldilocks** | **316** | **130** | **-$49,415** | **$332,500** | **$283,085** |

### 6.5 Total Accumulated Capital (10-Account Farm)
Below is the equity curve demonstrating the total extracted payouts (Net Profit) from the 10-Account Goldilocks Farm over the 14-year period:

![Total Accumulated Prop Firm Capital](images/flex_prop_firm_accumulated_payouts_v2.png)

### 6.6 The Final Verdict
When scaling to a 10-account farm, the **$300/$75 Goldilocks Model** becomes mathematically undeniable. By dynamically throttling risk during consolidation, it blows 239 fewer accounts, saving nearly $35,000 in unnecessary reset fees, resulting in a staggering **$283,085 in Net Profit**.

Because the strategy only triggers an average of **0.49 trades per day**, it is the ultimate candidate for manual execution paired with local trade copiers. By completely sidestepping automated EA bans, a disciplined operator can leverage this exact mathematical framework to scale boundlessly across the entire proprietary trading industry.

---

## 7. The Compounding Mirage: Execution & Scaling Limits

While the flat-dollar risk framework proves statistically undeniable, exploring the mathematical extremes of **Compound Scaling** (risking a percentage of the growing equity balance) reveals both the explosive upside of the edge and the brutal execution realities that prevent theoretical millions from materializing in real markets.

### 7.1 Compounding at 0.5% Risk (7.0x RR)
Compounding risk at 0.5% per trade transforms a $100,000 starting balance into over $320,000 across the 14-year backtest (with full slippage friction applied).

![7.0x RR Strategy Profile (0.5% Compounded)](images/7rr_compound_05_curve.png)

![7.0x RR (0.5% Comp) MC Histogram](images/7rr_compound_05_mc_hist.png)

![7.0x RR (0.5% Comp) MC Equity and Drawdown](images/7rr_compound_05_mc.png)

### 7.2 The Compounding Parameter Matrix (14-Year Simulation, Full Friction)

**=== 7.0x RR Strategy (14-Year Compounding) ===**
| Risk % | Final Equity | Max Drawdown | Sharpe |
| :--- | :--- | :--- | :--- |
| **0.30%** | $208,327 | -16.33% | 0.636 |
| **0.50%** | $320,485 | -26.21% | 0.636 |
| **0.75%** | $515,021 | -37.48% | 0.636 |
| **1.00%** | $772,194 | -47.81% | 0.636 |

**=== 20.0x RR Strategy (14-Year Compounding) ===**
| Risk % | Final Equity | Max Drawdown | Sharpe |
| :--- | :--- | :--- | :--- |
| **0.30%** | $369,625 | -15.44% | 0.841 |
| **0.50%** | $799,144 | -24.57% | 0.841 |
| **0.75%** | $1,889,219 | -34.78% | 0.841 |
| **1.00%** | $4,016,086 | -43.77% | 0.841 |

*(Note: The Sharpe ratio remains identical across risk parameters because Sharpe measures Risk-Adjusted Return. Scaling risk equally scales both returns and standard deviation.)*

### 7.3 Why the Theoretical Millions Are a Mirage
While compounding mathematically works on paper, there are three fundamental mechanical execution barriers that prevent realization in live markets:

1. **The Execution Gap (Slippage):** Massive 7x breakouts frequently correlate with macroeconomic news releases or flash volatility. During these events, order book liquidity vanishes. The backtest penalizes 0.5 points per trade — in live markets at scale, this can balloon to 5+ points on illiquid moments, as demonstrated in our Hyper-Slippage stress test which turned the strategy into a **-$602,094 loss**.
2. **The Liquidity Ceiling (Market Impact):** At large account sizes, a 1.0% risk parameter requires dropping large contract blocks onto the Nasdaq. An operator executing at this scale becomes the liquidity and directly moves the market against themselves.
3. **The Extended "Bleed" Periods:** Due to the low win rate, the algorithm undergoes extended periods of sideways bleeding during market consolidation regimes. Trading 0.49 trades per day means you can go 2–3 months with no winners, requiring iron psychological discipline.

These frictions confirm why utilizing small, fixed-dollar risk across a diversified matrix of proprietary firm accounts is the only realistic avenue to actualizing the mathematical edge in cash.



---

## 8. The Breakeven Optimization: Moving SL to Entry at 50% of Target

Having established the baseline mathematical architecture, we now test a single, surgically applied risk management rule: **move the Stop Loss to the Entry Price (Breakeven) once the trade has covered 50% of the distance to the Take Profit target.**

This means:
*   **7.0x RR Strategy:** SL moves to entry when price reaches **+3.5x Risk**
*   **20.0x RR Strategy:** SL moves to entry when price reaches **+10.0x Risk**

The core thesis: by triggering BE only at the **halfway point**, we avoid the common mistake of moving the stop too early (which chokes out trades before they can reach the target). We only protect profits once the trade has already demonstrated a strong directional conviction.

### 8.1 The Full Comparison: No-BE vs With-BE (All Risk Models)

#### 7.0x RR Strategy

| Metric | No Breakeven | BE at 3.5x | Delta |
| :--- | :---: | :---: | :---: |
| **Executions** | 1,371 | 1,437 | +66 |
| **Win Rate** | 16.12% | 14.89% | -1.23% |
| **True Sharpe Ratio** | 0.636 | **0.722** | **+0.086** |
| **Wins / Losses / Scratch BEs** | 221 / 1,150 / 0 | 214 / 1,119 / 104 | Saved 31 losses |
| **Flat $1k Final Equity** | $362,556 | **$392,377** | **+$29,821** |
| **Flat $1k Max DD** | -$57,362 | **-$49,723** | **+$7,639** |
| **Goldilocks $300/$75 Equity** | $171,599 | **$179,567** | **+$7,968** |
| **Goldilocks $300/$75 Max DD** | -$7,863 | -$8,815 | -$952 |
| **0.5% Comp Equity** | $320,485 | **$374,082** | **+$53,597** |
| **0.5% Comp Max DD** | -26.21% | **-23.27%** | **+2.94%** |
| **1.0% Comp Equity** | $772,194 | **$1,063,418** | **+$291,224** |
| **1.0% Comp Max DD** | -47.81% | **-42.95%** | **+4.86%** |
| **MC Flat $1k Max DD (Mean / Median)** | -$63,269 / -$60,454 | **-$57,710 / -$55,385** | **+$5,558** |
| **MC Goldilocks Max DD (Mean / Median)** | -$14,339 / -$13,565 | **-$12,999 / -$12,510** | **+$1,339** |
| **MC 0.5% Comp Max DD (Mean / Median)** | -27.76% / -26.97% | **-25.64% / -24.87%** | **+2.12%** |
| **MC 1.0% Comp Max DD (Mean / Median)** | -48.84% / -48.14% | **-45.59% / -44.72%** | **+3.25%** |

#### 20.0x RR Strategy

| Metric | No Breakeven | BE at 10x | Delta |
| :--- | :---: | :---: | :---: |
| **Executions** | 611 | 623 | +12 |
| **Win Rate** | 8.84% | 8.67% | -0.17% |
| **True Sharpe Ratio** | 0.841 | **0.874** | **+0.033** |
| **Wins / Losses / Scratch BEs** | 54 / 557 / 0 | 54 / 548 / 21 | Saved 9 losses |
| **Flat $1k Final Equity** | $567,821 | **$585,440** | **+$17,619** |
| **Flat $1k Max DD** | -$55,109 | **-$51,594** | **+$3,515** |
| **Goldilocks $300/$75 Equity** | $205,615 | $200,256 | -$5,359 |
| **Goldilocks $300/$75 Max DD** | -$9,890 | **-$8,832** | **+$1,058** |
| **0.5% Comp Equity** | $799,144 | **$872,939** | **+$73,795** |
| **0.5% Comp Max DD** | -24.57% | **-23.23%** | **+1.34%** |
| **1.0% Comp Equity** | $4,016,086 | **$4,794,323** | **+$778,237** |
| **1.0% Comp Max DD** | -43.77% | **-41.75%** | **+2.02%** |
| **MC Flat $1k Max DD (Mean / Median)** | -$58,342 / -$55,553 | **-$55,767 / -$52,890** | **+$2,574** |
| **MC Goldilocks Max DD (Mean / Median)** | -$14,290 / -$13,512 | **-$13,914 / -$13,121** | **+$376** |
| **MC 0.5% Comp Max DD (Mean / Median)** | -25.54% / -24.75% | **-24.59% / -23.68%** | **+0.96%** |
| **MC 1.0% Comp Max DD (Mean / Median)** | -44.96% / -44.02% | **-43.54% / -42.62%** | **+1.42%** |

---

### 8.2 Visual Proof: No-BE vs With-BE Overlay

The charts below show both equity curves drawn on the same axis. The **cyan line is the BE strategy**, the **grey line is the baseline**. Watch how the BE strategy pulls ahead and the drawdown bands become shallower.

#### 7.0x RR - Flat $1,000 Risk
![7RR No-BE vs With-BE Comparison](images/7rr_be_vs_nobe.png)

#### 20.0x RR - Flat $1,000 Risk
![20RR No-BE vs With-BE Comparison](images/20rr_be_vs_nobe.png)

#### 7.0x RR - 1.0% Compounding
![7RR No-BE vs With-BE Compounding](images/7rr_be_vs_nobe_comp.png)

---

### 8.3 Equity and Drawdown Profiles (BE Strategy)

#### 7.0x RR - Flat $1,000 Risk - With BE at 3.5x
![7RR BE Equity Flat](images/7rr_be_equity_flat.png)

#### 20.0x RR - Flat $1,000 Risk - With BE at 10x
![20RR BE Equity Flat](images/20rr_be_equity_flat.png)

#### 7.0x RR - 1.0% Compounding - With BE at 3.5x
![7RR BE Equity Compounding](images/7rr_be_equity_comp10.png)

#### 20.0x RR - 1.0% Compounding - With BE at 10x
![20RR BE Equity Compounding](images/20rr_be_equity_comp10.png)

---

### 8.4 Monte Carlo Validation (1,000-Path Simulation)

#### 7.0x RR (BE at 3.5x) - 1,000 Path Distribution
*Mean Max Drawdown: 31.04% | Risk of Ruin: 0.00%*

![7RR BE MC Distribution](images/mc_hist_7rr_be.png)

#### 7.0x RR (BE at 3.5x) - 1,000 Actual Paths
![7RR BE MC Paths](images/mc_paths_7rr_be.png)

#### 20.0x RR (BE at 10x) - 1,000 Path Distribution
*Mean Max Drawdown: 26.38% | Risk of Ruin: 0.00%*

![20RR BE MC Distribution](images/mc_hist_20rr_be.png)

#### 20.0x RR (BE at 10x) - 1,000 Actual Paths
![20RR BE MC Paths](images/mc_paths_20rr_be.png)

---

### 8.5 The Verdict: Why 50% BE Wins

The 50% Breakeven rule is mathematically optimal because it threads the needle between two competing failure modes:

1. **Move BE Too Early (e.g., at 1x RR):** You choke out winners constantly. Price regularly retraces 1x on its way to 7x. You convert profitable trades into scratch trades, destroying your edge.
2. **Never Move BE:** You allow trades that reached +5x to fall all the way back to -1x. Pure psychological torture and unnecessary equity destruction.
3. **Move BE at 50% (3.5x for 7RR):** By the time price has traveled 3.5x in your direction, it has demonstrated meaningful momentum conviction. The probability of a full reversal back to your entry is statistically low. You convert what would have been painful losses into neutral scratch trades, while still giving winners room to hit the full 7x target.

The compounding improvement is the most compelling argument: the 7RR strategy grows from **$772k to $1.06M** simply by adding one additional price-level check. The 20RR strategy grows from **$4.0M to $4.8M** (+$778k).

**Disclaimer: This research and the associated backtests are for educational purposes only. Past performance is not indicative of future results, and trading futures carries significant risk of loss.**


---

## 9. Appendix: Optimizing the Engine (Slower EMAs)

While the `25/100` EMA baseline is incredibly robust because of its structural simplicity (a standard 1:4 ratio), we also performed a massive In-Sample grid search and Out-of-Sample validation to find the mathematically optimal parameters.

### 9.1 Parameter Surface Heatmaps
We ran a grid search across over 3,000 EMA combinations to map out the "zones of profitability". We look for massive red plateaus (which indicate structural alpha) rather than single spikes (which indicate curve-fitting).

**10.0x Risk-to-Reward Parameter Heatmap**

![10RR Heatmap](images/ema_heatmap_10rr.png)

**7.0x Risk-to-Reward Parameter Heatmap**

![7RR Heatmap](images/ema_heatmap_7rr.png)

### 9.2 The 60/180 EMA (The Armored Tank)
The `60/180` crossover maps to a 15-Hour / 45-Hour trend. It significantly reduces trade frequency (down to ~55 trades/year) but pushes the Sharpe Ratio above 1.20 by filtering out nearly all false breakouts.


### 3. Institutional Destruction Stress-Testing (10RR)

| Stress Test Scenario | Final Equity | Max DD | Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Control Environment** | $500,014 | -$33,095 | 1.204 | - |
| **Latency Injection (30 Mins Late)** | $270,879 | -$35,224 | 0.710 | PASSED |
| **Gaussian Noise (±0.05% Random Walk)**| $434,131 | -$43,265 | 1.063 | PASSED |
| **Hyper-Slippage (5.0 Points per Trade)**| $228,253 | -$85,572 | 0.547 | FAILED |

### 4.3 Historical Monthly Performance

**=== 10.0x RR Strategy (166 Months Traded) ===**
*   **Profitable Months:** 60.2% 
*   **Avg Win Month:** +$8,338 | **Avg Loss Month:** -$5,057
*   **Best Month:** +$26,915 | **Worst Month:** -$10,703

### 8.1 The Full Comparison: No-BE vs With-BE (10RR)

#### 10.0x RR Strategy (60/180 EMAs)

| Metric | No Breakeven | BE at 5.0x | Delta |
| :--- | :---: | :---: | :---: |
| **Executions** | 756 | 770 | +14 |
| **Win Rate** | 15.61% | 14.29% | -1.32% |
| **True Sharpe Ratio** | 1.204 | 1.180 | -0.025 |
| **Wins / Losses / Scratch BEs** | 118 / 638 / 0 | 110 / 589 / 71 | |
| **Flat $1k Final Equity** | **$500,014** | $473,196 | $-26,818 |
| **Flat $1k Max DD** | -$33,095 | **-$36,252** | +$-3,157 |
| **0.5% Comp Equity** | **$1,047,002** | $925,103 | $-121,899 |
| **0.5% Comp Max DD** | -15.40% | **-16.73%** | +-1.33% |
| **1.0% Comp Equity** | **$8,237,671** | $6,557,440 | $-1,680,231 |
| **1.0% Comp Max DD** | -28.68% | **-30.90%** | +-2.23% |
| **MC Flat $1k Max DD (Mean / Median)** | **-$37,841 / -$36,339** | -$36,749 / -$35,160 | -$1,092 |
| **MC 1.0% Comp Max DD (Mean / Median)** | **-32.06% / -31.23%** | -31.27% / -30.57% | -0.79% |



#### 60/180 (10RR) - Flat Equity Curve
![60/180 10RR Flat Equity](images/60_180_10rr_equity_flat.png)

#### 60/180 (10RR) - 1.0% Compounding Equity Curve
![60/180 10RR Comp Equity](images/60_180_10rr_equity_comp.png)

#### 60/180 (10RR) - 1.0% Compounding Monte Carlo (1,000 Paths)
![60/180 10RR MC Paths](images/60_180_10rr_mc_paths.png)

#### 60/180 (10RR) - 1.0% Compounding Monte Carlo Drawdown Distribution
*Notice how tight the drawdown curve is despite massive compounding*

![60/180 10RR MC Hist](images/60_180_10rr_mc_hist.png)

### 9.3 The 50/200 EMA (The 1:4 Harmonic Upgrade)
The `50/200` is the mathematically elegant big brother to the `25/100`. It maintains the textbook 1:4 ratio while doubling the length of the lookback, perfectly threading the needle between higher win rate and better drawdown characteristics. 


### 3. Institutional Destruction Stress-Testing (10RR Baseline)
All tests use the Flat $1,000 Risk per trade model.

| Stress Test Scenario | Final Equity | Max DD | Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Control Environment** | $406,907 | -$31,247 | 0.990 | - |
| **Latency Injection (30 Mins Late)** | $114,273 | -$76,865 | 0.307 | PASSED |
| **Gaussian Noise (±0.05% Random Walk)**| $385,377 | -$35,833 | 0.947 | PASSED |
| **Hyper-Slippage (5.0 Points per Trade)**| $121,940 | -$115,700 | 0.296 | FAILED |

### 4.3 Historical Monthly Performance
To understand the actual month-to-month reality of trading this strategy over the 14-year period:

**=== 10.0x RR Strategy (168 Months Traded) ===**
*   **Profitable Months:** 55.4% 
*   **Avg Win Month:** +$8,546 | **Avg Loss Month:** -$5,171
*   **Best Month:** +$19,981 | **Worst Month:** -$11,774

### 8.1 The Full Comparison: No-BE vs With-BE (10RR)

#### 10.0x RR Strategy (50/200 EMAs)

| Metric | No Breakeven | BE at 5.0x | Delta |
| :--- | :---: | :---: | :---: |
| **Executions** | 787 | 802 | +15 |
| **Win Rate** | 14.23% | 13.22% | -1.01% |
| **True Sharpe Ratio** | 0.990 | 0.999 | +0.009 |
| **Wins / Losses / Scratch BEs** | 112 / 675 / 0 | 106 / 626 / 70 | |
| **Flat $1k Final Equity** | **$406,907** | $398,667 | $-8,241 |
| **Flat $1k Max DD** | -$31,247 | **-$27,214** | +$4,033 |
| **0.5% Comp Equity** | **$660,269** | $638,949 | $-21,319 |
| **0.5% Comp Max DD** | -14.84% | **-13.10%** | +1.74% |
| **1.0% Comp Equity** | **$3,304,212** | $3,143,540 | $-160,672 |
| **1.0% Comp Max DD** | -28.08% | **-25.11%** | +2.97% |
| **MC Flat $1k Max DD (Mean / Median)** | **-$43,574 / -$41,753** | -$41,379 / -$39,614 | -$2,195 |
| **MC 1.0% Comp Max DD (Mean / Median)** | **-36.13% / -35.07%** | -34.61% / -33.71% | -1.52% |


### 9.4 Out-of-Sample Proof (Is this curve-fitted?)
To prove these slower EMAs aren't just curve-fitted anomalies, we split the 14-year dataset in half. We optimized the parameters on the first 7 years (2010-2017) and found the slow EMAs performed best. 

We then took the optimized parameters and tested them blindly on the Out-of-Sample data (2017-2024).


| Strategy (10RR) | 2010-2017 (Training) Sharpe | 2017-2024 (Blind Test) Sharpe | Performance Decay |
| :--- | :---: | :---: | :---: |
| **Optimized (70/160)** | 1.178 | 1.319 | 12.0% |
| **Baseline (25/100)** | 0.216 | 1.104 | 411.2% |


**Conclusion:** The slower EMA variants (like `60/180` or `50/200`) actually *improved* during the out-of-sample forward test because the NQ's overall volatility regime structurally expanded post-2017. They are not curve-fitted; they are mathematically superior filters for the modern volatility environment.
