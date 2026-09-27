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
def run_prop_firm_monthly(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, months):
    num_candles = len(close_p)
    
    start_bal = 100000.0
    eval_cost = 455.0
    max_static_loss_level = 92000.0
    
    equity = start_bal
    daily_start_eq = start_bal
    current_date = dates[0]
    current_month = months[0]
    
    # Real capital baseline
    real_cap_eq = 100000.0
    month_start_real_cap = 100000.0
    
    phase = 1 
    first_payout_done = False
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    real_cap_contracts = 0.0
    friction = 0.5
    
    # Storage arrays for max 200 months
    out_months = np.zeros(200, dtype=np.int32)
    out_payouts = np.zeros(200)
    out_fees = np.zeros(200)
    out_blown = np.zeros(200, dtype=np.int32)
    out_passed = np.zeros(200, dtype=np.int32)
    out_real_return = np.zeros(200)
    
    m_idx = 0
    out_months[m_idx] = current_month
    out_fees[m_idx] = eval_cost # Initial fee
    
    for i in range(1, num_candles - 1):
        if months[i] != current_month:
            # End of month recording for real capital return
            out_real_return[m_idx] = (real_cap_eq - month_start_real_cap) / month_start_real_cap
            month_start_real_cap = real_cap_eq
            
            # Transition to new month
            current_month = months[i]
            m_idx += 1
            out_months[m_idx] = current_month
            
        if dates[i] != current_date:
            daily_start_eq = equity
            current_date = dates[i]
            
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            
            risk_pct = 0.006 if atr[i] > atr_sma[i] else 0.0015
            
            trade_dir = 1
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk 
            tp_p = entry_p + trade_risk * 7.0
            
            contracts = (equity * risk_pct) / (trade_risk * 20)
            real_cap_contracts = (real_cap_eq * risk_pct) / (trade_risk * 20)
            
            in_trade = True
                    
        if in_trade:
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            unrealized_loss = min(0.0, (mae_px - entry_p - friction) * contracts * 20)
            lowest_equity = equity + unrealized_loss
            daily_dd_pct = (daily_start_eq - lowest_equity) / daily_start_eq
            
            if lowest_equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                out_blown[m_idx] += 1
                out_fees[m_idx] += eval_cost
                
                equity = start_bal
                daily_start_eq = start_bal
                phase = 1
                first_payout_done = False
                in_trade = False
                continue
                
            trade_closed = False
            profit = 0.0
            real_profit = 0.0
            
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            if current_low <= sl_p:
                exit_px = min(sl_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                real_profit = (exit_px - entry_p - friction) * real_cap_contracts * 20
                trade_closed = True
            elif current_high >= tp_p:
                exit_px = max(tp_p, open_p[i+1])
                profit = (exit_px - entry_p - friction) * contracts * 20
                real_profit = (exit_px - entry_p - friction) * real_cap_contracts * 20
                trade_closed = True
                    
            if trade_closed:
                equity += profit
                real_cap_eq += real_profit
                if real_cap_eq < 0.0001: real_cap_eq = 0.0001
                in_trade = False
                
                daily_dd_pct = (daily_start_eq - equity) / daily_start_eq
                if equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                    out_blown[m_idx] += 1
                    out_fees[m_idx] += eval_cost
                    equity = start_bal
                    daily_start_eq = start_bal
                    phase = 1
                    first_payout_done = False
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
                        out_passed[m_idx] += 1
                        first_payout_done = False
                elif phase == 3: 
                    if not first_payout_done:
                        if equity >= 101000.0:
                            out_payouts[m_idx] += (1000.0 + eval_cost)
                            equity = start_bal
                            daily_start_eq = start_bal
                            first_payout_done = True
                    else:
                        if equity >= 102000.0:
                            out_payouts[m_idx] += 2000.0
                            equity = start_bal
                            daily_start_eq = start_bal
                            
    out_real_return[m_idx] = (real_cap_eq - month_start_real_cap) / month_start_real_cap
    
    return out_months[:m_idx+1], out_payouts[:m_idx+1], out_fees[:m_idx+1], out_blown[:m_idx+1], out_passed[:m_idx+1], out_real_return[:m_idx+1]

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
    
    open_p = df_15['open'].values
    high_p = df_15['high'].values
    low_p = df_15['low'].values
    close_p = df_15['close'].values
    dates = df_15['date_int'].values
    months = df_15['month_int'].values
    
    emas = compute_emas(close_p, [25, 100])
    atr = compute_atr(high_p, low_p, close_p, 14)
    atr_sma = compute_sma(atr, 50)
    
    res_m, res_pay, res_fee, res_bl, res_pa, res_ret = run_prop_firm_monthly(
        open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, months
    )
    
    records = []
    cumulative_net = 0.0
    cum_net_arr = []
    labels = []
    
    for i in range(len(res_m)):
        m_str = str(res_m[i])
        m_formatted = f"{m_str[:4]}-{m_str[4:]}"
        
        pay = res_pay[i]
        fee = res_fee[i]
        net = pay - fee
        cumulative_net += net
        cum_net_arr.append(cumulative_net)
        labels.append(m_formatted)
        
        # Only show months where something significant happened (fees paid, payout, or pass/fail)
        if fee > 0 or pay > 0 or res_bl[i] > 0 or res_pa[i] > 0:
            records.append({
                'Month': m_formatted,
                'Payouts': f"${pay:,.0f}",
                'Fees': f"${fee:,.0f}",
                'Blown': res_bl[i],
                'Passed': res_pa[i],
                'Net Profit': f"${net:,.0f}",
                'Real Cap Return': f"{res_ret[i]*100:.2f}%"
            })
            
    res_df = pd.DataFrame(records)
    print("\n=========================================================================")
    print("                MONTHLY PROP FIRM ACTION BREAKDOWN                       ")
    print("=========================================================================")
    print(res_df.to_string(index=False))
    
    # Plot Cumulative Net Profit
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(cum_net_arr)), cum_net_arr, color='green', linewidth=2)
    plt.fill_between(range(len(cum_net_arr)), cum_net_arr, 0, color='green', alpha=0.1)
    
    # Formatting X-axis ticks (1 tick per year)
    x_ticks = []
    x_labels = []
    for i, lbl in enumerate(labels):
        if lbl.endswith("-01"): # Jan of each year
            x_ticks.append(i)
            x_labels.append(lbl[:4])
            
    plt.xticks(x_ticks, x_labels, rotation=45)
    plt.title('Accumulated Prop Firm Net Profit (Payouts - Fees)', fontsize=16)
    plt.ylabel('Accumulated Cash ($)', fontsize=12)
    plt.xlabel('Year', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.axhline(0, color='black', linewidth=1)
    
    plt.tight_layout()
    plt.savefig('C:/Users/kingcuber/.gemini/antigravity-ide/brain/8de29cf5-0876-457b-989d-862decba2572/prop_firm_accumulated_payouts.png', dpi=300)
    print(f"\nSaved Equity Curve: prop_firm_accumulated_payouts.png")
