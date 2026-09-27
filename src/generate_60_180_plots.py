import numpy as np
import pandas as pd
import glob
import os
import matplotlib.pyplot as plt
from numba import njit
import seaborn as sns

plt.style.use('dark_background')

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

op, hi, lo, cl = df15['open'].values, df15['high'].values, df15['low'].values, df15['close'].values

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

trr = run_engine_fast(op, hi, lo, cl, f_ema, s_ema, atr, 10.0)
trr = np.array(trr)

# 1. Flat Equity Curve
eq = np.zeros(len(trr) + 1); eq[0] = 100000
for i in range(len(trr)):
    eq[i+1] = eq[i] + trr[i] * 1000.0

plt.figure(figsize=(10, 5))
plt.plot(eq, color='#00ffcc', linewidth=2)
plt.title('60/180 EMA (10RR Baseline) - Flat $1,000 Risk Equity Curve')
plt.ylabel('Account Balance ($)')
plt.xlabel('Trades (2010 - 2024)')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('images/60_180_10rr_equity_flat.png', facecolor='#111111')
plt.close()

# 2. Compounded Equity Curve (1.0%)
c10 = np.zeros(len(trr) + 1); c10[0] = 100000
for i in range(len(trr)):
    c10[i+1] = c10[i] * (1 + trr[i] * 0.01)

plt.figure(figsize=(10, 5))
plt.plot(c10, color='#ff00ff', linewidth=2)
plt.title('60/180 EMA (10RR Baseline) - 1.0% Compounding Equity Curve')
plt.ylabel('Account Balance ($)')
plt.xlabel('Trades (2010 - 2024)')
plt.yscale('log')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('images/60_180_10rr_equity_comp.png', facecolor='#111111')
plt.close()

# 3. Monte Carlo Paths
n_paths = 1000
mc_c10_paths = []
mc_max_dds = []

for seed in range(n_paths):
    rng = np.random.default_rng(seed)
    sh = rng.permutation(trr)
    c10_path = np.zeros(len(trr)+1); c10_path[0]=100000
    for i, r in enumerate(sh):
        c10_path[i+1] = c10_path[i] * (1 + r*0.01)
    
    pk = np.maximum.accumulate(c10_path)
    dd = np.max((pk - c10_path)/pk*100)
    mc_max_dds.append(dd)
    mc_c10_paths.append(c10_path)

plt.figure(figsize=(10, 6))
for i in range(200):
    plt.plot(mc_c10_paths[i], color='#00ffcc', alpha=0.05)
plt.plot(c10, color='#ff00ff', linewidth=2, label='Historical Path')
plt.title('60/180 EMA (10RR Baseline) - 1.0% Compounding MC (1,000 Paths)')
plt.ylabel('Account Balance ($)')
plt.xlabel('Trades (2010 - 2024)')
plt.yscale('log')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('images/60_180_10rr_mc_paths.png', facecolor='#111111')
plt.close()

# 4. Monte Carlo Drawdown Hist
plt.figure(figsize=(10, 5))
sns.histplot(mc_max_dds, bins=50, color='#ff3333', kde=True)
plt.title('60/180 EMA (10RR Baseline) - 1.0% Compounding MC Max Drawdown Distribution')
plt.xlabel('Maximum Drawdown (%)')
plt.ylabel('Frequency')
plt.axvline(np.mean(mc_max_dds), color='white', linestyle='dashed', linewidth=2, label=f'Mean DD: {np.mean(mc_max_dds):.1f}%')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('images/60_180_10rr_mc_hist.png', facecolor='#111111')
plt.close()

print("Graphs generated successfully.")
