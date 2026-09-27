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
def get_max_micros(phase, equity):
    if phase == 1:
        return 60.0
    else:
        profit = equity - 100000.0
        if profit < 1000.0: return 30.0
        elif profit < 2000.0: return 40.0
        elif profit < 3000.0: return 50.0
        else: return 60.0

@njit
def run_flex_prop_firm(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, high_risk, low_risk):
    num_candles = len(close_p)
    
    start_bal = 100000.0
    eval_fee_initial = 293.0
    eval_fee_reset = 170.0
    
    equity = start_bal
    daily_start_eq = start_bal
    highest_eod_eq = start_bal
    current_date = dates[0]
    
    phase = 1 # 1: Eval, 2: Funded
    fees_spent = eval_fee_initial
    payouts_received = 0.0
    evals_blown = 0
    evals_passed = 0 
    
    total_trades = 0
    total_wins = 0
    
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    friction = 0.5
    
    # 50% Consistency tracker
    daily_profit = 0.0
    total_eval_profit = 0.0
    max_daily_profit_eval = 0.0
    
    circuit_breaker_active = False
    
    for i in range(1, num_candles - 1):
        if dates[i] != current_date:
            # End of day logic
            if equity > highest_eod_eq:
                highest_eod_eq = equity
                
            if phase == 1:
                if daily_profit > max_daily_profit_eval:
                    max_daily_profit_eval = daily_profit
            
            daily_start_eq = equity
            current_date = dates[i]
            daily_profit = 0.0
            circuit_breaker_active = False
            
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long and not circuit_breaker_active:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            
            # Sizing in Micros (1 micro = $2 per point)
            # Total Dollar Risk = contracts * trade_risk * 2.0
            # So contracts = risk_amount / (trade_risk * 2.0)
            
            # Use volatility to scale risk
            risk_amt = high_risk if atr[i] > atr_sma[i] else low_risk
            desired_micros = risk_amt / (trade_risk * 2.0)
            
            max_allowed = get_max_micros(phase, equity)
            if desired_micros > max_allowed:
                desired_micros = max_allowed
                
            contracts = desired_micros
            actual_dollar_risk = contracts * trade_risk * 2.0
            
            # Circuit Breaker to prevent Daily Loss Limit ($1800)
            # DLL threshold is daily_start_eq - 1800
            current_daily_loss = daily_start_eq - equity
            if current_daily_loss + actual_dollar_risk >= 1700.0: # small buffer
                circuit_breaker_active = True
                continue
                
            trade_dir = 1
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk 
            tp_p = entry_p + trade_risk * 7.0
            in_trade = True
                    
        if in_trade:
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            unrealized_loss = min(0.0, (mae_px - entry_p - friction) * contracts * 2.0)
            lowest_equity = equity + unrealized_loss
            
            # Max Loss Threshold (Trailing EOD by $3000, locking at $100k)
            max_loss_threshold = highest_eod_eq - 3000.0
            if max_loss_threshold > 100000.0:
                max_loss_threshold = 100000.0
                
            # Daily Loss Threshold ($1800)
            daily_loss_threshold = daily_start_eq - 1800.0
            
            if lowest_equity <= max_loss_threshold or lowest_equity <= daily_loss_threshold:
                evals_blown += 1
                total_trades += 1
                
                equity = start_bal
                daily_start_eq = start_bal
                highest_eod_eq = start_bal
                phase = 1
                fees_spent += eval_fee_reset
                in_trade = False
                circuit_breaker_active = False
                daily_profit = 0.0
                total_eval_profit = 0.0
                max_daily_profit_eval = 0.0
                continue
                
            trade_closed = False
            profit = 0.0
            
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            if current_low <= sl_p:
                exit_px = min(sl_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 2.0
                trade_closed = True
            elif current_high >= tp_p:
                exit_px = max(tp_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 2.0
                trade_closed = True
                    
            if trade_closed:
                equity += profit
                daily_profit += profit
                if phase == 1:
                    total_eval_profit += profit
                    
                in_trade = False
                total_trades += 1
                if profit > 0: total_wins += 1
                
                max_loss_threshold = highest_eod_eq - 3000.0
                if max_loss_threshold > 100000.0: max_loss_threshold = 100000.0
                daily_loss_threshold = daily_start_eq - 1800.0
                
                if equity <= max_loss_threshold or equity <= daily_loss_threshold:
                    evals_blown += 1
                    equity = start_bal
                    daily_start_eq = start_bal
                    highest_eod_eq = start_bal
                    phase = 1
                    fees_spent += eval_fee_reset
                    circuit_breaker_active = False
                    daily_profit = 0.0
                    total_eval_profit = 0.0
                    max_daily_profit_eval = 0.0
                    continue
                
                if phase == 1:
                    if equity >= 106000.0:
                        # Check 50% consistency
                        curr_max_day = max(max_daily_profit_eval, daily_profit)
                        if curr_max_day <= (total_eval_profit * 0.50):
                            phase = 2
                            equity = start_bal
                            daily_start_eq = start_bal
                            highest_eod_eq = start_bal
                            evals_passed += 1
                elif phase == 2:
                    if equity >= 102000.0: # Trigger $2k Payout
                        payouts_received += 2000.0
                        equity = start_bal
                        daily_start_eq = start_bal
                        highest_eod_eq = start_bal
                            
    return (evals_blown, evals_passed, fees_spent, payouts_received, total_trades, total_wins)

if __name__ == "__main__":
    print("Loading 14-year tick data for Flex Prop Firm Backtest...")
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
    
    risks = [(300.0, 75.0), (600.0, 150.0)]
    names = ['$300/$75 Goldilocks', '$600/$150 Goldilocks']
    
    records = []
    
    for i, r_tuple in enumerate(risks):
        high_r, low_r = r_tuple
        print(f"Running {names[i]}...")
        results = run_flex_prop_firm(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, high_r, low_r)
        
        evals_blown = results[0]
        evals_passed = results[1]
        fees_spent = results[2]
        payouts_received = results[3]
        total_trades = results[4]
        total_wins = results[5]
        
        net_profit = payouts_received - fees_spent
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        records.append({
            'Risk Size': names[i],
            'Blown': evals_blown,
            'Passed': evals_passed,
            'Win Rate': f"{win_rate:.2f}%",
            'Fees Spent': f"${fees_spent:,.0f}",
            'Payouts': f"${payouts_received:,.0f}",
            'Net Profit': f"${net_profit:,.0f}"
        })
        
    res_df = pd.DataFrame(records)
    print("\n===========================================================")
    print("      100K FLEX EVAL & FUNDED RULES: 14-YEAR REPORT        ")
    print("===========================================================")
    print(res_df.to_string(index=False))
