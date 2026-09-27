import pandas as pd
import numpy as np
import glob
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

plt.style.use('dark_background')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'axes.facecolor': '#0d1117',
    'figure.facecolor': '#0d1117',
    'text.color': 'white',
    'axes.labelcolor': '#aaaaaa',
    'xtick.color': '#aaaaaa',
    'ytick.color': '#aaaaaa',
    'axes.edgecolor': '#333333',
    'grid.color': '#222222',
    'grid.linestyle': ':',
    'grid.alpha': 0.5,
})

OUT_DIR = "C:/Users/kingcuber/.gemini/antigravity-ide/scratch/Goldilocks-NQ-Strategy/images"
os.makedirs(OUT_DIR, exist_ok=True)

def compute_emas(close, periods):
    emas = {}
    for period in periods:
        alpha = 2 / (period + 1)
        ema = np.zeros(len(close))
        ema[0] = close[0]
        for i in range(1, len(close)):
            ema[i] = alpha * close[i] + (1 - alpha) * ema[i - 1]
        emas[period] = ema
    return emas

def compute_atr(high, low, close, period=14):
    tr = np.zeros(len(close))
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    atr = np.zeros(len(close))
    atr[0] = tr[0]
    for i in range(1, len(close)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

def compute_sma(data, period):
    sma = np.zeros(len(data))
    sma[0] = data[0]
    for i in range(1, len(data)):
        if i < period:
            sma[i] = np.mean(data[:i+1])
        else:
            sma[i] = np.mean(data[i-period+1:i+1])
    return sma

def run_engine(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma,
               rr_target, friction=0.5, noise_std=0.0, latency_bars=0,
               override_friction=None, has_be=False, be_mult=0.5):
    """Master engine: Long-Only, ATR stop, fixed RR target, Goldilocks sizing.
    has_be: move SL to entry once price reaches be_mult * rr_target distance.
    be_mult: fraction of TP at which BE triggers (0.5 = halfway).
    """
    if override_friction is not None:
        friction = override_friction

    trades_rr = []
    goldilocks_pnl = []

    in_trade = False
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    be_trigger_px = 0.0
    be_hit = False
    current_risk_pts = 0.0
    current_gold_risk = 0.0

    n = len(close_p)
    for i in range(1, n - 1):
        f_val = f_ema[i]
        s_val = s_ema[i]
        f_prev = f_ema[i-1]
        s_prev = s_ema[i-1]

        crossover_long = f_prev <= s_prev and f_val > s_val

        if not in_trade and crossover_long:
            exec_bar = i + 1 + latency_bars
            if exec_bar >= n - 1:
                continue

            trade_risk = 2.0 * atr[i]
            if noise_std > 0:
                trade_risk *= (1 + np.random.normal(0, noise_std))
            if trade_risk < 5.0:
                trade_risk = 5.0

            gold_risk = 300.0 if atr[i] > atr_sma[i] else 75.0

            entry_p = open_p[exec_bar]
            sl_p = entry_p - trade_risk
            tp_p = entry_p + trade_risk * rr_target
            # BE triggers at be_mult fraction of the full TP distance
            be_trigger_px = entry_p + trade_risk * rr_target * be_mult

            in_trade = True
            be_hit = False
            current_risk_pts = trade_risk
            current_gold_risk = gold_risk

        elif in_trade:
            check_bar = i + 1
            if check_bar >= n:
                break

            cur_lo = low_p[check_bar]
            cur_hi = high_p[check_bar]
            gap_open = open_p[check_bar]

            # Check if BE should be triggered this bar
            if has_be and not be_hit and cur_hi >= be_trigger_px:
                be_hit = True
                sl_p = entry_p  # Move stop to breakeven

            trade_closed = False
            result_rr = 0.0

            if gap_open <= sl_p:
                # Gap through SL or BE level
                if be_hit:
                    result_rr = 0.0  # Gapped through BE → scratch
                else:
                    result_rr = (gap_open - entry_p) / current_risk_pts
                trade_closed = True
            elif cur_lo <= sl_p:
                result_rr = 0.0 if be_hit else -1.0
                trade_closed = True
            elif cur_hi >= tp_p:
                result_rr = rr_target
                trade_closed = True

            if trade_closed:
                friction_rr = (friction * 2.0) / current_risk_pts
                final_rr = result_rr - friction_rr
                trades_rr.append(final_rr)
                goldilocks_pnl.append(final_rr * current_gold_risk)
                in_trade = False

    return np.array(trades_rr), np.array(goldilocks_pnl)

def build_equity_curves(trades_rr, gold_pnl, start=100000.0):
    n = len(trades_rr)
    flat = np.zeros(n + 1); flat[0] = start
    gold = np.zeros(n + 1); gold[0] = start
    c05  = np.zeros(n + 1); c05[0] = start
    c10  = np.zeros(n + 1); c10[0] = start

    for i in range(n):
        flat[i+1] = flat[i] + trades_rr[i] * 1000.0
        gold[i+1] = gold[i] + gold_pnl[i]
        c05[i+1]  = c05[i] * (1 + trades_rr[i] * 0.005)
        c10[i+1]  = c10[i] * (1 + trades_rr[i] * 0.010)

    return flat, gold, c05, c10

def max_dd_abs(curve):
    peak = np.maximum.accumulate(curve)
    return float(np.max(peak - curve))

def max_dd_pct(curve):
    peak = np.maximum.accumulate(curve)
    dd = (peak - curve) / peak * 100
    return float(np.max(dd))

def sharpe(trades_rr, risk_free=0.0):
    r = np.array(trades_rr)
    if r.std() == 0: return 0.0
    return float((r.mean() - risk_free) / r.std() * np.sqrt(252))

def plot_equity_dd(eq_curve, title, filename, color='#00ffcc'):
    n = len(eq_curve)
    peak = np.maximum.accumulate(eq_curve)
    dd_pct = (peak - eq_curve) / peak * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#0d1117')

    ax1.plot(eq_curve, color=color, linewidth=1.5)
    ax1.fill_between(range(n), eq_curve, eq_curve[0], alpha=0.1, color=color)
    ax1.set_title(title, fontsize=14, fontweight='bold', color='white', pad=12)
    ax1.set_ylabel('Account Equity ($)', fontsize=11)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax1.grid(True)

    ax2.fill_between(range(n), -dd_pct, 0, color='#ff3366', alpha=0.6)
    ax2.plot(-dd_pct, color='#ff3366', linewidth=0.8)
    ax2.set_ylabel('Drawdown %', fontsize=11)
    ax2.set_xlabel('Number of Trades', fontsize=11)
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def plot_mc_paths(all_paths, title, filename, color='#00ffcc'):
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#0d1117')
    n_paths = len(all_paths)
    for path in all_paths[:200]:
        ax.plot(path, color=color, alpha=0.04, linewidth=0.5)
    median_path = np.median(all_paths, axis=0)
    ax.plot(median_path, color='white', linewidth=2, label='Median Path')
    ax.set_title(title, fontsize=14, fontweight='bold', color='white', pad=12)
    ax.set_ylabel('Account Equity ($)', fontsize=11)
    ax.set_xlabel('Trade Number', fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def plot_mc_histogram(final_equities, max_dds, title, filename):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#0d1117')
    fig.suptitle(title, fontsize=14, fontweight='bold', color='white', y=1.01)

    eq_range = final_equities.max() - final_equities.min()
    n_bins_eq = max(10, min(50, int(eq_range / 1000))) if eq_range > 0 else 1
    if n_bins_eq == 1:
        ax1.axvline(final_equities.mean(), color='#00ffcc', linewidth=4, label='All paths identical')
    else:
        ax1.hist(final_equities, bins=n_bins_eq, color='#00ffcc', alpha=0.8, edgecolor='none')
    ax1.axvline(np.median(final_equities), color='white', linewidth=2, linestyle='--', label=f'Median: ${np.median(final_equities):,.0f}')
    ax1.axvline(np.mean(final_equities), color='#ff9900', linewidth=2, linestyle='--', label=f'Mean: ${np.mean(final_equities):,.0f}')
    ax1.set_title('Final Equity Distribution', color='white')
    ax1.set_xlabel('Final Equity ($)', fontsize=11)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
    ax1.legend()
    ax1.grid(True)

    ax2.hist(max_dds, bins='auto', color='#ff3366', alpha=0.8, edgecolor='none')
    ax2.axvline(np.median(max_dds), color='white', linewidth=2, linestyle='--', label=f'Median DD: {np.median(max_dds):.1f}%')
    ax2.set_title('Max Drawdown Distribution', color='white')
    ax2.set_xlabel('Max Drawdown (%)', fontsize=11)
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, filename), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

def run_monte_carlo(trades_rr, n_paths=1000, start=100000.0, risk=1000.0):
    """Shuffle trade sequence 1000 times, record final equities and max DDs."""
    all_paths = []
    final_eqs = []
    max_dds = []
    n = len(trades_rr)

    for seed in range(n_paths):
        rng = np.random.default_rng(seed)
        shuffled = rng.permutation(trades_rr)
        eq = np.zeros(n + 1)
        eq[0] = start
        for i in range(n):
            eq[i+1] = eq[i] + shuffled[i] * risk
        all_paths.append(eq)
        final_eqs.append(eq[-1])
        peak = np.maximum.accumulate(eq)
        dd = (peak - eq) / peak * 100
        max_dds.append(float(np.max(dd)))

    return np.array(all_paths), np.array(final_eqs), np.array(max_dds)

# ============================================================
# LOAD DATA
# ============================================================
print("Loading 14-year data...")
d = "C:/Users/kingcuber/.gemini/antigravity-ide/scratch/FX-1-Minute-Data/output/nsxusd"
csv_files = glob.glob(os.path.join(d, "*.csv"))
dfs = []
for f in csv_files:
    try:
        _df = pd.read_csv(f, sep=';', header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
        _df['datetime'] = pd.to_datetime(_df['date'], format='%Y%m%d %H%M%S')
        _df = _df.set_index('datetime')
        dfs.append(_df)
    except: pass
df = pd.concat(dfs).sort_index()
df_15 = df.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()

open_p  = df_15['open'].values
high_p  = df_15['high'].values
low_p   = df_15['low'].values
close_p = df_15['close'].values
dates   = df_15.index

emas    = compute_emas(close_p, [25, 100])
atr     = compute_atr(high_p, low_p, close_p, 14)
atr_sma = compute_sma(atr, 50)

print("Data loaded. Starting analysis...\n")

# ============================================================
# SECTION 4: BASELINE METRICS
# ============================================================
print("=== SECTION 4: Baseline Metrics ===")
rr7_base, gold7_base = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0)
flat7, goldcurve7, c05_7, c10_7 = build_equity_curves(rr7_base, gold7_base)

n7 = len(rr7_base)
wins7 = int(np.sum(rr7_base > 0))
losses7 = int(np.sum(rr7_base < -0.1))
wr7 = wins7 / n7 * 100

print(f"7.0x RR | Executions: {n7} | Wins: {wins7} ({wr7:.2f}%)")
print(f"  Flat $1k  : ${flat7[-1]:,.2f} | DD: ${max_dd_abs(flat7):,.2f}")
print(f"  Goldilocks: ${goldcurve7[-1]:,.2f} | DD: ${max_dd_abs(goldcurve7):,.2f}")
print(f"  0.5% Comp : ${c05_7[-1]:,.2f} | DD: {max_dd_pct(c05_7):.2f}%")
print(f"  1.0% Comp : ${c10_7[-1]:,.2f} | DD: {max_dd_pct(c10_7):.2f}%")
print(f"  Sharpe    : {sharpe(rr7_base):.3f}")

# 20x baseline
rr20_base, gold20_base = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 20.0)
flat20, goldcurve20, c05_20, c10_20 = build_equity_curves(rr20_base, gold20_base)

