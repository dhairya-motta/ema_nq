import numpy as np
import matplotlib.pyplot as plt
import os

out_dir = "C:/Users/kingcuber/.gemini/antigravity-ide/brain/8de29cf5-0876-457b-989d-862decba2572"
plt.style.use('dark_background')
plt.rcParams.update({'font.family': 'sans-serif', 'axes.facecolor': '#111217', 'figure.facecolor': '#111217'})

np.random.seed(42)

def plot_single_compound(n_trades, win_rate, rr, risk_pct, title, filename, color):
    trades = np.random.choice([rr * risk_pct, -risk_pct], size=n_trades, p=[win_rate, 1-win_rate])
    equity = np.zeros(n_trades + 1)
    equity[0] = 100000
    peak = 100000
    drawdown = np.zeros(n_trades + 1)
    
    for i in range(n_trades):
        equity[i+1] = equity[i] * (1 + trades[i])
        
    for i in range(n_trades + 1):
        if equity[i] > peak: peak = equity[i]
        drawdown[i] = (equity[i] - peak) / peak * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})

    ax1.plot(equity, color=color, linewidth=2, label=f'Equity Curve')
    ax1.set_title(title, fontsize=14, fontweight='bold', color='white', pad=15)
    ax1.set_ylabel('Account Equity ($)', fontsize=12, color='#aaaaaa')
    ax1.legend(loc='upper left')
    ax1.grid(True, linestyle=':', alpha=0.3)

    ax2.fill_between(range(len(drawdown)), drawdown, 0, color='#ff3366', alpha=0.5, label='Drawdown (%)')
    ax2.plot(drawdown, color='#ff3366', linewidth=1)
    ax2.set_xlabel('Number of Trades', fontsize=12, color='#aaaaaa')
    ax2.set_ylabel('Drawdown %', fontsize=12, color='#aaaaaa')
    ax2.legend(loc='lower left')
    ax2.grid(True, linestyle=':', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, filename), dpi=300)
    plt.close()

def plot_mc_compound(n_trades, win_rate, rr, risk_pct, title_eq, title_dd, filename, color):
    n_paths = 100
    start_balance = 100000

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    for _ in range(n_paths):
        trades = np.random.choice([rr * risk_pct, -risk_pct], size=n_trades, p=[win_rate, 1-win_rate])
        equity = np.zeros(n_trades + 1)
        equity[0] = start_balance
        peak = start_balance
        drawdown = np.zeros(n_trades + 1)
        
        for i in range(n_trades):
            equity[i+1] = equity[i] * (1 + trades[i])
        for i in range(n_trades + 1):
            if equity[i] > peak: peak = equity[i]
            drawdown[i] = (equity[i] - peak) / peak * 100
            
        ax1.plot(equity, color=color, alpha=0.15, linewidth=1)
        ax2.plot(drawdown, color='#ff3366', alpha=0.15, linewidth=1)
        
    ax1.set_title(title_eq, fontsize=14, fontweight='bold', color='white')
    ax1.set_xlabel('Number of Trades', color='#aaaaaa')
    ax1.set_ylabel('Account Equity ($)', color='#aaaaaa')
    ax1.grid(True, linestyle=':', alpha=0.3)
    ax1.set_yscale('log') # Log scale because compounding explodes
    
    ax2.set_title(title_dd, fontsize=14, fontweight='bold', color='white')
    ax2.set_xlabel('Number of Trades', color='#aaaaaa')
    ax2.set_ylabel('Drawdown %', color='#aaaaaa')
    ax2.grid(True, linestyle=':', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, filename), dpi=300)
    plt.close()

# 0.5% Compounding for 7RR
plot_single_compound(1373, 0.1605, 7.0, 0.005, '7.0x RR Strategy Profile (0.5% Compounded)', '7rr_compound_05_curve.png', '#00ffcc')
plot_mc_compound(1373, 0.1605, 7.0, 0.005, '7.0x RR (0.5% Comp) MC Equity (Log Scale)', '7.0x RR (0.5% Comp) MC Drawdown', '7rr_compound_05_mc.png', '#00ffcc')

print("Compounding images generated")
