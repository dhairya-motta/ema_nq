import pandas as pd
import numpy as np

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

def run_prop_firm_sim(df, fast_period, slow_period, risk_mode, friction=0.75, min_sl_dist=10.0, rr_target=0.5):
    open_p = df['open'].values
    high_p = df['high'].values
    low_p = df['low'].values
    close_p = df['close'].values
    dates = df['date'].values
    
    emas = compute_emas(close_p, [fast_period, slow_period])
    fast_ema = emas[fast_period]
    slow_ema = emas[slow_period]
    
    # Account State
    equity = 100000.0
    phase = 1
    evals_blown = 0
    evals_passed = 0
    fees_spent = 455.0
    payouts_value = 0.0
    num_payouts = 0
    first_payout_done = False
    
    # Stats
    trades = 0
    wins = 0
    start_date_phase1 = None
    start_date_phase2 = None
    days_in_p1_total = 0
    days_in_p2_total = 0
    passes_p1 = 0
    passes_p2 = 0
    
    sod_equity = 100000.0
    can_trade_today = True
    
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    contracts = 0.0
    
    for i in range(1, len(close_p) - 1):
        if dates[i] != dates[i-1]:
            sod_equity = equity
            can_trade_today = True
            
        if not in_trade:
            if can_trade_today:
                crossover_long = fast_ema[i-1] <= slow_ema[i-1] and fast_ema[i] > slow_ema[i]
                crossover_short = fast_ema[i-1] >= slow_ema[i-1] and fast_ema[i] < slow_ema[i]
                
                if crossover_long or crossover_short:
                    if phase == 1 and start_date_phase1 is None: start_date_phase1 = pd.to_datetime(dates[i])
                    if phase == 2 and start_date_phase2 is None: start_date_phase2 = pd.to_datetime(dates[i])
                    
                    # Risk Logic
                    daily_drop_pct = (sod_equity - equity) / sod_equity
                    if risk_mode == 'A':
                        risk_pct = 0.01
                    else: # Part B
                        if daily_drop_pct > 0.015: # We lost the first 2% trade, we are down ~2%
                            risk_pct = 0.01
                        else:
                            risk_pct = 0.02
                            
                    if crossover_long:
                        trade_dir = 1
                        entry_price = open_p[i+1]
                        sl_price = min(fast_ema[i], slow_ema[i]) # Smaller EMA
                        
                        trade_risk = entry_price - sl_price
                        if trade_risk < min_sl_dist:
                            trade_risk = min_sl_dist
                            sl_price = entry_price - min_sl_dist
                            
                        if trade_risk > 0:
                            risk_dollars = equity * risk_pct
                            contracts = risk_dollars / trade_risk
                            tp_price = entry_price + trade_risk * rr_target
                            in_trade = True
                            
                    elif crossover_short:
                        trade_dir = -1
                        entry_price = open_p[i+1]
                        sl_price = max(fast_ema[i], slow_ema[i]) # Smaller EMA (higher for short)
                        
                        trade_risk = sl_price - entry_price
                        if trade_risk < min_sl_dist:
                            trade_risk = min_sl_dist
                            sl_price = entry_price + min_sl_dist
                            
                        if trade_risk > 0:
                            risk_dollars = equity * risk_pct
                            contracts = risk_dollars / trade_risk
                            tp_price = entry_price - trade_risk * rr_target
                            in_trade = True
        else:
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            # Check MAE for blowups
            if trade_dir == 1:
                mae = entry_price - current_low
            else:
                mae = current_high - entry_price
                
            min_equity = equity - (mae * contracts)
            
            if min_equity <= 92000 or min_equity <= sod_equity * 0.96:
                # BLOWN
                evals_blown += 1
                fees_spent += 455.0
                equity = 100000.0
                sod_equity = 100000.0
                phase = 1
                start_date_phase1 = None
                start_date_phase2 = None
                in_trade = False
                trades += 1
                can_trade_today = False
                continue
                
            trade_closed = False
            profit = 0.0
            
            if trade_dir == 1:
                if current_low <= sl_price:
                    exit_price = min(sl_price, open_p[i+1])
                    profit = (exit_price - entry_price - friction) * contracts
                    trade_closed = True
                elif current_high >= tp_price:
                    exit_price = max(tp_price, open_p[i+1])
                    profit = (exit_price - entry_price - friction) * contracts
                    trade_closed = True
            elif trade_dir == -1:
                if current_high >= sl_price:
                    exit_price = max(sl_price, open_p[i+1])
                    profit = (entry_price - exit_price - friction) * contracts
                    trade_closed = True
                elif current_low <= tp_price:
                    exit_price = min(tp_price, open_p[i+1])
                    profit = (entry_price - exit_price - friction) * contracts
                    trade_closed = True
                    
            if trade_closed:
                equity += profit
                trades += 1
                if profit > 0: wins += 1
                in_trade = False
                
                if equity <= 92000 or equity <= sod_equity * 0.96:
                    evals_blown += 1
                    fees_spent += 455.0
                    equity = 100000.0
                    sod_equity = 100000.0
                    phase = 1
                    start_date_phase1 = None
                    start_date_phase2 = None
                    can_trade_today = False
                    continue
                    
                if equity <= sod_equity * 0.97:
                    can_trade_today = False
                    
                if phase == 1 and equity >= 108000:
                    phase = 2
                    equity = 100000.0
                    sod_equity = 100000.0
                    if start_date_phase1 is not None:
                        days = (pd.to_datetime(dates[i]) - start_date_phase1).days
                        days_in_p1_total += days
                        passes_p1 += 1
                    start_date_phase1 = None
                    can_trade_today = True
                elif phase == 2 and equity >= 105000:
                    phase = 3
                    equity = 100000.0
                    sod_equity = 100000.0
                    first_payout_done = False
                    evals_passed += 1
                    if start_date_phase2 is not None:
                        days = (pd.to_datetime(dates[i]) - start_date_phase2).days
                        days_in_p2_total += days
                        passes_p2 += 1
                    start_date_phase2 = None
                    can_trade_today = True
                elif phase == 3:
                    if not first_payout_done and equity >= 101000:
                        first_payout_done = True
                        payouts_value += (equity - 100000) + 455.0
                        num_payouts += 1
                        equity = 100000.0
                        sod_equity = 100000.0
                        can_trade_today = True
                    elif first_payout_done and equity >= 102000:
                        payouts_value += (equity - 100000)
                        num_payouts += 1
                        equity = 100000.0
                        sod_equity = 100000.0
                        can_trade_today = True

    avg_p1 = round(days_in_p1_total / passes_p1, 1) if passes_p1 > 0 else 0
    avg_p2 = round(days_in_p2_total / passes_p2, 1) if passes_p2 > 0 else 0
    win_rate = round(wins / trades * 100, 2) if trades > 0 else 0
    net_profit = payouts_value - fees_spent
    
    return {
        'Config': f"{fast_period}/{slow_period}",
        'Mode': risk_mode,
        'Evals Blown': evals_blown,
        'Evals Passed': evals_passed,
        'Payouts #': num_payouts,
        'Payouts ($)': round(payouts_value, 2),
        'Fees Spent': round(fees_spent, 2),
        'Net Profit': round(net_profit, 2),
        'Win Rate (%)': win_rate,
        'Avg Days P1': avg_p1,
        'Avg Days P2': avg_p2
    }

if __name__ == "__main__":
    file_path = "C:/Users/kingcuber/Desktop/algoRange/TBR/Dataset_NQ_1min_2022_2025.csv"
    print("Loading and resampling data...")
    df = pd.read_csv(file_path).dropna(subset=['open', 'high', 'low', 'close'])
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df = df.set_index('timestamp ET')
    
    tf_df = df.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    tf_df['date'] = tf_df.index.date
    
    configs = [(87, 93), (88, 92), (89, 91), (85, 95), (86, 94)]
    
    results = []
    
    for c in configs:
        for mode in ['A', 'B']:
            res = run_prop_firm_sim(tf_df, c[0], c[1], mode)
            results.append(res)
            
    res_df = pd.DataFrame(results)
    print("\n--- PROP FIRM SIMULATION RESULTS ---")
    print(res_df.to_string(index=False))
