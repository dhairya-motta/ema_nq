"""Generate all diagrams for the BE (Breakeven at 50%) strategy variant."""
import pandas as pd
import numpy as np
import glob
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('dark_background')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'axes.facecolor': '#0d1117', 'figure.facecolor': '#0d1117',
    'text.color': 'white', 'axes.labelcolor': '#aaaaaa',
    'xtick.color': '#aaaaaa', 'ytick.color': '#aaaaaa',
    'axes.edgecolor': '#333333', 'grid.color': '#222222',
    'grid.linestyle': ':', 'grid.alpha': 0.5,
})
OUT = "C:/Users/kingcuber/.gemini/antigravity-ide/scratch/Goldilocks-NQ-Strategy/images"
os.makedirs(OUT, exist_ok=True)

def compute_emas(close, periods):
    emas = {}
    for period in periods:
        alpha = 2 / (period + 1)
        ema = np.zeros(len(close)); ema[0] = close[0]
        for i in range(1, len(close)): ema[i] = alpha*close[i] + (1-alpha)*ema[i-1]
        emas[period] = ema
    return emas

def compute_atr(high, low, close, period=14):
    tr = np.zeros(len(close)); tr[0] = high[0]-low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    atr = np.zeros(len(close)); atr[0] = tr[0]
    for i in range(1, len(close)): atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return atr

def compute_sma(data, period):
    sma = np.zeros(len(data)); sma[0] = data[0]
    for i in range(1, len(data)):
        sma[i] = np.mean(data[:i+1]) if i < period else np.mean(data[i-period+1:i+1])
    return sma

def run_engine(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, rr_target, has_be=False):
    friction = 0.5; be_mult = 0.5
    trades_rr = []; gold_pnl = []
    in_trade = False; entry_p=sl_p=tp_p=be_px=risk_pts=gold_risk = 0.0; be_hit=False
    n = len(close_p)
    for i in range(1, n-1):
        co = f_ema[i-1]<=s_ema[i-1] and f_ema[i]>s_ema[i]
        if not in_trade and co:
            eb = i+1
            if eb >= n-1: continue
            risk = max(2.0*atr[i], 5.0)
            gr = 300.0 if atr[i]>atr_sma[i] else 75.0
            entry_p=open_p[eb]; sl_p=entry_p-risk; tp_p=entry_p+risk*rr_target
            be_px=entry_p+risk*rr_target*be_mult
            in_trade=True; be_hit=False; risk_pts=risk; gold_risk=gr
        elif in_trade:
            cb=i+1
            if cb>=n: break
            lo=low_p[cb]; hi=high_p[cb]; go=open_p[cb]
            if has_be and not be_hit and hi>=be_px: be_hit=True; sl_p=entry_p
            closed=False; res=0.0
            if go<=sl_p:
                res=0.0 if be_hit else (go-entry_p)/risk_pts; closed=True
            elif lo<=sl_p: res=0.0 if be_hit else -1.0; closed=True
            elif hi>=tp_p: res=rr_target; closed=True
            if closed:
                fr=(friction*2.0)/risk_pts; frr=res-fr
                trades_rr.append(frr); gold_pnl.append(frr*gold_risk); in_trade=False
    return np.array(trades_rr), np.array(gold_pnl)

