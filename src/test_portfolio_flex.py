import pandas as pd
import numpy as np
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

def get_max_micros(phase, equity):
    if phase == 1:
        return 60.0
    else:
        profit = equity - 100000.0
        if profit < 1000.0: return 30.0
        elif profit < 2000.0: return 40.0
        elif profit < 3000.0: return 50.0
        else: return 60.0

def run_portfolio(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, high_risk, low_risk, is_goldilocks):
    num_candles = len(close_p)
    
    target = 5000.0
    eod_max_loss = 2500.0
    eval_consist = 0.40
    funded_consist = 1.0
    init_fee = 264.99
    reset_fee = 147.99
    payout_trigger = 2500.0
    reward_share = 0.95
    
    class Account:
        def __init__(self, is_reset=False):
            self.equity = 100000.0
            self.highest_eod_eq = 100000.0
            self.phase = 1
            self.daily_profit = 0.0
            self.phase_profit = 0.0
            self.max_daily_profit_phase = 0.0
            self.is_reset = is_reset
            self.in_trade = False
            self.contracts = 0.0
            
    accounts = []
    
    current_date = dates[0]
    trading_days = 0
    accounts_launched = 0
    
    # Launch first account
    accounts.append(Account(is_reset=False))
    accounts_launched = 1
    
    fees_spent = init_fee
    payouts_received = 0.0
    evals_blown = 0
    evals_passed = 0
    
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0
    friction = 0.5
    
    for i in range(1, num_candles - 1):
        if dates[i] != current_date:
            # End of day processing
            trading_days += 1
            
            # Launch new accounts every 5 trading days until 10 max
            if trading_days % 5 == 0 and accounts_launched < 10:
                accounts.append(Account(is_reset=False))
                accounts_launched += 1
                fees_spent += init_fee
                
            for acc in accounts:
                if acc.equity > acc.highest_eod_eq:
                    acc.highest_eod_eq = acc.equity
                if acc.daily_profit > acc.max_daily_profit_phase:
                    acc.max_daily_profit_phase = acc.daily_profit
                acc.daily_profit = 0.0
            current_date = dates[i]
            
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            
            if is_goldilocks:
                risk_amt = high_risk if atr[i] > atr_sma[i] else low_risk
            else:
                risk_amt = high_risk
                
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk
            tp_p = entry_p + trade_risk * 7.0
            
            # Calculate contracts for each account
            for acc in accounts:
                desired_micros = risk_amt / (trade_risk * 2.0)
                max_allowed = get_max_micros(acc.phase, acc.equity)
                acc.contracts = min(desired_micros, max_allowed)
                acc.in_trade = True
                
            in_trade = True
            
        if in_trade:
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            trade_closed = False
            exit_px = 0.0
            if current_low <= sl_p:
                exit_px = min(sl_p, open_p[i+1])
                trade_closed = True
            elif current_high >= tp_p:
                exit_px = max(tp_p, open_p[i+1])
                trade_closed = True
                
            # Process open excursion for blowups
            active_accounts = []
            for acc in accounts:
                if not acc.in_trade:
                    active_accounts.append(acc)
                    continue
                    
                unrealized_loss = min(0.0, (mae_px - entry_p - friction) * acc.contracts * 2.0)
                lowest_equity = acc.equity + unrealized_loss
                
                max_loss_threshold = acc.highest_eod_eq - eod_max_loss
                if max_loss_threshold > 100000.0: max_loss_threshold = 100000.0
                
                if lowest_equity <= max_loss_threshold:
                    evals_blown += 1
                    fees_spent += reset_fee
                    active_accounts.append(Account(is_reset=True)) # instantly replace
                else:
                    if trade_closed:
                        profit = (exit_px - entry_p - friction) * acc.contracts * 2.0
                        acc.equity += profit
                        acc.daily_profit += profit
                        acc.phase_profit += profit
                        
                        max_loss_threshold = acc.highest_eod_eq - eod_max_loss
                        if max_loss_threshold > 100000.0: max_loss_threshold = 100000.0
                        
                        if acc.equity <= max_loss_threshold:
                            evals_blown += 1
                            fees_spent += reset_fee
                            active_accounts.append(Account(is_reset=True))
                        else:
                            curr_max_day = max(acc.max_daily_profit_phase, acc.daily_profit)
                            if acc.phase == 1:
                                if acc.phase_profit >= target:
                                    if curr_max_day <= (acc.phase_profit * eval_consist):
                                        acc.phase = 2
                                        acc.equity = 100000.0
                                        acc.highest_eod_eq = 100000.0
                                        acc.daily_profit = 0.0
                                        acc.phase_profit = 0.0
                                        acc.max_daily_profit_phase = 0.0
                                        evals_passed += 1
                            elif acc.phase == 2:
                                if acc.phase_profit >= payout_trigger:
                                    if curr_max_day <= (acc.phase_profit * funded_consist):
                                        payouts_received += (payout_trigger * reward_share)
                                        acc.equity = 100000.0
                                        acc.highest_eod_eq = 100000.0
                                        acc.daily_profit = 0.0
                                        acc.phase_profit = 0.0
                                        acc.max_daily_profit_phase = 0.0
                            active_accounts.append(acc)
                    else:
                        active_accounts.append(acc)
                        
            accounts = active_accounts
            if trade_closed:
                in_trade = False
                for acc in accounts:
                    acc.in_trade = False
                
    return evals_blown, evals_passed, fees_spent, payouts_received

if __name__ == "__main__":
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
    
    risk_models = [
        {"name": "Flat $150 Risk", "hr": 150.0, "lr": 150.0, "g": False},
        {"name": "Flat $300 Risk", "hr": 300.0, "lr": 300.0, "g": False},
        {"name": "$300 / $75 Goldilocks", "hr": 300.0, "lr": 75.0, "g": True},
        {"name": "$600 / $150 Goldilocks", "hr": 600.0, "lr": 150.0, "g": True},
    ]
    
    print(f"\n=========================================================================================")
    print(f"                      10-ACCOUNT PORTFOLIO: Flex $100K (14-Years)")
    print(f"=========================================================================================")
    print(f"{'Risk Size':<25} | {'Blown':<5} | {'Passed':<6} | {'Fees':<10} | {'Payouts':<10} | {'NET PROFIT':<10}")
    print("-" * 89)
    
    for rm in risk_models:
        bl, pa, fees, pay = run_portfolio(
            open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates,
            rm['hr'], rm['lr'], rm['g']
        )
        net = pay - fees
        print(f"{rm['name']:<25} | {bl:<5} | {pa:<6} | ${fees:,.0f}{'':<4} | ${pay:,.0f}{'':<4} | ${net:,.0f}")