n20 = len(rr20_base)
wins20 = int(np.sum(rr20_base > 0))
losses20 = int(np.sum(rr20_base < -0.1))
wr20 = wins20 / n20 * 100

print(f"\n20.0x RR | Executions: {n20} | Wins: {wins20} ({wr20:.2f}%)")
print(f"  Flat $1k  : ${flat20[-1]:,.2f} | DD: ${max_dd_abs(flat20):,.2f}")
print(f"  Goldilocks: ${goldcurve20[-1]:,.2f} | DD: ${max_dd_abs(goldcurve20):,.2f}")
print(f"  0.5% Comp : ${c05_20[-1]:,.2f} | DD: {max_dd_pct(c05_20):.2f}%")
print(f"  1.0% Comp : ${c10_20[-1]:,.2f} | DD: {max_dd_pct(c10_20):.2f}%")
print(f"  Sharpe    : {sharpe(rr20_base):.3f}")

# Plot equity curves
print("\nGenerating equity curve plots...")
plot_equity_dd(flat7, "7.0x RR Strategy | Flat $1,000 Risk per Trade (14 Years, With Friction)", "7rr_equity_curve_v2.png")
plot_equity_dd(flat20, "20.0x RR Strategy | Flat $1,000 Risk per Trade (14 Years, With Friction)", "20rr_equity_curve_v2.png")
plot_equity_dd(c05_7, "7.0x RR Strategy | 0.5% Compounding Risk (14 Years, With Friction)", "7rr_compound_05_curve.png", color='#ff9900')

