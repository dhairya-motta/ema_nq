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
df15['date_int'] = df15.index.strftime('%Y%m').astype(int)

op, hi, lo, cl = df15['open'].values, df15['high'].values, df15['low'].values, df15['close'].values
dates = df15['date_int'].values

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

emas = compute_emas(cl, [60, 180])
f_ema, s_ema = emas[0], emas[1]
atr = compute_atr(hi, lo, cl, 14)

@njit
def run_engine_detailed(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, rr_target, has_be, friction=0.5, latency_shift=0, noise_std=0.0):
    in_trade = False
    trade_risk = 0.0
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    be_p = 0.0
    moved_be = False
    
    trades_rr = []
    trade_months = []
    
    for i in range(1, len(open_p) - 1 - latency_shift):
        if not in_trade:
            crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
            if crossover_long:
                trade_risk = 2.0 * atr[i]
                if trade_risk < 5.0: trade_risk = 5.0
                
                entry_idx = i + 1 + latency_shift
                if entry_idx >= len(open_p): break
                
                entry_p = open_p[entry_idx]
                if noise_std > 0:
                    entry_p += entry_p * np.random.normal(0, noise_std)
                    
                sl_p = entry_p - trade_risk
                tp_p = entry_p + trade_risk * rr_target
                be_p = entry_p + trade_risk * (rr_target / 2.0)
                moved_be = False
                in_trade = True
                
                if open_p[entry_idx] < sl_p:
                    exit_px = open_p[entry_idx]
                    pnl_pts = exit_px - entry_p - friction
                    trades_rr.append(pnl_pts / trade_risk)
                    trade_months.append(dates[entry_idx])
                    in_trade = False
                    continue
        
        if in_trade:
            curr_low = low_p[i+1]
            curr_high = high_p[i+1]
            
            if has_be and not moved_be and curr_high >= be_p:
                sl_p = entry_p + friction
                moved_be = True
                
            if curr_low <= sl_p:
                exit_px = sl_p
                if open_p[i+1] < sl_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                trades_rr.append(pnl_pts / trade_risk)
                trade_months.append(dates[i+1])
                in_trade = False
                
            elif curr_high >= tp_p:
                exit_px = tp_p
                if open_p[i+1] > tp_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                trades_rr.append(pnl_pts / trade_risk)
                trade_months.append(dates[i+1])
                in_trade = False
                
    return trades_rr, trade_months

def calc_stats(trades_rr, trade_months, years=14.167):
    trr = np.array(trades_rr)
    tm = np.array(trade_months)
    
    n_trades = len(trr)
    wins = np.sum(trr > 0)
    losses = np.sum(trr < -0.1)
    scratch = n_trades - wins - losses
    win_rate = wins / n_trades * 100 if n_trades > 0 else 0
    
    eq = np.zeros(n_trades + 1); eq[0] = 100000
    c05 = np.zeros(n_trades + 1); c05[0] = 100000
    c10 = np.zeros(n_trades + 1); c10[0] = 100000
    
    for i in range(n_trades):
        eq[i+1] = eq[i] + trr[i] * 1000.0
        c05[i+1] = c05[i] * (1 + trr[i]*0.005)
        c10[i+1] = c10[i] * (1 + trr[i]*0.01)
        
    flat_eq = eq[-1] - 100000.0
    flat_dd = np.max(np.maximum.accumulate(eq) - eq)
    
    c05_eq = c05[-1]
    pk = np.maximum.accumulate(c05)
    c05_dd = np.max((pk - c05)/pk*100) if n_trades > 0 else 0
    
    c10_eq = c10[-1]
    pk = np.maximum.accumulate(c10)
    c10_dd = np.max((pk - c10)/pk*100) if n_trades > 0 else 0
    
    tpy = n_trades / years
    std = np.std(trr * 1000.0)
    sharpe = (np.mean(trr * 1000.0) / std) * np.sqrt(tpy) if std > 0 else 0
    
    unique_months = np.unique(tm)
    monthly_pnls = []
    for m in unique_months:
        idx = np.where(tm == m)[0]
        monthly_pnls.append(np.sum(trr[idx] * 1000.0))
    monthly_pnls = np.array(monthly_pnls)
    prof_months = np.sum(monthly_pnls > 0)
    win_m = monthly_pnls[monthly_pnls > 0]
    los_m = monthly_pnls[monthly_pnls < 0]
    
    return {
        'Executions': n_trades,
        'Win Rate': win_rate,
        'Wins/Loss/BE': f'{wins} / {losses} / {scratch}',
        'Flat Eq': flat_eq,
        'Flat DD': flat_dd,
        'Sharpe': sharpe,
        '0.5% Eq': c05_eq,
        '0.5% DD': c05_dd,
        '1.0% Eq': c10_eq,
        '1.0% DD': c10_dd,
        'Months Traded': len(unique_months),
        'Prof Months %': prof_months / len(unique_months) * 100 if len(unique_months)>0 else 0,
        'Avg Win Month': np.mean(win_m) if len(win_m)>0 else 0,
        'Avg Loss Month': np.mean(los_m) if len(los_m)>0 else 0,
        'Best Month': np.max(monthly_pnls) if len(monthly_pnls)>0 else 0,
        'Worst Month': np.min(monthly_pnls) if len(monthly_pnls)>0 else 0
    }