def plot_equity_dd(eq_curve, title, filename, color='#00ffcc'):
    n = len(eq_curve)
    peak = np.maximum.accumulate(eq_curve)
    dd_pct = (peak - eq_curve) / peak * 100
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#0d1117')
    ax1.plot(eq_curve, color=color, linewidth=1.5)
    ax1.fill_between(range(n), eq_curve, eq_curve[0], alpha=0.1, color=color)
    ax1.set_title(title, fontsize=13, fontweight='bold', color='white', pad=12)
    ax1.set_ylabel('Account Equity ($)', fontsize=11)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax1.grid(True)
    ax2.fill_between(range(n), -dd_pct, 0, color='#ff3366', alpha=0.6)
    ax2.plot(-dd_pct, color='#ff3366', linewidth=0.8)
    ax2.set_ylabel('Drawdown %', fontsize=11)
    ax2.set_xlabel('Number of Trades', fontsize=11)
    ax2.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def plot_mc_paths(all_paths, title, filename, color='#00ffcc'):
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#0d1117')
    for path in all_paths[:200]: ax.plot(path, color=color, alpha=0.04, linewidth=0.5)
    ax.plot(np.median(all_paths, axis=0), color='white', linewidth=2, label='Median Path')
    ax.set_title(title, fontsize=13, fontweight='bold', color='white', pad=12)
    ax.set_ylabel('Account Equity ($)', fontsize=11)
    ax.set_xlabel('Trade Number', fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.legend(); ax.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def plot_mc_histogram(final_equities, max_dds, title, filename):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#0d1117')
    fig.suptitle(title, fontsize=13, fontweight='bold', color='white')
    eq_range = final_equities.max() - final_equities.min()
    n_bins = max(10, min(50, int(eq_range/1000))) if eq_range > 0 else 1
    if n_bins == 1:
        ax1.axvline(final_equities.mean(), color='#00ffcc', linewidth=4)
    else:
        ax1.hist(final_equities, bins=n_bins, color='#00ffcc', alpha=0.8, edgecolor='none')
    ax1.axvline(np.median(final_equities), color='white', linewidth=2, linestyle='--', label=f'Median: ${np.median(final_equities):,.0f}')
    ax1.axvline(np.mean(final_equities), color='#ff9900', linewidth=2, linestyle='--', label=f'Mean: ${np.mean(final_equities):,.0f}')
    ax1.set_title('Final Equity Distribution', color='white')
    ax1.set_xlabel('Final Equity ($)', fontsize=11)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
    ax1.legend(); ax1.grid(True)
    ax2.hist(max_dds, bins='auto', color='#ff3366', alpha=0.8, edgecolor='none')
    ax2.axvline(np.median(max_dds), color='white', linewidth=2, linestyle='--', label=f'Median DD: {np.median(max_dds):.1f}%')
    ax2.set_title('Max Drawdown Distribution', color='white')
    ax2.set_xlabel('Max Drawdown (%)', fontsize=11)
    ax2.legend(); ax2.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def plot_side_by_side_comparison(eq_nobe, eq_be, rr_label, filename):
    """Overlay equity curves: No-BE vs With-BE on same chart."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#0d1117')
    n = len(eq_nobe)
    ax1.plot(eq_nobe, color='#aaaaaa', linewidth=1.2, alpha=0.8, label='No Breakeven Rule')
    ax1.plot(eq_be,   color='#00ffcc', linewidth=1.5, label='With BE at 50% of TP')
    ax1.set_title(f'{rr_label} Strategy | No-BE vs With-BE Overlay', fontsize=13, fontweight='bold', color='white', pad=12)
    ax1.set_ylabel('Account Equity ($)', fontsize=11)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax1.legend(fontsize=11); ax1.grid(True)
    peak_nobe = np.maximum.accumulate(eq_nobe)
    peak_be   = np.maximum.accumulate(eq_be)
    dd_nobe = (peak_nobe - eq_nobe) / peak_nobe * 100
    dd_be   = (peak_be   - eq_be)   / peak_be   * 100
    ax2.plot(-dd_nobe, color='#ff6666', linewidth=1, alpha=0.8, label='No-BE Drawdown')
    ax2.plot(-dd_be,   color='#ff3366', linewidth=1.2, label='BE Drawdown')
    ax2.set_ylabel('Drawdown %', fontsize=11)
    ax2.set_xlabel('Number of Trades', fontsize=11)
    ax2.legend(fontsize=10); ax2.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

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
print("Done. Running engines...")

# Run all
r7n, g7n  = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma, 7.0, False)
r7b, g7b  = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma, 7.0, True)
r20n,g20n = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma,20.0, False)
r20b,g20b = run_engine(op,hi,lo,cl,emas[25],emas[100],atr,asma,20.0, True)

def make_curves(rr, gp, start=100000.0):
    n = len(rr)
    flat=np.zeros(n+1); flat[0]=start
    gold=np.zeros(n+1); gold[0]=start
    c05=np.zeros(n+1);  c05[0]=start
    c10=np.zeros(n+1);  c10[0]=start
    for i in range(n):
        flat[i+1]=flat[i]+rr[i]*1000
        gold[i+1]=gold[i]+gp[i]
        c05[i+1]=c05[i]*(1+rr[i]*0.005)
        c10[i+1]=c10[i]*(1+rr[i]*0.01)
    return flat, gold, c05, c10

flat7n,gold7n,c05_7n,c10_7n = make_curves(r7n,g7n)
flat7b,gold7b,c05_7b,c10_7b = make_curves(r7b,g7b)
flat20n,gold20n,c05_20n,c10_20n = make_curves(r20n,g20n)
flat20b,gold20b,c05_20b,c10_20b = make_curves(r20b,g20b)

print("Generating charts...")

# Equity curves for BE variants
plot_equity_dd(flat7b, "7.0x RR (BE at 3.5x) | Flat $1,000 Risk | 14-Year Backtest", "7rr_be_equity_flat.png", '#00ffcc')
plot_equity_dd(flat20b, "20.0x RR (BE at 10x) | Flat $1,000 Risk | 14-Year Backtest", "20rr_be_equity_flat.png", '#ff9900')
plot_equity_dd(c10_7b, "7.0x RR (BE at 3.5x) | 1.0% Compounding | 14-Year Backtest", "7rr_be_equity_comp10.png", '#00ccff')
plot_equity_dd(c10_20b, "20.0x RR (BE at 10x) | 1.0% Compounding | 14-Year Backtest", "20rr_be_equity_comp10.png", '#ff6600')

# Side-by-side overlays
plot_side_by_side_comparison(flat7n, flat7b, "7.0x RR | Flat $1,000 Risk", "7rr_be_vs_nobe.png")
plot_side_by_side_comparison(flat20n, flat20b, "20.0x RR | Flat $1,000 Risk", "20rr_be_vs_nobe.png")
plot_side_by_side_comparison(c10_7n, c10_7b, "7.0x RR | 1.0% Compounding", "7rr_be_vs_nobe_comp.png")

# MC for BE variants
print("Running MC simulations (this takes ~2 min)...")
def mc_run(trades_rr, risk=1000.0):
    paths=[]; feqs=[]; dds=[]
    n=len(trades_rr)
    for seed in range(1000):
        rng=np.random.default_rng(seed); sh=rng.permutation(trades_rr)
        eq=np.zeros(n+1); eq[0]=100000
        for j,r in enumerate(sh): eq[j+1]=eq[j]+r*risk
        paths.append(eq); feqs.append(eq[-1])
        pk=np.maximum.accumulate(eq); dds.append(float(np.max((pk-eq)/pk*100)))
    return np.array(paths), np.array(feqs), np.array(dds)

paths_7b, feq_7b, mdd_7b = mc_run(r7b)
print("  7RR BE MC done")
paths_20b, feq_20b, mdd_20b = mc_run(r20b)
print("  20RR BE MC done")

plot_mc_paths(paths_7b, "7.0x RR (BE at 3.5x) | Monte Carlo 1,000-Path Simulation", "mc_paths_7rr_be.png", '#00ffcc')
plot_mc_paths(paths_20b, "20.0x RR (BE at 10x) | Monte Carlo 1,000-Path Simulation", "mc_paths_20rr_be.png", '#ff9900')
plot_mc_histogram(feq_7b, mdd_7b, "7.0x RR (BE at 3.5x) | MC Distribution (1,000 Paths)", "mc_hist_7rr_be.png")
plot_mc_histogram(feq_20b, mdd_20b, "20.0x RR (BE at 10x) | MC Distribution (1,000 Paths)", "mc_hist_20rr_be.png")

print(f"\n7RR BE MC: Mean MaxDD={np.mean(mdd_7b):.2f}% | 0% RoR: {np.sum(feq_7b<0)/10:.1f}%")
print(f"20RR BE MC: Mean MaxDD={np.mean(mdd_20b):.2f}% | 0% RoR: {np.sum(feq_20b<0)/10:.1f}%")
print("\nAll BE charts generated successfully!")