# ============================================================
# SECTION 3: STRESS TESTS
# ============================================================
print("\n=== SECTION 3: Stress Tests ===")

# Control
rr_ctrl, _ = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0)
flat_ctrl, _, _, _ = build_equity_curves(rr_ctrl, _)
sr_ctrl = sharpe(rr_ctrl)
dd_ctrl = max_dd_pct(flat_ctrl)
print(f"Control:          Equity=${flat_ctrl[-1]:,.0f} | DD={dd_ctrl:.2f}% | Sharpe={sr_ctrl:.3f}")

# Latency injection (skip 2 bars = ~30 mins)
rr_lat, _ = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0, latency_bars=2)
flat_lat, _, _, _ = build_equity_curves(rr_lat, _)
sr_lat = sharpe(rr_lat)
dd_lat = max_dd_pct(flat_lat)
print(f"Latency 30min:    Equity=${flat_lat[-1]:,.0f} | DD={dd_lat:.2f}% | Sharpe={sr_lat:.3f}")

# Gaussian noise
rr_noise, _ = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0, noise_std=0.0005)
flat_noise, _, _, _ = build_equity_curves(rr_noise, _)
sr_noise = sharpe(rr_noise)
dd_noise = max_dd_pct(flat_noise)
print(f"Gaussian Noise:   Equity=${flat_noise[-1]:,.0f} | DD={dd_noise:.2f}% | Sharpe={sr_noise:.3f}")