def mc_stats(trades_rr, n_paths=1000):
    trr = np.array(trades_rr)
    n = len(trr)
    flat_dds = []; c05_dds = []; c10_dds = []
    
    for seed in range(n_paths):
        rng = np.random.default_rng(seed)
        sh = rng.permutation(trr)
        
        f = np.zeros(n+1); f[0]=100000
        c05 = np.zeros(n+1); c05[0]=100000
        c10 = np.zeros(n+1); c10[0]=100000
        
        for i, r in enumerate(sh):
            f[i+1] = f[i] + r*1000
            c05[i+1] = c05[i]*(1+r*0.005)
            c10[i+1] = c10[i]*(1+r*0.01)
            
        flat_dds.append(np.max(np.maximum.accumulate(f) - f))
        pk = np.maximum.accumulate(c05)
        c05_dds.append(np.max((pk-c05)/pk*100))
        pk = np.maximum.accumulate(c10)
        c10_dds.append(np.max((pk-c10)/pk*100))
        
    return {
        'flat': (np.mean(flat_dds), np.median(flat_dds)),
        'c05': (np.mean(c05_dds), np.median(c05_dds)),
        'c10': (np.mean(c10_dds), np.median(c10_dds))
    }

r10, m10 = run_engine_detailed(op, hi, lo, cl, f_ema, s_ema, atr, 10.0, False)
r10b, m10b = run_engine_detailed(op, hi, lo, cl, f_ema, s_ema, atr, 10.0, True)

r10_lat, m10_lat = run_engine_detailed(op, hi, lo, cl, f_ema, s_ema, atr, 10.0, False, latency_shift=2)
r10_noise, m10_noi = run_engine_detailed(op, hi, lo, cl, f_ema, s_ema, atr, 10.0, False, noise_std=0.0005)
r10_slip, m10_slip = run_engine_detailed(op, hi, lo, cl, f_ema, s_ema, atr, 10.0, False, friction=5.0)

s10 = calc_stats(r10, m10)
s10b = calc_stats(r10b, m10b)
slat = calc_stats(r10_lat, m10_lat)
snoi = calc_stats(r10_noise, m10_noi)
sslip = calc_stats(r10_slip, m10_slip)

mc10 = mc_stats(r10)
mc10b = mc_stats(r10b)

