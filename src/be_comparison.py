"""
BE COMPARISON SCRIPT
Runs 7RR and 20RR with and without SL-to-BE at 50% of TP.
Outputs a clean before/after comparison table.
"""
import pandas as pd
import numpy as np
import glob
import os
import sys
sys.path.insert(0, "C:/Users/kingcuber/.gemini/antigravity-ide/scratch")

# Inline the engine here so we don't have to import the whole master script
def compute_emas(close, periods):
    emas = {}
    for period in periods:
        alpha = 2 / (period + 1)
        ema = np.zeros(len(close)); ema[0] = close[0]
        for i in range(1, len(close)):
            ema[i] = alpha * close[i] + (1 - alpha) * ema[i - 1]
        emas[period] = ema
    return emas

def compute_atr(high, low, close, period=14):
    tr = np.zeros(len(close)); tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    atr = np.zeros(len(close)); atr[0] = tr[0]
    for i in range(1, len(close)):
        atr[i] = (atr[i-1]*(period-1) + tr[i]) / period
    return atr

def compute_sma(data, period):
    sma = np.zeros(len(data)); sma[0] = data[0]
    for i in range(1, len(data)):
        sma[i] = np.mean(data[:i+1]) if i < period else np.mean(data[i-period+1:i+1])
    return sma

def run_engine(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma,
               rr_target, has_be=False):
    friction = 0.5
    be_mult = 0.5  # Trigger BE at 50% of TP distance
    trades_rr = []; gold_pnl = []
    in_trade = False; entry_p=sl_p=tp_p=be_px=risk_pts=gold_risk = 0.0
    be_hit = False
    n = len(close_p)
    for i in range(1, n-1):
        co = f_ema[i-1]<=s_ema[i-1] and f_ema[i]>s_ema[i]
        if not in_trade and co:
            eb = i+1
            if eb >= n-1: continue
            risk = max(2.0*atr[i], 5.0)
            gr = 300.0 if atr[i]>atr_sma[i] else 75.0
            entry_p = open_p[eb]
            sl_p = entry_p - risk
            tp_p = entry_p + risk*rr_target
            be_px = entry_p + risk*rr_target*be_mult
            in_trade=True; be_hit=False; risk_pts=risk; gold_risk=gr
        elif in_trade:
            cb = i+1
            if cb>=n: break
            lo=low_p[cb]; hi=high_p[cb]; go=open_p[cb]
            if has_be and not be_hit and hi>=be_px:
                be_hit=True; sl_p=entry_p
            closed=False; res=0.0
            if go<=sl_p:
                res=0.0 if be_hit else (go-entry_p)/risk_pts; closed=True
            elif lo<=sl_p:
                res=0.0 if be_hit else -1.0; closed=True
            elif hi>=tp_p:
                res=rr_target; closed=True
            if closed:
                fr=(friction*2.0)/risk_pts; frr=res-fr
                trades_rr.append(frr); gold_pnl.append(frr*gold_risk); in_trade=False
    return np.array(trades_rr), np.array(gold_pnl)

