import pandas as pd
import numpy as np
from numba import njit, prange
import glob
import os

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

@njit
def extract_trades(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates):
    num_candles = len(close_p)
    
    # Store daily returns to compute a continuous run
    # Max possible trades ~ 5000
    trade_rets = np.zeros(5000)
    trade_dates = np.zeros(5000)
    trade_count = 0
    
    equity = 100000.0
    friction = 0.5
    
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    current_date = dates[0]
    
    for i in range(1, num_candles - 1):
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long:
            trade_dir = 1
            entry_p = open_p[i+1]
            
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            sl_p = entry_p - trade_risk 
                
            risk_pct = 0.006 if atr[i] > atr_sma[i] else 0.0015
            contracts = (equity * risk_pct) / (trade_risk * 20)
            tp_p = entry_p + trade_risk * 7.0
            
            # The risk percent for this trade:
            # We want to store the actual % return of the trade
            in_trade = True
                    
        current_low = low_p[i+1]
        current_high = high_p[i+1]
        
        if in_trade:
            trade_closed = False
            profit = 0.0
            
            if current_low <= sl_p:
                exit_px = min(sl_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                trade_closed = True
            elif current_high >= tp_p:
                exit_px = max(tp_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                trade_closed = True
                    
            if trade_closed:
                ret_pct = profit / equity
                equity += profit
                if equity <= 0: equity = 0.0001
                in_trade = False
                
                trade_rets[trade_count] = ret_pct
                trade_dates[trade_count] = dates[i]
                trade_count += 1
                
    return trade_rets[:trade_count], trade_dates[:trade_count]

def simulate_prop_firm(trade_rets, trade_dates, max_daily_dd=0.04, max_total_dd=0.12, p1_target=0.08, p2_target=0.05, num_sims=1000):
    # To simulate prop firm, we will randomly pick a starting trade index for each simulation
    # and run the sequence until the account blows up.
    
    passed_p1 = 0
    passed_p2 = 0
    funded_accounts = 0
    total_payouts_pct = 0.0
    
    p1_days_to_pass = []
    p2_days_to_pass = []
    funded_lifespans = []
    payouts_collected = []
    
    np.random.seed(42)
    start_indices = np.random.randint(0, len(trade_rets) - 50, size=num_sims)
    
    for start_idx in start_indices:
        # Phase 1
        equity = 1.0
        peak_eq = 1.0
        start_date = trade_dates[start_idx]
        current_date = start_date
        daily_start_eq = 1.0
        
        passed = False
        failed = False
        idx = start_idx
        
        # PHASE 1
        while idx < len(trade_rets) and not passed and not failed:
            ret = trade_rets[idx]
            trade_date = trade_dates[idx]
            
            if trade_date != current_date:
                daily_start_eq = equity
                current_date = trade_date
                
            equity *= (1.0 + ret)
            if equity > peak_eq: peak_eq = equity
            
            # Check DD
            daily_dd = (daily_start_eq - equity) / daily_start_eq
            total_dd = (peak_eq - equity) / peak_eq
            
            if daily_dd >= max_daily_dd or total_dd >= max_total_dd:
                failed = True
                break
                
            if equity >= 1.0 + p1_target:
                passed = True
                break
                
            idx += 1
            
        if failed or not passed: continue
        passed_p1 += 1
        p1_days_to_pass.append(idx - start_idx)
        
        # PHASE 2
        equity = 1.0
        peak_eq = 1.0
        start_idx = idx
        daily_start_eq = 1.0
        current_date = trade_dates[idx] if idx < len(trade_rets) else 0
        
        passed = False
        failed = False
        
        while idx < len(trade_rets) and not passed and not failed:
            ret = trade_rets[idx]
            trade_date = trade_dates[idx]
            
            if trade_date != current_date:
                daily_start_eq = equity
                current_date = trade_date
                
            equity *= (1.0 + ret)
            if equity > peak_eq: peak_eq = equity
            
            # Check DD
            daily_dd = (daily_start_eq - equity) / daily_start_eq
            total_dd = (peak_eq - equity) / peak_eq
            
            if daily_dd >= max_daily_dd or total_dd >= max_total_dd:
                failed = True
                break
                
            if equity >= 1.0 + p2_target:
                passed = True
                break
                
            idx += 1
            
        if failed or not passed: continue
        passed_p2 += 1
        funded_accounts += 1
        p2_days_to_pass.append(idx - start_idx)
        
        # FUNDED PHASE
        equity = 1.0
        peak_eq = 1.0
        start_idx = idx
        daily_start_eq = 1.0
        current_date = trade_dates[idx] if idx < len(trade_rets) else 0
        
        failed = False
        payout = 0.0
        days_in_funded = 0
        payouts_for_this_acc = 0.0
        
        while idx < len(trade_rets) and not failed:
            ret = trade_rets[idx]
            trade_date = trade_dates[idx]
            
            if trade_date != current_date:
                daily_start_eq = equity
                current_date = trade_date
                days_in_funded += 1
                
                # Simulate Monthly Payout (every 20 trading days)
                if days_in_funded % 20 == 0:
                    if equity > 1.0:
                        profit = equity - 1.0
                        payouts_for_this_acc += profit
                        equity = 1.0 # Reset equity after payout
                        peak_eq = 1.0
                        daily_start_eq = 1.0
                
            equity *= (1.0 + ret)
            if equity > peak_eq: peak_eq = equity
            
            daily_dd = (daily_start_eq - equity) / daily_start_eq
            total_dd = (peak_eq - equity) / peak_eq
            
            if daily_dd >= max_daily_dd or total_dd >= max_total_dd:
                failed = True
                break
                
            idx += 1
            
        funded_lifespans.append(idx - start_idx)
        payouts_collected.append(payouts_for_this_acc)
        total_payouts_pct += payouts_for_this_acc
        
    return {
        'num_sims': num_sims,
        'passed_p1': passed_p1,
        'passed_p2': passed_p2,
        'avg_p1_trades': np.mean(p1_days_to_pass) if p1_days_to_pass else 0,
        'avg_p2_trades': np.mean(p2_days_to_pass) if p2_days_to_pass else 0,
        'avg_funded_trades': np.mean(funded_lifespans) if funded_lifespans else 0,
        'avg_payout_pct': np.mean(payouts_collected) * 100 if payouts_collected else 0,
        'max_payout_pct': np.max(payouts_collected) * 100 if payouts_collected else 0,
        'total_payout_pct': total_payouts_pct * 100
    }

if __name__ == "__main__":
    print("Loading tick data for Prop Firm Simulation...")
    d = "C:/Users/kingcuber/.gemini/antigravity-ide/scratch/FX-1-Minute-Data/output/nsxusd"
    csv_files = glob.glob(os.path.join(d, "*.csv"))
    
    dfs = []
    for f in csv_files:
        try:
            _df = pd.read_csv(f, sep=';', header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
            _df['datetime'] = pd.to_datetime(_df['date'], format='%Y%m%d %H%M%S')
            _df = _df.set_index('datetime')
            dfs.append(_df)
        except:
            pass
            
    df = pd.concat(dfs).sort_index()
    
    df_15 = df.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    df_15['date_int'] = df_15.index.strftime('%Y%m%d').astype(int)
    
    open_p, high_p, low_p, close_p = df_15['open'].values, df_15['high'].values, df_15['low'].values, df_15['close'].values
    dates = df_15['date_int'].values
    
    emas = compute_emas(close_p, [25, 100])
    atr = compute_atr(high_p, low_p, close_p, 14)
    atr_sma = compute_sma(atr, 50)
    
    print("Extracting trade sequence (Base 7.0 RR)...")
    trade_rets, trade_dates = extract_trades(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates)
    
    print(f"Extracted {len(trade_rets)} trades over 14 years.")
    
    print("Running 5000 Monte Carlo Prop Firm Challenge Simulations (12% Max DD, 4% Daily DD)...")
    res = simulate_prop_firm(trade_rets, trade_dates, max_daily_dd=0.04, max_total_dd=0.12, num_sims=5000)
    
    print("\n==================================================")
    print("           PROP FIRM SIMULATION RESULTS           ")
    print("==================================================")
    print(f"Simulations Run:           {res['num_sims']}")
    print(f"Passed Phase 1:            {res['passed_p1']} ({res['passed_p1']/res['num_sims']*100:.2f}%)")
    print(f"Passed Phase 2 (FUNDED):   {res['passed_p2']} ({res['passed_p2']/res['num_sims']*100:.2f}%)")
    print(f"Avg Trades to Pass P1:     {res['avg_p1_trades']:.1f} trades")
    print(f"Avg Trades to Pass P2:     {res['avg_p2_trades']:.1f} trades")
    print(f"Avg Trades Survived Funded:{res['avg_funded_trades']:.1f} trades")
    print("--------------------------------------------------")
    print(f"Average Payout Collected:  {res['avg_payout_pct']:.2f}% of Account Balance")
    print(f"Max Payout by Top Trader:  {res['max_payout_pct']:.2f}% of Account Balance")
    print("==================================================")
    
    # Calculate Prop Firm leverage scaling
    # $100k Challenge costs ~$500.
    # If Avg Payout is 3%, that's $3000 profit on a $500 risk = 600% ROI.
    print(f"\n* Note: A 3% payout on a $100k account is $3,000. For a $500 challenge fee, that is a 600% ROI.")
