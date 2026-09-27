import pandas as pd
import numpy as np
from numba import njit
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
def run_prop_firm_monthly_full(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, dates, months, target_rr):
    num_candles = len(close_p)
    
    start_bal = 100000.0
    eval_cost = 455.0
    max_static_loss_level = 92000.0
    
    equity = start_bal
    daily_start_eq = start_bal
    current_date = dates[0]
    current_month = months[0]
    
    phase = 1 
    first_payout_done = False
    in_trade = False
    trade_dir = 0; entry_p = 0.0; sl_p = 0.0; tp_p = 0.0; contracts = 0.0
    friction = 0.5
    
    # Tracking
    out_months = np.zeros(500, dtype=np.int32)
    out_payouts = np.zeros(500)
    out_fees = np.zeros(500)
    out_blown = np.zeros(500, dtype=np.int32)
    out_passed = np.zeros(500, dtype=np.int32)
    out_max_dd = np.zeros(500)
    out_wins = np.zeros(500, dtype=np.int32)
    out_trades = np.zeros(500, dtype=np.int32)
    out_made = np.zeros(500)
    out_lost = np.zeros(500)
    
    m_idx = 0
    out_months[m_idx] = current_month
    out_fees[m_idx] = eval_cost # Initial fee
    
    month_peak_equity = equity
    
    for i in range(1, num_candles - 1):
        if months[i] != current_month:
            current_month = months[i]
            m_idx += 1
            out_months[m_idx] = current_month
            month_peak_equity = equity
            
        if dates[i] != current_date:
            daily_start_eq = equity
            current_date = dates[i]
            
        if equity > month_peak_equity:
            month_peak_equity = equity
            
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            
            risk_pct = 0.006 if atr[i] > atr_sma[i] else 0.0015
            
            trade_dir = 1
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk 
            tp_p = entry_p + trade_risk * target_rr
            
            contracts = (equity * risk_pct) / (trade_risk * 20)
            in_trade = True
                    
        if in_trade:
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            unrealized_loss = min(0.0, (mae_px - entry_p - friction) * contracts * 20)
            lowest_equity = equity + unrealized_loss
            daily_dd_pct = (daily_start_eq - lowest_equity) / daily_start_eq
            
            dd_from_peak = (month_peak_equity - lowest_equity) / month_peak_equity
            if dd_from_peak > out_max_dd[m_idx]:
                out_max_dd[m_idx] = dd_from_peak
            
            if lowest_equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                out_blown[m_idx] += 1
                out_fees[m_idx] += eval_cost
                
                # Assume closed at exactly 0.04 loss if it was daily limit
                loss_amt = equity - lowest_equity
                out_lost[m_idx] += loss_amt
                out_trades[m_idx] += 1
                
                equity = start_bal
                daily_start_eq = start_bal
                phase = 1
                first_payout_done = False
                in_trade = False
                month_peak_equity = equity
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
                out_trades[m_idx] += 1
                
                if profit > 0:
                    out_wins[m_idx] += 1
                    out_made[m_idx] += profit
                else:
                    out_lost[m_idx] += abs(profit)
                
                if equity > month_peak_equity:
                    month_peak_equity = equity
                    
                daily_dd_pct = (daily_start_eq - equity) / daily_start_eq
                if equity <= max_static_loss_level or daily_dd_pct >= 0.04:
                    out_blown[m_idx] += 1
                    out_fees[m_idx] += eval_cost
                    equity = start_bal
                    daily_start_eq = start_bal
                    phase = 1
                    first_payout_done = False
                    month_peak_equity = equity
                    continue
                
                if phase == 1:
                    if equity >= 108000.0:
                        phase = 2
                        equity = start_bal
                        daily_start_eq = start_bal
                        month_peak_equity = equity
                elif phase == 2:
                    if equity >= 105000.0:
                        phase = 3
                        equity = start_bal
                        daily_start_eq = start_bal
                        out_passed[m_idx] += 1
                        first_payout_done = False
                        month_peak_equity = equity
                elif phase == 3: 
                    if not first_payout_done:
                        if equity >= 101000.0:
                            out_payouts[m_idx] += (1000.0 + eval_cost)
                            equity = start_bal
                            daily_start_eq = start_bal
                            first_payout_done = True
                            month_peak_equity = equity
                    else:
                        if equity >= 102000.0:
                            out_payouts[m_idx] += 2000.0
                            equity = start_bal
                            daily_start_eq = start_bal
                            month_peak_equity = equity
                            
    return (out_months[:m_idx+1], out_payouts[:m_idx+1], out_fees[:m_idx+1], out_blown[:m_idx+1], 
            out_passed[:m_idx+1], out_max_dd[:m_idx+1], out_wins[:m_idx+1], out_trades[:m_idx+1], 
            out_made[:m_idx+1], out_lost[:m_idx+1], equity, phase)

if __name__ == "__main__":
    filepath = r"C:\Users\kingcuber\Desktop\algoRange\TBR\NAS100_1m.csv"
    print(f"Loading tick data from {filepath}...")
    
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['time'], utc=True)
    df = df.set_index('datetime')
    
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
    
    rr_targets = [5.0, 7.0, 10.0]
    
    for trr in rr_targets:
        print(f"\n=========================================================================")
        print(f"                MONTHLY REPORT: {trr}x TARGET RR                         ")
        print(f"=========================================================================")
        
        res_m, res_pay, res_fee, res_bl, res_pa, res_mdd, res_w, res_t, res_made, res_lost, final_equity, final_phase = run_prop_firm_monthly_full(
            open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, dates, months, trr
        )
        
        records = []
        for i in range(len(res_m)):
            m_str = str(res_m[i])
            m_formatted = f"{m_str[:4]}-{m_str[4:]}"
            
            pay = res_pay[i]
            fee = res_fee[i]
            net = pay - fee
            wr = (res_w[i] / res_t[i] * 100) if res_t[i] > 0 else 0.0
            
            if res_t[i] > 0 or fee > 0 or pay > 0 or res_bl[i] > 0:
                records.append({
                    'Month': m_formatted,
                    'Made': f"${res_made[i]:,.0f}",
                    'Lost': f"${res_lost[i]:,.0f}",
                    'Max DD': f"{res_mdd[i]*100:.2f}%",
                    'WR': f"{wr:.1f}%",
                    'Blown': res_bl[i],
                    'Passed': res_pa[i],
                    'Payouts': f"${pay:,.0f}",
                    'Net': f"${net:,.0f}"
                })
                
        res_df = pd.DataFrame(records)
        print(res_df.to_string(index=False))
        print(f"\n>> Final Account Equity: ${final_equity:,.2f}")
        phase_str = "Phase 1" if final_phase == 1 else ("Phase 2" if final_phase == 2 else "Funded")
        print(f">> Final Phase Reached: {phase_str}")