# Hyper-slippage
rr_slip, _ = run_engine(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0, override_friction=5.0)
flat_slip, _, _, _ = build_equity_curves(rr_slip, _)
sr_slip = sharpe(rr_slip)
dd_slip = max_dd_pct(flat_slip)
print(f"Hyper Slippage:   Equity=${flat_slip[-1]:,.0f} | DD={dd_slip:.2f}% | Sharpe={sr_slip:.3f}")

# ============================================================
# SECTION 5: MONTHLY BREAKDOWN
# ============================================================
print("\n=== SECTION 5: Monthly Breakdown ===")
# Rebuild with trade timestamps
in_trade = False
entry_p = 0.0; sl_p = 0.0; tp_p = 0.0
current_risk_pts = 0.0
friction = 0.5

monthly_data_7 = {}
for i in range(1, len(close_p) - 1):
    crossover_long = emas[25][i-1] <= emas[100][i-1] and emas[25][i] > emas[100][i]
    if not in_trade and crossover_long:
        trade_risk = 2.0 * atr[i]
        if trade_risk < 5.0: trade_risk = 5.0
        entry_p = open_p[i+1]
        sl_p = entry_p - trade_risk
        tp_p = entry_p + trade_risk * 7.0
        in_trade = True
        current_risk_pts = trade_risk
        entry_date = dates[i]
    elif in_trade:
        cur_lo = low_p[i+1]
        cur_hi = high_p[i+1]
        gap_open = open_p[i+1]
        trade_closed = False; result_rr = 0.0
        if gap_open <= sl_p:
            result_rr = (gap_open - entry_p) / current_risk_pts
            trade_closed = True
        elif cur_lo <= sl_p:
            result_rr = -1.0; trade_closed = True
        elif cur_hi >= tp_p:
            result_rr = 7.0; trade_closed = True
        if trade_closed:
            friction_rr = (friction * 2.0) / current_risk_pts
            final_rr = result_rr - friction_rr
            month_key = dates[i].strftime('%Y-%m')
            if month_key not in monthly_data_7:
                monthly_data_7[month_key] = []
            monthly_data_7[month_key].append(final_rr)
            in_trade = False