out = f"""
### 3. Institutional Destruction Stress-Testing (10RR)

| Stress Test Scenario | Final Equity | Max DD | Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Control Environment** | ${s10['Flat Eq']:,.0f} | -${s10['Flat DD']:,.0f} | {s10['Sharpe']:.3f} | - |
| **Latency Injection (30 Mins Late)** | ${slat['Flat Eq']:,.0f} | -${slat['Flat DD']:,.0f} | {slat['Sharpe']:.3f} | PASSED |
| **Gaussian Noise (±0.05% Random Walk)**| ${snoi['Flat Eq']:,.0f} | -${snoi['Flat DD']:,.0f} | {snoi['Sharpe']:.3f} | PASSED |
| **Hyper-Slippage (5.0 Points per Trade)**| ${sslip['Flat Eq']:,.0f} | -${sslip['Flat DD']:,.0f} | {sslip['Sharpe']:.3f} | FAILED |

### 4.3 Historical Monthly Performance

**=== 10.0x RR Strategy ({s10['Months Traded']} Months Traded) ===**
*   **Profitable Months:** {s10['Prof Months %']:.1f}% 
*   **Avg Win Month:** +${s10['Avg Win Month']:,.0f} | **Avg Loss Month:** -${-s10['Avg Loss Month']:,.0f}
*   **Best Month:** +${s10['Best Month']:,.0f} | **Worst Month:** -${-s10['Worst Month']:,.0f}

### 8.1 The Full Comparison: No-BE vs With-BE (10RR)

#### 10.0x RR Strategy (60/180 EMAs)

| Metric | No Breakeven | BE at 5.0x | Delta |
| :--- | :---: | :---: | :---: |
| **Executions** | {s10['Executions']} | {s10b['Executions']} | +{s10b['Executions'] - s10['Executions']} |
| **Win Rate** | {s10['Win Rate']:.2f}% | {s10b['Win Rate']:.2f}% | {s10b['Win Rate'] - s10['Win Rate']:+.2f}% |
| **True Sharpe Ratio** | {s10['Sharpe']:.3f} | {s10b['Sharpe']:.3f} | {s10b['Sharpe'] - s10['Sharpe']:+.3f} |
| **Wins / Losses / Scratch BEs** | {s10['Wins/Loss/BE']} | {s10b['Wins/Loss/BE']} | |
| **Flat $1k Final Equity** | **${s10['Flat Eq']:,.0f}** | ${s10b['Flat Eq']:,.0f} | ${s10b['Flat Eq'] - s10['Flat Eq']:,.0f} |
| **Flat $1k Max DD** | -${s10['Flat DD']:,.0f} | **-${s10b['Flat DD']:,.0f}** | +${s10['Flat DD'] - s10b['Flat DD']:,.0f} |
| **0.5% Comp Equity** | **${s10['0.5% Eq']:,.0f}** | ${s10b['0.5% Eq']:,.0f} | ${s10b['0.5% Eq'] - s10['0.5% Eq']:,.0f} |
| **0.5% Comp Max DD** | -{s10['0.5% DD']:.2f}% | **-{s10b['0.5% DD']:.2f}%** | +{s10['0.5% DD'] - s10b['0.5% DD']:.2f}% |
| **1.0% Comp Equity** | **${s10['1.0% Eq']:,.0f}** | ${s10b['1.0% Eq']:,.0f} | ${s10b['1.0% Eq'] - s10['1.0% Eq']:,.0f} |
| **1.0% Comp Max DD** | -{s10['1.0% DD']:.2f}% | **-{s10b['1.0% DD']:.2f}%** | +{s10['1.0% DD'] - s10b['1.0% DD']:.2f}% |
| **MC Flat $1k Max DD (Mean / Median)** | **-${mc10['flat'][0]:,.0f} / -${mc10['flat'][1]:,.0f}** | -${mc10b['flat'][0]:,.0f} / -${mc10b['flat'][1]:,.0f} | -${mc10['flat'][0] - mc10b['flat'][0]:,.0f} |
| **MC 1.0% Comp Max DD (Mean / Median)** | **-{mc10['c10'][0]:.2f}% / -{mc10['c10'][1]:.2f}%** | -{mc10b['c10'][0]:.2f}% / -{mc10b['c10'][1]:.2f}% | -{mc10['c10'][0] - mc10b['c10'][0]:.2f}% |
"""
with open('results_10rr.txt', 'w', encoding='utf-8') as f:
    f.write(out)
print("Finished!")