def stats(trades_rr, gold_pnl):
    n = len(trades_rr)
    wins = int(np.sum(trades_rr > 0))
    losses = int(np.sum(trades_rr < -0.1))
    bes = n - wins - losses
    wr = wins/n*100

    # Flat $1k
    flat = np.zeros(n+1); flat[0]=100000
    for i,r in enumerate(trades_rr): flat[i+1]=flat[i]+r*1000
    flat_dd = float(np.max(np.maximum.accumulate(flat)-flat))

    # Goldilocks
    gold = np.zeros(n+1); gold[0]=100000
    for i,p in enumerate(gold_pnl): gold[i+1]=gold[i]+p
    gold_dd = float(np.max(np.maximum.accumulate(gold)-gold))

    # 0.5% Comp
    c05 = np.zeros(n+1); c05[0]=100000
    for i,r in enumerate(trades_rr): c05[i+1]=c05[i]*(1+r*0.005)
    pk05=np.maximum.accumulate(c05); dd05=float(np.max((pk05-c05)/pk05*100))

    # 1.0% Comp
    c10 = np.zeros(n+1); c10[0]=100000
    for i,r in enumerate(trades_rr): c10[i+1]=c10[i]*(1+r*0.01)
    pk10=np.maximum.accumulate(c10); dd10=float(np.max((pk10-c10)/pk10*100))

    # MC Mean MaxDD
    mc_dds = []
    for seed in range(1000):
        rng=np.random.default_rng(seed); sh=rng.permutation(trades_rr)
        eq=np.zeros(n+1); eq[0]=100000
        for j,r in enumerate(sh): eq[j+1]=eq[j]+r*1000
        pk=np.maximum.accumulate(eq); mc_dds.append(float(np.max((pk-eq)/pk*100)))

    return {
        "n": n, "wins": wins, "losses": losses, "bes": bes, "wr": wr,
        "flat_eq": flat[-1], "flat_dd": flat_dd,
        "gold_eq": gold[-1], "gold_dd": gold_dd,
        "c05_eq": c05[-1], "c05_dd": dd05,
        "c10_eq": c10[-1], "c10_dd": dd10,
        "mc_dd": float(np.mean(mc_dds)),
    }

# Load data
print("Loading data...")
d = "C:/Users/kingcuber/.gemini/antigravity-ide/scratch/FX-1-Minute-Data/output/nsxusd"
dfs = []
for f in glob.glob(os.path.join(d, "*.csv")):
    try:
        _df = pd.read_csv(f, sep=';', header=None, names=['date','open','high','low','close','volume'])
        _df['datetime'] = pd.to_datetime(_df['date'], format='%Y%m%d %H%M%S')
        _df = _df.set_index('datetime'); dfs.append(_df)
    except: pass
df = pd.concat(dfs).sort_index()
df15 = df.resample('15min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
op,hi,lo,cl = df15['open'].values,df15['high'].values,df15['low'].values,df15['close'].values
emas = compute_emas(cl,[25,100])
atr  = compute_atr(hi,lo,cl,14)
asma = compute_sma(atr,50)
print("Done. Running simulations...\n")

# Run all 4 combinations
r7_nobe, g7_nobe = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma, 7.0, has_be=False)
r7_be,   g7_be   = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma, 7.0, has_be=True)
r20_nobe,g20_nobe= run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma,20.0, has_be=False)
r20_be,  g20_be  = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma,20.0, has_be=True)

print("Calculating stats (MC takes ~30s)...")
s7n  = stats(r7_nobe,  g7_nobe)
print("7RR No-BE done")
s7b  = stats(r7_be,    g7_be)
print("7RR With-BE done")
s20n = stats(r20_nobe, g20_nobe)
print("20RR No-BE done")
s20b = stats(r20_be,   g20_be)
print("20RR With-BE done\n")

def row(label, nobe, be):
    def fmt(v):
        if isinstance(v, float):
            if abs(v) > 999: return f"${v:,.0f}" if 'Eq' in label or 'DD ($' in label else f"{v:.2f}%"
            return f"{v:.2f}%"
        return str(v)
    print(f"  {label:<35} | {str(nobe):<22} | {str(be)}")