monthly_pnl_7 = {k: sum(v) * 1000.0 for k, v in monthly_data_7.items()}
monthly_pcts_7 = list(monthly_pnl_7.values())
profitable_7 = [x for x in monthly_pcts_7 if x > 0]
losing_7 = [x for x in monthly_pcts_7 if x <= 0]
print(f"7.0x | Months: {len(monthly_pcts_7)} | Profitable: {len(profitable_7)} ({len(profitable_7)/len(monthly_pcts_7)*100:.1f}%)")
print(f"       Avg Win Month: ${np.mean(profitable_7):,.0f} | Avg Loss Month: ${np.mean(losing_7):,.0f}")
print(f"       Best: ${max(monthly_pcts_7):,.0f} | Worst: ${min(monthly_pcts_7):,.0f}")

# 20x monthly
in_trade = False
monthly_data_20 = {}
for i in range(1, len(close_p) - 1):
    crossover_long = emas[25][i-1] <= emas[100][i-1] and emas[25][i] > emas[100][i]
    if not in_trade and crossover_long:
        trade_risk = 2.0 * atr[i]
        if trade_risk < 5.0: trade_risk = 5.0
        entry_p = open_p[i+1]
        sl_p = entry_p - trade_risk
        tp_p = entry_p + trade_risk * 20.0
        in_trade = True
        current_risk_pts = trade_risk
    elif in_trade:
        cur_lo = low_p[i+1]; cur_hi = high_p[i+1]
        gap_open = open_p[i+1]
        trade_closed = False; result_rr = 0.0
        if gap_open <= sl_p:
            result_rr = (gap_open - entry_p) / current_risk_pts; trade_closed = True
        elif cur_lo <= sl_p:
            result_rr = -1.0; trade_closed = True
        elif cur_hi >= tp_p:
            result_rr = 20.0; trade_closed = True
        if trade_closed:
            friction_rr = (friction * 2.0) / current_risk_pts
            final_rr = result_rr - friction_rr
            month_key = dates[i].strftime('%Y-%m')
            if month_key not in monthly_data_20:
                monthly_data_20[month_key] = []
            monthly_data_20[month_key].append(final_rr)
            in_trade = False

monthly_pnl_20 = {k: sum(v) * 1000.0 for k, v in monthly_data_20.items()}
monthly_pcts_20 = list(monthly_pnl_20.values())
profitable_20 = [x for x in monthly_pcts_20 if x > 0]
losing_20 = [x for x in monthly_pcts_20 if x <= 0]
print(f"\n20.0x | Months: {len(monthly_pcts_20)} | Profitable: {len(profitable_20)} ({len(profitable_20)/len(monthly_pcts_20)*100:.1f}%)")
print(f"        Avg Win Month: ${np.mean(profitable_20):,.0f} | Avg Loss Month: ${np.mean(losing_20):,.0f}")
print(f"        Best: ${max(monthly_pcts_20):,.0f} | Worst: ${min(monthly_pcts_20):,.0f}")

# ============================================================
# SECTION 5.1: MONTE CARLO
# ============================================================
print("\n=== SECTION 5.1: Monte Carlo (1000 paths) ===")
np.random.seed(42)
paths_7, feq_7, mdd_7 = run_monte_carlo(rr7_base, n_paths=1000, risk=1000.0)
print(f"7.0x  | Mean Eq: ${np.mean(feq_7):,.0f} | Median: ${np.median(feq_7):,.0f} | Mean MaxDD: {np.mean(mdd_7):.2f}%")
print(f"       Risk of Ruin (Eq < 0): {np.sum(feq_7 < 0) / len(feq_7) * 100:.2f}%")

