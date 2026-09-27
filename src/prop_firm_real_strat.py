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

def run_real_strat_prop_sim(df, risk_pct_label, risk_pct_val, friction=0.75, min_sl_dist=10.0):
    open_p = df['open'].values
    high_p = df['high'].values
    low_p = df['low'].values
    close_p = df['close'].values
    dates = df['date'].values
    
    fast_period, slow_period = 25, 50
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
    start_date_funded = None
    days_in_p1_total = 0
    days_in_p2_total = 0
    passes_p1 = 0
    passes_p2 = 0
    
    payout_dates = []
    first_payout_days_total = 0
    first_payouts_count = 0
    
    sod_equity = 100000.0
    can_trade_today = True
    
    in_trade = False
    trade_dir = 0
    entry_price = 0.0
    sl_price = 0.0
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
                    # Protection Rule: If taking this risk would breach 4% daily loss, halt for the day.
                    current_daily_loss = sod_equity - equity
                    proposed_risk_dollars = equity * risk_pct_val
                    if current_daily_loss + proposed_risk_dollars >= sod_equity * 0.038: # slight buffer below 4%
                        can_trade_today = False
                        continue
                        
                    if phase == 1 and start_date_phase1 is None: start_date_phase1 = pd.to_datetime(dates[i])
                    if phase == 2 and start_date_phase2 is None: start_date_phase2 = pd.to_datetime(dates[i])
                    if phase == 3 and start_date_funded is None: start_date_funded = pd.to_datetime(dates[i])
                            
                    if crossover_long:
                        trade_dir = 1
                        entry_price = open_p[i+1]
                        sl_price = low_p[i] # Candle low
                        
                        trade_risk = entry_price - sl_price
                        if trade_risk < min_sl_dist:
                            trade_risk = min_sl_dist
                            sl_price = entry_price - min_sl_dist
                            
                        if trade_risk > 0:
                            risk_dollars = equity * risk_pct_val
                            contracts = risk_dollars / trade_risk
                            in_trade = True
                            
                    elif crossover_short:
                        trade_dir = -1
                        entry_price = open_p[i+1]
                        sl_price = high_p[i] # Candle high
                        
                        trade_risk = sl_price - entry_price
                        if trade_risk < min_sl_dist:
                            trade_risk = min_sl_dist
                            sl_price = entry_price + min_sl_dist
                            
                        if trade_risk > 0:
                            risk_dollars = equity * risk_pct_val
                            contracts = risk_dollars / trade_risk
                            in_trade = True
        else:
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            # Trailing update
            if trade_dir == 1 and slow_ema[i] > sl_price:
                sl_price = slow_ema[i]
            elif trade_dir == -1 and slow_ema[i] < sl_price:
                sl_price = slow_ema[i]
            
            # Check MAE for blowups
            if trade_dir == 1:
                mae = entry_price - current_low
            else:
                mae = current_high - entry_price
                
            min_equity = equity - (mae * contracts)
            
            if min_equity <= 92000 or min_equity <= sod_equity * 0.96:
                evals_blown += 1
                fees_spent += 455.0
                equity = 100000.0
                sod_equity = 100000.0
                phase = 1
                start_date_phase1 = None
                start_date_phase2 = None
                start_date_funded = None
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
            elif trade_dir == -1:
                if current_high >= sl_price:
                    exit_price = max(sl_price, open_p[i+1])
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
                    start_date_funded = None
                    can_trade_today = False
                    continue
                    
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
                    start_date_funded = pd.to_datetime(dates[i])
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
                        payout_dates.append(pd.to_datetime(dates[i]))
                        if start_date_funded is not None:
                            first_payout_days_total += (pd.to_datetime(dates[i]) - start_date_funded).days
                            first_payouts_count += 1
                        equity = 100000.0
                        sod_equity = 100000.0
                        can_trade_today = True
                    elif first_payout_done and equity >= 102000:
                        payouts_value += (equity - 100000)
                        num_payouts += 1
                        payout_dates.append(pd.to_datetime(dates[i]))
                        equity = 100000.0
                        sod_equity = 100000.0
                        can_trade_today = True

    avg_p1 = round(days_in_p1_total / passes_p1, 1) if passes_p1 > 0 else 0
    avg_p2 = round(days_in_p2_total / passes_p2, 1) if passes_p2 > 0 else 0
    avg_first_payout_time = round(first_payout_days_total / first_payouts_count, 1) if first_payouts_count > 0 else 0
    
    # Avg time between subsequent payouts
    avg_subs_payout_time = 0
    if len(payout_dates) > 1:
        diffs = [(payout_dates[j] - payout_dates[j-1]).days for j in range(1, len(payout_dates))]
        avg_subs_payout_time = round(np.mean(diffs), 1)
        
    win_rate = round(wins / trades * 100, 2) if trades > 0 else 0
    net_profit = payouts_value - fees_spent
    
    return {
        'Risk Mode': risk_pct_label,
        'Evals Blown': evals_blown,
        'Evals Passed': evals_passed,
        'Total Payouts': num_payouts,
        'Payouts ($)': round(payouts_value, 2),
        'Net Profit': round(net_profit, 2),
        'Win Rate (%)': win_rate,
        'Avg Days P1': avg_p1,
        'Avg Days P2': avg_p2,
        'Days to 1st Payout': avg_first_payout_time,
        'Days between Payouts': avg_subs_payout_time
    }

if __name__ == "__main__":
    file_path = "C:/Users/kingcuber/Desktop/algoRange/TBR/Dataset_NQ_1min_2022_2025.csv"
    print("Loading and resampling data to 5min...")
    df = pd.read_csv(file_path).dropna(subset=['open', 'high', 'low', 'close'])
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df = df.set_index('timestamp ET')
    
    tf_df = df.resample('5min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    tf_df['date'] = tf_df.index.date
    
    modes = [
        ('C (0.1%)', 0.001),
        ('A (0.3%)', 0.003),
        ('B (0.5%)', 0.005),
        ('D (1.0%)', 0.01)
    ]
    
    results = []
    
    for label, val in modes:
        res = run_real_strat_prop_sim(tf_df, label, val)
        results.append(res)
        
    res_df = pd.DataFrame(results)
    print("\n--- REAL ACCOUNT STRAT (27/48 5m TRAILING) ON PROP FIRM EVALS ---")
    print(res_df.to_string(index=False))
