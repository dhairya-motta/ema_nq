import numpy as np
import pandas as pd
import glob
import os
import time
from numba import njit

d = 'C:/Users/kingcuber/.gemini/antigravity-ide/scratch/FX-1-Minute-Data/output/nsxusd'
dfs = []
for f in glob.glob(os.path.join(d, '*.csv')):
    try:
        _df = pd.read_csv(f, sep=';', header=None, names=['date','open','high','low','close','volume'])
        _df['datetime'] = pd.to_datetime(_df['date'], format='%Y%m%d %H%M%S')
        _df = _df.set_index('datetime'); dfs.append(_df)
    except: pass
df = pd.concat(dfs).sort_index()
df15 = df.resample('15min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

df15['year'] = df15.index.year

@njit
def compute_emas(close_p, periods):
    res = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = np.zeros_like(close_p)
        ema[0] = close_p[0]
        for i in range(1, len(close_p)):
            ema[i] = (close_p[i] - ema[i-1]) * alpha + ema[i-1]
        res.append(ema)
    return res

@njit
def compute_atr(high_p, low_p, close_p, period=14):
    atr = np.zeros_like(close_p)
    tr = np.zeros_like(close_p)
    tr[0] = high_p[0] - low_p[0]
    atr[0] = tr[0]
    for i in range(1, len(close_p)):
        hl = high_p[i] - low_p[i]
        hc = np.abs(high_p[i] - close_p[i-1])
        lc = np.abs(low_p[i] - close_p[i-1])
        tr[i] = max(hl, hc, lc)
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

@njit
def run_engine_fast(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, rr_target):
    friction = 0.5
    in_trade = False
    trade_risk = 0.0
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    
    trades_rr = []
    for i in range(1, len(open_p) - 1):
        if not in_trade:
            crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
            if crossover_long:
                trade_risk = 2.0 * atr[i]
                if trade_risk < 5.0: trade_risk = 5.0
                
                entry_p = open_p[i+1]
                sl_p = entry_p - trade_risk
                tp_p = entry_p + trade_risk * rr_target
                in_trade = True
        
        if in_trade:
            curr_low = low_p[i+1]
            curr_high = high_p[i+1]
            
            if curr_low <= sl_p:
                exit_px = sl_p
                if open_p[i+1] < sl_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                rr_earned = pnl_pts / trade_risk
                trades_rr.append(rr_earned)
                in_trade = False
                
            elif curr_high >= tp_p:
                exit_px = tp_p
                if open_p[i+1] > tp_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                rr_earned = pnl_pts / trade_risk
                trades_rr.append(rr_earned)
                in_trade = False
                
    return trades_rr

def test_epoch(df_target, f_p, s_p, name, years=2.0):
    op = df_target['open'].values
    hi = df_target['high'].values
    lo = df_target['low'].values
    cl = df_target['close'].values
    
    atr = compute_atr(hi, lo, cl, 14)
    emas = compute_emas(cl, [f_p, s_p])
    f_ema, s_ema = emas[0], emas[1]
    
    trades_rr_list = run_engine_fast(op, hi, lo, cl, f_ema, s_ema, atr, 10.0)
    trades_rr = np.array(trades_rr_list)
    
    n_trades = len(trades_rr)
    if n_trades == 0:
        return 0.0, 0, 0
    
    tpy = n_trades / years
    std = np.std(trades_rr * 1000.0)
    sharpe = (np.mean(trades_rr * 1000.0) / std) * np.sqrt(tpy) if std > 0 else 0
    
    win_rate = np.sum(trades_rr > 0) / n_trades * 100
    return sharpe, n_trades, win_rate

print("Running Rolling 2-Year Epoch Validation (Testing for Overfitting)...")
epochs = [
    (2010, 2011),
    (2012, 2013),
    (2014, 2015),
    (2016, 2017),
    (2018, 2019),
    (2020, 2021),
    (2022, 2024) # 3 years for the last chunk
]

results = []
for start_y, end_y in epochs:
    df_epoch = df15[(df15['year'] >= start_y) & (df15['year'] <= end_y)]
    duration = end_y - start_y + 1
    
    # 60/180
    sh_60, n_60, wr_60 = test_epoch(df_epoch, 60, 180, f"{start_y}-{end_y}", years=duration)
    # 25/100 (Baseline)
    sh_25, n_25, wr_25 = test_epoch(df_epoch, 25, 100, f"{start_y}-{end_y}", years=duration)
    
    results.append({
        'Epoch': f"{start_y}-{end_y}",
        '60/180 Sharpe': sh_60,
        '60/180 WR': wr_60,
        '60/180 Trades': n_60,
        '25/100 Sharpe': sh_25
    })

res_df = pd.DataFrame(results)

out = """
### === ROLLING 2-YEAR EPOCH VALIDATION (60/180 OVERFIT TEST) ===

If 60/180 is overfitted to a specific historical anomaly, it will break down in certain epochs.
If it is structurally robust, it should maintain profitability across multiple disjoint eras.

| Epoch | Market Regime | 60/180 Sharpe | 25/100 (Base) Sharpe | 60/180 WinRate | Trades |
| :--- | :--- | :---: | :---: | :---: | :---: |
"""

for _, row in res_df.iterrows():
    epoch = row['Epoch']
    s60 = row['60/180 Sharpe']
    s25 = row['25/100 Sharpe']
    wr = row['60/180 WR']
    tr = row['60/180 Trades']
    
    regime = "Standard"
    if epoch == "2010-2011": regime = "Post-GFC Grind"
    elif epoch == "2012-2013": regime = "Low Vol Bull"
    elif epoch == "2014-2015": regime = "Chop/Consolidation"
    elif epoch == "2016-2017": regime = "Melt-Up"
    elif epoch == "2018-2019": regime = "Vol Spike / V-Shape"
    elif epoch == "2020-2021": regime = "Covid Crash & QE Mania"
    elif epoch == "2022-2024": regime = "Bear Market & AI Boom"
    
    out += f"| **{epoch}** | {regime} | {s60:.3f} | {s25:.3f} | {wr:.1f}% | {tr} |\n"

out += f"""
**Verdict:**
60/180 Average Epoch Sharpe: {res_df['60/180 Sharpe'].mean():.3f}
25/100 Average Epoch Sharpe: {res_df['25/100 Sharpe'].mean():.3f}
Profitable Epochs (60/180): {sum(res_df['60/180 Sharpe'] > 0)} / {len(epochs)}
"""

with open('epoch_results.txt', 'w', encoding='utf-8') as f:
    f.write(out)
print(out)