np.random.seed(42)
paths_20, feq_20, mdd_20 = run_monte_carlo(rr20_base, n_paths=1000, risk=1000.0)
print(f"20.0x | Mean Eq: ${np.mean(feq_20):,.0f} | Median: ${np.median(feq_20):,.0f} | Mean MaxDD: {np.mean(mdd_20):.2f}%")
print(f"       Risk of Ruin (Eq < 0): {np.sum(feq_20 < 0) / len(feq_20) * 100:.2f}%")

# ============================================================
# SECTION 7: COMPOUNDING MATRIX
# ============================================================
print("\n=== SECTION 7: Compounding Matrix ===")
for rr_label, rr_trades in [("7.0x", rr7_base), ("20.0x", rr20_base)]:
    print(f"\n{rr_label} RR Compounding:")
    for pct in [0.003, 0.005, 0.0075, 0.01]:
        eq = np.zeros(len(rr_trades) + 1); eq[0] = 100000.0
        for i, r in enumerate(rr_trades):
            eq[i+1] = eq[i] * (1 + r * pct)
        peak = np.maximum.accumulate(eq)
        dd = float(np.max((peak - eq) / peak * 100))
        sr = sharpe(rr_trades)
        print(f"  {pct*100:.2f}% Risk: Eq=${eq[-1]:,.0f} | MaxDD={dd:.2f}% | Sharpe={sr:.3f}")

# ============================================================
# GENERATE ALL CHARTS
# ============================================================
print("\n=== Generating All Charts ===")

# MC Paths
plot_mc_paths(paths_7, "7.0x RR | Monte Carlo 1,000-Path Simulation", "mc_paths_lines_7rr_v2.png")
plot_mc_paths(paths_20, "20.0x RR | Monte Carlo 1,000-Path Simulation", "mc_paths_lines_20rr_v2.png", color='#ff9900')

# MC Histograms
plot_mc_histogram(feq_7, mdd_7, "7.0x RR | Monte Carlo Distribution (1,000 Paths)", "mc_path_dependency.png")
plot_mc_histogram(feq_20, mdd_20, "20.0x RR | Monte Carlo Distribution (1,000 Paths)", "mc_path_dependency_20rr.png")

# 0.5% Comp MC paths
np.random.seed(99)
comp05_paths_7 = []
comp05_feq_7 = []
comp05_mdd_7 = []
for _ in range(1000):
    sh = np.random.permutation(rr7_base)
    eq = np.zeros(len(sh)+1); eq[0] = 100000.0
    for i, r in enumerate(sh): eq[i+1] = eq[i] * (1 + r * 0.005)
    comp05_paths_7.append(eq)
    comp05_feq_7.append(eq[-1])
    peak = np.maximum.accumulate(eq)
    comp05_mdd_7.append(float(np.max((peak-eq)/peak*100)))

plot_mc_paths(np.array(comp05_paths_7), "7.0x RR (0.5% Compounding) | MC 1,000-Path Simulation", "7rr_compound_05_mc.png", color='#ff9900')
plot_mc_histogram(np.array(comp05_feq_7), np.array(comp05_mdd_7), "7.0x RR (0.5% Compounding) | MC Distribution", "7rr_compound_05_mc_hist.png")

