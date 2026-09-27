# The Goldilocks 7RR Manual Execution Playbook

This document is your physical, rigid set of rules for trading the strategy in real-time. Do not deviate from these rules. The mathematics rely on perfectly consistent execution.

---

## 1. The Trading Environment
* **Asset:** NQ (Nasdaq 100 Futures)
* **Timeframe:** 15-Minute Chart (15m)
* **Trading Tooling:** 
  * TradingView for charting and signals.
  * Replikanto, Quantower, or Trade Copier for executing across 10 Prop Firm accounts simultaneously.
* **Prop Firm Setup:** Ten $100k Evaluation/Funded accounts.

## 2. The Indicators (TradingView Setup)
Apply the custom Pine Script below to your chart. It will automatically plot the 25 EMA, 100 EMA, and precisely draw your Entry, Stop Loss, and 7x Take Profit lines the exact second a valid signal is confirmed.

```pine
// This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © footballermessi53

//@version=6
indicator("Goldilocks 7RR Execution Assistant", overlay=true)

// --- 1. EMA Calculations ---
ema25 = ta.ema(close, 25)
ema100 = ta.ema(close, 100)

plot(ema25, color=color.aqua, title="25 EMA", linewidth=2)
plot(ema100, color=color.fuchsia, title="100 EMA", linewidth=2)

// --- 2. ATR Calculation ---
my_atr = ta.atr(14)
trade_risk = math.max(2.0 * my_atr, 5.0) // 2x ATR, minimum 5 pts

// --- 3. Signal Logic ---
longCondition = ta.crossover(ema25, ema100)

// --- 4. Trade Management Variables ---
var float entryPrice = na
var float slPrice = na
var float tpPrice = na
var bool inTrade = false

// When a crossover happens and we are NOT already in a trade
if (longCondition and not inTrade)
    inTrade := true
    entryPrice := close 
    slPrice := entryPrice - trade_risk
    tpPrice := entryPrice + (trade_risk * 7.0) 

// Clear lines if SL or TP hit
if inTrade
    if low <= slPrice or high >= tpPrice
        inTrade := false
        entryPrice := na
        slPrice := na
        tpPrice := na

// --- 5. Visual Plotting ---
plotshape(series=longCondition and not inTrade[1], title="Long Signal", style=shape.triangleup, location=location.belowbar, color=color.green, size=size.normal)

plot(inTrade ? slPrice : na, color=color.red, style=plot.style_linebr, linewidth=2, title="Stop Loss (2x ATR)")
plot(inTrade ? entryPrice : na, color=color.white, style=plot.style_linebr, linewidth=1, title="Entry Price")
plot(inTrade ? tpPrice : na, color=color.lime, style=plot.style_linebr, linewidth=2, title="Take Profit (7RR)")
```

---

## 3. The Execution Rules (Step-by-Step)

### Step 1: Wait for the Candle to Close
You **never** anticipate a crossover. EMAs will fluctuate while the candle is forming. Wait until the 15-minute clock ticks over to the next candle (e.g., exactly at 10:15:00 AM). When the candle officially closes, the EMA values are permanently locked. 

### Step 2: Identify the Signal
If the 25 EMA has closed **above** the 100 EMA, and a green triangle appears from your Pine Script, you have a valid signal.

### Step 3: Check the "1-Trade-at-a-Time" Rule
Are you already in an active trade?
* **Yes:** Do not take the trade. Ignore the signal.
* **No:** Proceed to execute.

### Step 4: Sizing (The Goldilocks Throttling)
Look at the 14-period ATR value and compare it to the 50-period SMA of the ATR.
* If **ATR > ATR 50-SMA:** (Market is volatile/trending). Risk **$300** per account.
* If **ATR < ATR 50-SMA:** (Market is consolidating). Risk **$75** per account.

*Calculate Contracts:* `Risk Amount / (2x ATR points * $2 per point for Micros)` = Number of Micro Contracts (MNQ). 
*(e.g., If risking $300 and Stop Loss is 25 points. 25 pts * $2 = $50 risk per micro. $300 / $50 = 6 MNQ contracts).*

### Step 5: Execute the Order
Immediately enter at Market Price at the open of the new candle. 
Place your Stop Loss exactly on the **Red Line** plotted by your indicator.
Place your Limit Take Profit exactly on the **Green Line** plotted by your indicator.

### Step 6: Walk Away
The math dictates that you do absolutely nothing else. 
* Do not move the Stop Loss to breakeven.
* Do not take partial profits.
* Do not manually close the trade if you get scared.

The trade will either hit the Red Line (Loss) or the Green Line (Massive Win). The trade is over when the lines disappear from your chart.
