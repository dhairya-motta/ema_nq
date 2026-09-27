import numpy as np
import matplotlib.pyplot as plt
import os

out_dir = "C:/Users/kingcuber/.gemini/antigravity-ide/brain/8de29cf5-0876-457b-989d-862decba2572"
plt.style.use('dark_background')
plt.rcParams.update({'font.family': 'sans-serif', 'axes.facecolor': '#111217', 'figure.facecolor': '#111217'})

np.random.seed(42)

def plot_mc_paths(n_trades, win_rate, rr, title, filename, color):
    n_paths = 1000
    risk_pct = 0.003
    start_balance = 100000

    plt.figure(figsize=(10, 6))
    
    for _ in range(n_paths):
        trades = np.random.choice([rr * risk_pct, -risk_pct], size=n_trades, p=[win_rate, 1-win_rate])
        equity = np.zeros(n_trades + 1)
        equity[0] = start_balance
        for i in range(n_trades):
            equity[i+1] = equity[i] * (1 + trades[i])
        plt.plot(equity, color=color, alpha=0.02, linewidth=1)
        
    plt.title(title, fontsize=14, fontweight='bold', color='white')
    plt.xlabel('Number of Trades', color='#aaaaaa')
    plt.ylabel('Account Equity ($)', color='#aaaaaa')
    plt.grid(True, linestyle=':', alpha=0.3)
    plt.axhline(start_balance, color='white', linestyle='--', linewidth=1)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, filename), dpi=300)
    plt.close()

# 7.0x RR params (14 years)
plot_mc_paths(1373, 0.1605, 7.0, '7.0x RR Monte Carlo Paths (1,000 Simulations)', 'mc_paths_lines_7rr_v2.png', '#00ffcc')

# 20.0x RR params
plot_mc_paths(613, 0.0881, 20.0, '20.0x RR Monte Carlo Paths (1,000 Simulations)', 'mc_paths_lines_20rr_v2.png', '#ff3366')

print("MC path lines generated")
