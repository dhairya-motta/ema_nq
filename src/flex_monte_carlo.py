import random
import numpy as np

def run_monte_carlo(win_rate, r_high, r_low, is_goldilocks, trials=10000):
    passes = 0
    blows = 0
    trades_to_pass = []
    
    for _ in range(trials):
        equity = 100000.0
        highest_eod = 100000.0
        trades_taken = 0
        
        while True:
            # Assume 1 trade per day for simplicity in Monte Carlo
            daily_start_eq = equity
            trades_taken += 1
            
            # Determine risk for this trade
            if is_goldilocks:
                trade_risk = r_high if random.random() < 0.5 else r_low
            else:
                trade_risk = r_high
                
            # Outcome
            if random.random() < win_rate:
                profit = trade_risk * 7.0 # 7.0 RR
            else:
                profit = -trade_risk
                
            # Check DLL during trade (max adverse excursion)
            # In Monte Carlo, we just assume the loss is the full risk amount. 
            # If it's a win, it might have dipped, but we'll assume it doesn't hit DLL for simplicity
            if profit < 0:
                lowest_equity = equity - trade_risk
            else:
                lowest_equity = equity - (trade_risk * 0.5) # approximate drawdown on a winning trade
                
            max_loss_thresh = min(100000.0, highest_eod - 3000.0)
            daily_loss_thresh = daily_start_eq - 1800.0
            
            if lowest_equity <= max_loss_thresh or lowest_equity <= daily_loss_thresh:
                blows += 1
                break
                
            equity += profit
            
            if equity > highest_eod:
                highest_eod = equity
                
            max_loss_thresh = min(100000.0, highest_eod - 3000.0)
            daily_loss_thresh = daily_start_eq - 1800.0
            
            if equity <= max_loss_thresh or equity <= daily_loss_thresh:
                blows += 1
                break
                
            if equity >= 106000.0:
                passes += 1
                trades_to_pass.append(trades_taken)
                break
                
    prob_pass = passes / trials * 100
    avg_trades = np.mean(trades_to_pass) if len(trades_to_pass) > 0 else 0
    return prob_pass, avg_trades

configs = [
    ("Flat $150", 0.158, 150.0, 150.0, False),
    ("Flat $300", 0.158, 300.0, 300.0, False),
    ("$300/$75 Goldilocks", 0.158, 300.0, 75.0, True),
    ("$600/$150 Goldilocks", 0.158, 600.0, 150.0, True)
]

print("=========================================================================")
print("            MONTE CARLO SIMULATION: 100K FLEX EVAL (10,000 Trials)       ")
print("=========================================================================")
print(f"{'Risk Model':<25} | {'Prob of Passing':<18} | {'Avg Trades to Pass':<20}")
print("-" * 70)

for name, wr, rh, rl, is_g in configs:
    prob, avg_t = run_monte_carlo(wr, rh, rl, is_g)
    print(f"{name:<25} | {prob:>16.2f}% | {avg_t:>18.1f}")
