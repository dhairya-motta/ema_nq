import pandas as pd
import numpy as np
from numba import njit
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
def run_prop_firm(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, risk_multiplier, target_rr):
    num_candles = len(close_p)
    
    start_bal = 100000.0
    eval_cost = 455.0
    max_static_loss_level = 92000.0
    
    equity = start_bal
    daily_start_eq = start_bal
    current_date = dates[0]
    
    phase = 1 
    fees_spent = eval_cost
    payouts_received = 0.0
    evals_blown = 0
    evals_passed = 0 
    first_payout_done = False
    
    total_trades = 0
    total_wins = 0
    
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    friction = 0.5
    
    circuit_breaker_active = False
    
    for i in range(1, num_candles - 1):
        if dates[i] != current_date:
            daily_start_eq = equity
            current_date = dates[i]
            circuit_breaker_active = False
            
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long and not circuit_breaker_active:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
                
            risk_pct = (0.006 if atr[i] > atr_sma[i] else 0.0015) * risk_multiplier
            
            # Check if this trade could breach the 4% daily DD limit (using 3.8% as a safety buffer)
            current_daily_dd = (daily_start_eq - equity) / daily_start_eq
            if current_daily_dd + risk_pct >= 0.038:
                circuit_breaker_active = True
                continue 
            
            trade_dir = 1
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk 
            contracts = (equity * risk_pct) / (trade_risk * 20)
            tp_p = entry_p + trade_risk * target_rr
            
            in_trade = True
                    
        if in_trade:
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            unrealized_loss = min(0.0, (mae_px - entry_p - friction) * contracts * 20)
            lowest_equity = equity + unrealized_loss
            daily_dd_pct = (daily_start_eq - lowest_equity) / daily_start_eq
            
            if lowest_equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                evals_blown += 1
                total_trades += 1
                
                equity = start_bal
                daily_start_eq = start_bal
                phase = 1
                fees_spent += eval_cost
                first_payout_done = False
                in_trade = False
                circuit_breaker_active = False
                continue
                
            trade_closed = False
            profit = 0.0
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            if current_low <= sl_p:
                exit_px = min(sl_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                trade_closed = True
            elif current_high >= tp_p:
                exit_px = max(tp_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                trade_closed = True
                    
            if trade_closed:
                equity += profit
                in_trade = False
                total_trades += 1
                if profit > 0: total_wins += 1
                
                daily_dd_pct = (daily_start_eq - equity) / daily_start_eq
                if equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                    evals_blown += 1
                    equity = start_bal
                    daily_start_eq = start_bal
                    phase = 1
                    fees_spent += eval_cost
                    first_payout_done = False
                    circuit_breaker_active = False
                    continue
                
                if phase == 1:
                    if equity >= 108000.0:
                        phase = 2
                        equity = start_bal
                        daily_start_eq = start_bal
                elif phase == 2:
                    if equity >= 105000.0:
                        phase = 3
                        equity = start_bal
                        daily_start_eq = start_bal
                        evals_passed += 1
                        first_payout_done = False
                elif phase == 3: 
                    if not first_payout_done:
                        if equity >= 101000.0:
                            payouts_received += (1000.0 + eval_cost)
                            equity = start_bal
                            daily_start_eq = start_bal
                            first_payout_done = True
                    else:
                        if equity >= 102000.0:
                            payouts_received += 2000.0
                            equity = start_bal
                            daily_start_eq = start_bal
                            
    return (evals_blown, evals_passed, fees_spent, payouts_received, total_trades, total_wins)

if __name__ == "__main__":
    print("Loading tick data for Chronological Prop Firm Backtest...")
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
    
    rr_targets = [5.0, 7.0, 10.0]
    names = ['5.0x Target', '7.0x Target (Base)', '10.0x Target']
    
    records = []
    
    for i, trr in enumerate(rr_targets):
        print(f"Running {names[i]}...")
        # 1.0x risk multiplier
        results = run_prop_firm(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, 1.0, trr)
        
        evals_blown = results[0]
        evals_passed = results[1]
        fees_spent = results[2]
        payouts_received = results[3]
        total_trades = results[4]
        total_wins = results[5]
        
        net_profit = payouts_received - fees_spent
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        records.append({
            'Target RR': names[i],
            'Blown': evals_blown,
            'Passed': evals_passed,
            'Win Rate': f"{win_rate:.2f}%",
            'Fees Spent': f"${fees_spent:,.0f}",
            'Payouts': f"${payouts_received:,.0f}",
            'Net Profit': f"${net_profit:,.0f}"
        })
        
    res_df = pd.DataFrame(records)
    print("\n===========================================================")
    print("      PROP FIRM TARGET RISK:REWARD (RR) SWEEP REPORT       ")
    print("===========================================================")
    print(res_df.to_string(index=False))