# Fat-tail distribution chart
print("  Generating fat-tail distribution chart...")
x = np.linspace(-5, 5, 1000)
normal_pdf = np.exp(-x**2/2) / np.sqrt(2*np.pi)
from scipy.stats import t as student_t
fat_tail_pdf = student_t.pdf(x, df=3)
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(x, normal_pdf, color='#aaaaaa', linewidth=2, linestyle='--', label='Normal Distribution (No Edge)')
ax.plot(x, fat_tail_pdf, color='#00ffcc', linewidth=2.5, label='Fat-Tailed Distribution (Real Markets)')
ax.fill_between(x, fat_tail_pdf, normal_pdf, where=(x > 2.5), color='#00ffcc', alpha=0.3, label='Excess Tail Probability (Our Alpha Lives Here)')
ax.fill_between(x, fat_tail_pdf, normal_pdf, where=(x < -2.5), color='#ff3366', alpha=0.3, label='Excess Left Tail Risk')
ax.axvline(0, color='#444444', linewidth=1)
ax.set_xlabel('Standard Deviations from Mean', fontsize=12)
ax.set_ylabel('Probability Density', fontsize=12)
ax.set_title('Fat-Tailed Market Distribution: Why 7x RR Works', fontsize=14, fontweight='bold', color='white', pad=12)
ax.legend(fontsize=10)
ax.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "distribution_fat_tails.png"), dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: distribution_fat_tails.png")

print("\n=== ALL ANALYSIS COMPLETE ===")
print("\n--- FINAL SUMMARY FOR README ---")
print(f"\n7.0x RR: Executions={n7} | WR={wr7:.2f}% | Sharpe={sharpe(rr7_base):.3f}")
print(f"  Flat $1k: ${flat7[-1]:,.0f} | DD: ${max_dd_abs(flat7):,.0f}")
print(f"  Goldilocks: ${goldcurve7[-1]:,.0f} | DD: ${max_dd_abs(goldcurve7):,.0f}")
print(f"  0.5% Comp: ${c05_7[-1]:,.0f} | DD: {max_dd_pct(c05_7):.2f}%")
print(f"  1.0% Comp: ${c10_7[-1]:,.0f} | DD: {max_dd_pct(c10_7):.2f}%")
print(f"\n20.0x RR: Executions={n20} | WR={wr20:.2f}% | Sharpe={sharpe(rr20_base):.3f}")
print(f"  Flat $1k: ${flat20[-1]:,.0f} | DD: ${max_dd_abs(flat20):,.0f}")
print(f"  Goldilocks: ${goldcurve20[-1]:,.0f} | DD: ${max_dd_abs(goldcurve20):,.0f}")
print(f"  0.5% Comp: ${c05_20[-1]:,.0f} | DD: {max_dd_pct(c05_20):.2f}%")
print(f"  1.0% Comp: ${c10_20[-1]:,.0f} | DD: {max_dd_pct(c10_20):.2f}%")
print(f"\nControl Stress Test: ${flat_ctrl[-1]:,.0f} | DD={dd_ctrl:.2f}% | Sharpe={sr_ctrl:.3f}")
print(f"Latency 30min:      ${flat_lat[-1]:,.0f} | DD={dd_lat:.2f}% | Sharpe={sr_lat:.3f}")
print(f"Gaussian Noise:     ${flat_noise[-1]:,.0f} | DD={dd_noise:.2f}% | Sharpe={sr_noise:.3f}")
print(f"Hyper Slippage 5pt: ${flat_slip[-1]:,.0f} | DD={dd_slip:.2f}% | Sharpe={sr_slip:.3f}")
print(f"\n7.0x MC: Mean=${np.mean(feq_7):,.0f} | Median=${np.median(feq_7):,.0f} | MeanDD={np.mean(mdd_7):.2f}%")
print(f"20.0x MC: Mean=${np.mean(feq_20):,.0f} | Median=${np.median(feq_20):,.0f} | MeanDD={np.mean(mdd_20):.2f}%")
print(f"\n7.0x Monthly: {len(monthly_pcts_7)} months | {len(profitable_7)/len(monthly_pcts_7)*100:.1f}% profitable | AvgWin=${np.mean(profitable_7):,.0f} | AvgLoss=${np.mean(losing_7):,.0f} | Best=${max(monthly_pcts_7):,.0f} | Worst=${min(monthly_pcts_7):,.0f}")
print(f"20.0x Monthly: {len(monthly_pcts_20)} months | {len(profitable_20)/len(monthly_pcts_20)*100:.1f}% profitable | AvgWin=${np.mean(profitable_20):,.0f} | AvgLoss=${np.mean(losing_20):,.0f} | Best=${max(monthly_pcts_20):,.0f} | Worst=${min(monthly_pcts_20):,.0f}")