print("=" * 85)
print(f"{'METRIC':<37} | {'7RR NO-BE':<22} | {'7RR WITH-BE (3.5x trigger)'}")
print("=" * 85)
print(f"  {'Executions':<35} | {s7n['n']:<22} | {s7b['n']}")
print(f"  {'Win Rate':<35} | {s7n['wr']:.2f}%{'':<17} | {s7b['wr']:.2f}%")
print(f"  {'Wins / Losses / Scratch BEs':<35} | {s7n['wins']}/{s7n['losses']}/{s7n['bes']:<13} | {s7b['wins']}/{s7b['losses']}/{s7b['bes']}")
print(f"  {'Flat $1k -> Final Equity':<35} | ${s7n['flat_eq']:,.0f}{'':<15} | ${s7b['flat_eq']:,.0f}")
print(f"  {'Flat $1k -> Max DD':<35} | ${s7n['flat_dd']:,.0f}{'':<15} | ${s7b['flat_dd']:,.0f}")
print(f"  {'Goldilocks $300/$75 -> Equity':<35} | ${s7n['gold_eq']:,.0f}{'':<15} | ${s7b['gold_eq']:,.0f}")
print(f"  {'Goldilocks $300/$75 -> Max DD':<35} | ${s7n['gold_dd']:,.0f}{'':<15} | ${s7b['gold_dd']:,.0f}")
print(f"  {'0.5% Comp -> Equity':<35} | ${s7n['c05_eq']:,.0f}{'':<15} | ${s7b['c05_eq']:,.0f}")
print(f"  {'0.5% Comp -> Max DD':<35} | {s7n['c05_dd']:.2f}%{'':<17} | {s7b['c05_dd']:.2f}%")
print(f"  {'1.0% Comp -> Equity':<35} | ${s7n['c10_eq']:,.0f}{'':<15} | ${s7b['c10_eq']:,.0f}")
print(f"  {'1.0% Comp -> Max DD':<35} | {s7n['c10_dd']:.2f}%{'':<17} | {s7b['c10_dd']:.2f}%")
print(f"  {'MC Mean Max DD (1000 paths)':<35} | {s7n['mc_dd']:.2f}%{'':<17} | {s7b['mc_dd']:.2f}%")

print()
print("=" * 85)
print(f"{'METRIC':<37} | {'20RR NO-BE':<22} | {'20RR WITH-BE (10x trigger)'}")
print("=" * 85)
print(f"  {'Executions':<35} | {s20n['n']:<22} | {s20b['n']}")
print(f"  {'Win Rate':<35} | {s20n['wr']:.2f}%{'':<17} | {s20b['wr']:.2f}%")
print(f"  {'Wins / Losses / Scratch BEs':<35} | {s20n['wins']}/{s20n['losses']}/{s20n['bes']:<13} | {s20b['wins']}/{s20b['losses']}/{s20b['bes']}")
print(f"  {'Flat $1k -> Final Equity':<35} | ${s20n['flat_eq']:,.0f}{'':<15} | ${s20b['flat_eq']:,.0f}")
print(f"  {'Flat $1k -> Max DD':<35} | ${s20n['flat_dd']:,.0f}{'':<15} | ${s20b['flat_dd']:,.0f}")
print(f"  {'Goldilocks $300/$75 -> Equity':<35} | ${s20n['gold_eq']:,.0f}{'':<15} | ${s20b['gold_eq']:,.0f}")
print(f"  {'Goldilocks $300/$75 -> Max DD':<35} | ${s20n['gold_dd']:,.0f}{'':<15} | ${s20b['gold_dd']:,.0f}")
print(f"  {'0.5% Comp -> Equity':<35} | ${s20n['c05_eq']:,.0f}{'':<15} | ${s20b['c05_eq']:,.0f}")
print(f"  {'0.5% Comp -> Max DD':<35} | {s20n['c05_dd']:.2f}%{'':<17} | {s20b['c05_dd']:.2f}%")
print(f"  {'1.0% Comp -> Equity':<35} | ${s20n['c10_eq']:,.0f}{'':<15} | ${s20b['c10_eq']:,.0f}")
print(f"  {'1.0% Comp -> Max DD':<35} | {s20n['c10_dd']:.2f}%{'':<17} | {s20b['c10_dd']:.2f}%")
print(f"  {'MC Mean Max DD (1000 paths)':<35} | {s20n['mc_dd']:.2f}%{'':<17} | {s20b['mc_dd']:.2f}%")
