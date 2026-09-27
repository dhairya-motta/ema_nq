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

# Split the dataset 50/50 exactly down the middle
midpoint = len(df15) // 2
df_in_sample = df15.iloc[:midpoint]
df_out_sample = df15.iloc[midpoint:]

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

def run_grid(df_target, name):
    op = df_target['open'].values
    hi = df_target['high'].values
    lo = df_target['low'].values
    cl = df_target['close'].values
    
    atr = compute_atr(hi, lo, cl, 14)
    fast_emas_to_test = list(range(5, 105, 5))
    slow_emas_to_test = list(range(10, 205, 5))
    
    periods = sorted(list(set(fast_emas_to_test + slow_emas_to_test)))
    computed_emas = compute_emas(cl, periods)
    ema_dict = {p: e for p, e in zip(periods, computed_emas)}
    
    rr = 10.0
    results = []
    years = 7.08
    
    for f_p in fast_emas_to_test:
        for s_p in slow_emas_to_test:
            if f_p >= s_p: continue
            
            f_ema = ema_dict[f_p]
            s_ema = ema_dict[s_p]
            
            trades_rr_list = run_engine_fast(op, hi, lo, cl, f_ema, s_ema, atr, rr)
            trades_rr = np.array(trades_rr_list)
            
            n_trades = len(trades_rr)
            if n_trades == 0: continue
            
            tpy = n_trades / years
            std = np.std(trades_rr * 1000.0)
            sharpe = (np.mean(trades_rr * 1000.0) / std) * np.sqrt(tpy) if std > 0 else 0
            
            results.append({
                'Fast': f_p,
                'Slow': s_p,
                'Sharpe': sharpe
            })
            
    res_df = pd.DataFrame(results)
    return res_df

print("Running In-Sample Optimization (First 7 Years, 2010-2017)...")
is_results = run_grid(df_in_sample, "In-Sample")
is_results = is_results.sort_values('Sharpe', ascending=False)
best_in_sample = is_results.iloc[0]
best_f = int(best_in_sample['Fast'])
best_s = int(best_in_sample['Slow'])
best_is_sharpe = best_in_sample['Sharpe']

print(f"\nThe mathematically 'best' parameter during 2010-2017 was {best_f}/{best_s} with an IS Sharpe of {best_is_sharpe:.3f}")

print("\nRunning Out-of-Sample Validation (Last 7 Years, 2017-2024)...")
oos_results = run_grid(df_out_sample, "Out-of-Sample")

# Find how the IS winner performed in the OOS data
oos_performance = oos_results[(oos_results['Fast'] == best_f) & (oos_results['Slow'] == best_s)].iloc[0]
oos_sharpe = oos_performance['Sharpe']

print(f"When blindly trading the '{best_f}/{best_s}' combination in 2017-2024, the OOS Sharpe dropped to {oos_sharpe:.3f}")

# Compare to our baseline 25/100
baseline_is = is_results[(is_results['Fast'] == 25) & (is_results['Slow'] == 100)].iloc[0]['Sharpe']
baseline_oos = oos_results[(oos_results['Fast'] == 25) & (oos_results['Slow'] == 100)].iloc[0]['Sharpe']

print("\n=== THE MOMENT OF TRUTH: IN-SAMPLE VS OUT-OF-SAMPLE DECAY ===")
out = f"""
| Strategy (10RR) | 2010-2017 (Training) Sharpe | 2017-2024 (Blind Test) Sharpe | Performance Decay |
| :--- | :---: | :---: | :---: |
| **Optimized ({best_f}/{best_s})** | {best_is_sharpe:.3f} | {oos_sharpe:.3f} | {(oos_sharpe - best_is_sharpe) / best_is_sharpe * 100:.1f}% |
| **Baseline (25/100)** | {baseline_is:.3f} | {baseline_oos:.3f} | {(baseline_oos - baseline_is) / baseline_is * 100:.1f}% |
"""

with open('oos_results.txt', 'w', encoding='utf-8') as f:
    f.write(out)
print(out)
