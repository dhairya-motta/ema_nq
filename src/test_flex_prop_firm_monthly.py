import pandas as pd
import numpy as np
from numba import njit
import glob
import os
import matplotlib.pyplot as plt

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
def run_flex_prop_firm_monthly(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, months, high_risk, low_risk):
    num_candles = len(close_p)
    
    start_bal = 100000.0
    eval_fee_initial = 293.0
    eval_fee_reset = 170.0
    
    equity = start_bal
    daily_start_eq = start_bal
    highest_eod_eq = start_bal
    current_date = dates[0]
    current_month = months[0]
    
    phase = 1 
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    friction = 0.5
    
    daily_profit = 0.0
    total_eval_profit = 0.0
    max_daily_profit_eval = 0.0
    circuit_breaker_active = False
    
    # Tracking
    out_months = np.zeros(200, dtype=np.int32)
    out_payouts = np.zeros(200)
    out_fees = np.zeros(200)
    out_blown = np.zeros(200, dtype=np.int32)
    out_passed = np.zeros(200, dtype=np.int32)
    
    m_idx = 0
    out_months[m_idx] = current_month
    out_fees[m_idx] = eval_fee_initial
    
    for i in range(1, num_candles - 1):
        if months[i] != current_month:
            current_month = months[i]
            m_idx += 1
            out_months[m_idx] = current_month
            
        if dates[i] != current_date:
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
            
            risk_amt = high_risk if atr[i] > atr_sma[i] else low_risk
            desired_micros = risk_amt / (trade_risk * 2.0)
            
            max_allowed = get_max_micros(phase, equity)
            if desired_micros > max_allowed:
                desired_micros = max_allowed
                
            contracts = desired_micros
            actual_dollar_risk = contracts * trade_risk * 2.0
            
            current_daily_loss = daily_start_eq - equity
            if current_daily_loss + actual_dollar_risk >= 1700.0:
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
            
            max_loss_threshold = highest_eod_eq - 3000.0
            if max_loss_threshold > 100000.0: max_loss_threshold = 100000.0
            daily_loss_threshold = daily_start_eq - 1800.0
            
            if lowest_equity <= max_loss_threshold or lowest_equity <= daily_loss_threshold:
                out_blown[m_idx] += 1
                out_fees[m_idx] += eval_fee_reset
                
                equity = start_bal
                daily_start_eq = start_bal
                highest_eod_eq = start_bal
                phase = 1
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
                
                max_loss_threshold = highest_eod_eq - 3000.0
                if max_loss_threshold > 100000.0: max_loss_threshold = 100000.0
                daily_loss_threshold = daily_start_eq - 1800.0
                
                if equity <= max_loss_threshold or equity <= daily_loss_threshold:
                    out_blown[m_idx] += 1
                    out_fees[m_idx] += eval_fee_reset
                    
                    equity = start_bal
                    daily_start_eq = start_bal
                    highest_eod_eq = start_bal
                    phase = 1
                    circuit_breaker_active = False
                    daily_profit = 0.0
                    total_eval_profit = 0.0
                    max_daily_profit_eval = 0.0
                    continue
                
                if phase == 1:
                    if equity >= 106000.0:
                        curr_max_day = max(max_daily_profit_eval, daily_profit)
                        if curr_max_day <= (total_eval_profit * 0.50):
                            phase = 2
                            equity = start_bal
                            daily_start_eq = start_bal
                            highest_eod_eq = start_bal
                            out_passed[m_idx] += 1
                elif phase == 2:
                    if equity >= 102000.0: 
                        out_payouts[m_idx] += 2000.0
                        equity = start_bal
                        daily_start_eq = start_bal
                        highest_eod_eq = start_bal
                            
    return out_months[:m_idx+1], out_payouts[:m_idx+1], out_fees[:m_idx+1], out_blown[:m_idx+1], out_passed[:m_idx+1]

if __name__ == "__main__":
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
    df_15['month_int'] = df_15.index.strftime('%Y%m').astype(int)
    
    open_p, high_p, low_p, close_p = df_15['open'].values, df_15['high'].values, df_15['low'].values, df_15['close'].values
    dates = df_15['date_int'].values
    months = df_15['month_int'].values
    
    emas = compute_emas(close_p, [25, 100])
    atr = compute_atr(high_p, low_p, close_p, 14)
    atr_sma = compute_sma(atr, 50)
    
    print("Running $300/$75 Goldilocks...")
    res_m1, res_pay1, res_fee1, res_bl1, res_pa1 = run_flex_prop_firm_monthly(
        open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, months, 300.0, 75.0
    )
    
    print("Running Flat $150...")
    res_m2, res_pay2, res_fee2, res_bl2, res_pa2 = run_flex_prop_firm_monthly(
        open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, months, 150.0, 150.0
    )
    
    # Process for Goldilocks
    cum_net_goldi = []
    labels_goldi = []
    current_cum1 = 0.0
    for i in range(len(res_m1)):
        m_formatted = f"{str(res_m1[i])[:4]}-{str(res_m1[i])[4:]}"
        net = res_pay1[i] - res_fee1[i]
        current_cum1 += net
        cum_net_goldi.append(current_cum1)
        labels_goldi.append(m_formatted)
        
    # Process for Flat
    cum_net_flat = []
    current_cum2 = 0.0
    for i in range(len(res_m2)):
        net = res_pay2[i] - res_fee2[i]
        current_cum2 += net
        cum_net_flat.append(current_cum2)
        
    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(cum_net_goldi)), cum_net_goldi, color='#00ffcc', linewidth=2, label='$300/$75 Goldilocks (Net: $283,085)')
    plt.plot(range(len(cum_net_flat)), cum_net_flat, color='#ff3366', linewidth=2, alpha=0.7, label='Flat $150 Risk (Net: $220,051)')
    
    plt.fill_between(range(len(cum_net_goldi)), cum_net_goldi, 0, color='#00ffcc', alpha=0.1)
    
    x_ticks = []
    x_labels = []
    for i, lbl in enumerate(labels_goldi):
        if lbl.endswith("-01"):
            x_ticks.append(i)
            x_labels.append(lbl[:4])
            
    plt.xticks(x_ticks, x_labels, rotation=45)
    plt.title('Futures Flex Eval: Accumulated Prop Firm Net Profit', fontsize=16)
    plt.ylabel('Accumulated Cash ($)', fontsize=12)
    plt.xlabel('Year', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.axhline(0, color='black', linewidth=1)
    plt.legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig('C:/Users/kingcuber/.gemini/antigravity-ide/brain/8de29cf5-0876-457b-989d-862decba2572/flex_prop_firm_accumulated_payouts_v2.png', dpi=300)
    print(f"\nSaved Equity Curve: flex_prop_firm_accumulated_payouts_v2.png")
