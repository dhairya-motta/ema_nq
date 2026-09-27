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

def run_simulation(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, rr_target, has_be=False, be_thresh=0.0):
    friction = 0.5  # 0.5 points slippage/commission on entry/exit
    
    trades_rr = []
    trades_goldilocks = []
    
    in_trade = False
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    be_trigger_px = 0.0
    be_hit = False
    current_risk_dollar = 0.0
    current_risk_pts = 0.0
    
    for i in range(1, len(close_p) - 1):
        # Strictly LONG ONLY logic from original report
        crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
        
        if not in_trade and crossover_long:
            trade_risk = 2.0 * atr[i]
            if trade_risk < 5.0: trade_risk = 5.0
            
            # Goldilocks $300 / $75 sizing
            risk_amt = 300.0 if atr[i] > atr_sma[i] else 75.0
            
            entry_p = open_p[i+1]
            sl_p = entry_p - trade_risk
            tp_p = entry_p + (trade_risk * rr_target)
            
            if has_be:
                be_trigger_px = entry_p + (trade_risk * be_thresh)
                
            in_trade = True
            be_hit = False
            current_risk_dollar = risk_amt
            current_risk_pts = trade_risk
            
        elif in_trade:
            # We are holding a trade
            # Process Excursions (Slippage applied to exit executions later)
            mae_px = min(open_p[i+1], low_p[i+1])
            if mae_px <= sl_p: mae_px = sl_p
            
            current_low = low_p[i+1]
            current_high = high_p[i+1]
            
            trade_closed = False
            result_rr = 0.0
            
            if not be_hit:
                if current_low <= sl_p:
                    result_rr = -1.0
                    trade_closed = True
                elif current_high >= tp_p:
                    result_rr = rr_target
                    trade_closed = True
                elif has_be and current_high >= be_trigger_px:
                    be_hit = True
                    sl_p = entry_p # Move stop to BE
            
            if be_hit and not trade_closed:
                if current_low <= sl_p:
                    result_rr = 0.0
                    trade_closed = True
                elif current_high >= tp_p:
                    result_rr = rr_target
                    trade_closed = True
                    
            if trade_closed:
                # Calculate Friction Penalty in RR terms
                friction_rr = (friction * 2.0) / current_risk_pts
                final_rr = result_rr - friction_rr
                
                goldilocks_pnl = final_rr * current_risk_dollar
                
                trades_rr.append(final_rr)
                trades_goldilocks.append(goldilocks_pnl)
                in_trade = False

    trades_rr = np.array(trades_rr)
    trades_goldilocks = np.array(trades_goldilocks)
    
    total_trades = len(trades_rr)
    wins = len(trades_rr[trades_rr > 0])
    
    # === MODEL 1: Flat $1,000 Risk ===
    flat_eq = np.zeros(total_trades + 1)
    flat_eq[0] = 100000.0
    for i in range(total_trades):
        flat_eq[i+1] = flat_eq[i] + (trades_rr[i] * 1000.0)
    flat_dd_abs = np.max(np.maximum.accumulate(flat_eq) - flat_eq)
    
    # === MODEL 2: Goldilocks $300/$75 ===
    gold_eq = np.zeros(total_trades + 1)
    gold_eq[0] = 100000.0
    for i in range(total_trades):
        gold_eq[i+1] = gold_eq[i] + trades_goldilocks[i]
    gold_dd_abs = np.max(np.maximum.accumulate(gold_eq) - gold_eq)
    
    # === MODEL 3: 0.5% Compounding ===
    comp05_eq = np.zeros(total_trades + 1)
    comp05_eq[0] = 100000.0
    for i in range(total_trades):
        comp05_eq[i+1] = comp05_eq[i] * (1 + (trades_rr[i] * 0.005))
    peak05 = np.maximum.accumulate(comp05_eq)
    comp05_dd_pct = np.max((peak05 - comp05_eq) / peak05 * 100)
    
    # === MODEL 4: 1.0% Compounding ===
    comp10_eq = np.zeros(total_trades + 1)
    comp10_eq[0] = 100000.0
    for i in range(total_trades):
        comp10_eq[i+1] = comp10_eq[i] * (1 + (trades_rr[i] * 0.01))
    peak10 = np.maximum.accumulate(comp10_eq)
    comp10_dd_pct = np.max((peak10 - comp10_eq) / peak10 * 100)
    
    return {
        "Executions": total_trades,
        "Wins": wins,
        "Flat_Eq": flat_eq[-1],
        "Flat_DD": flat_dd_abs,
        "Gold_Eq": gold_eq[-1],
        "Gold_DD": gold_dd_abs,
        "Comp05_Eq": comp05_eq[-1],
        "Comp05_DD": comp05_dd_pct,
        "Comp10_Eq": comp10_eq[-1],
        "Comp10_DD": comp10_dd_pct,
    }

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
        except: pass
    df = pd.concat(dfs).sort_index()
    df_15 = df.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    
    open_p, high_p, low_p, close_p = df_15['open'].values, df_15['high'].values, df_15['low'].values, df_15['close'].values
    
    emas = compute_emas(close_p, [25, 100])
    atr = compute_atr(high_p, low_p, close_p, 14)
    atr_sma = compute_sma(atr, 50)
    
    print("\n" + "="*80)
    print("THE TRUTH MATRIX: MATHEMATICAL ENGINE BASELINE (14-YEARS)")
    print("="*80)
    
    # 7.0x RR Strategy (NO BE)
    r7 = run_simulation(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 7.0, False)
    # 20.0x RR Strategy (NO BE)
    r20 = run_simulation(open_p, high_p, low_p, close_p, emas[25], emas[100], atr, atr_sma, 20.0, False)
    
    print("\n--- 7.0x RISK-TO-REWARD STRATEGY ---")
    print(f"Total Executions: {r7['Executions']} | Wins: {r7['Wins']}")
    print(f"1) Flat $1,000 Risk:       Equity = ${r7['Flat_Eq']:,.2f} | Max DD = ${r7['Flat_DD']:,.2f}")
    print(f"2) Goldilocks $300/$75:    Equity = ${r7['Gold_Eq']:,.2f} | Max DD = ${r7['Gold_DD']:,.2f}")
    print(f"3) 0.5% Compounding:       Equity = ${r7['Comp05_Eq']:,.2f} | Max DD = {r7['Comp05_DD']:.2f}%")
    print(f"4) 1.0% Compounding:       Equity = ${r7['Comp10_Eq']:,.2f} | Max DD = {r7['Comp10_DD']:.2f}%")
    
    print("\n--- 20.0x RISK-TO-REWARD STRATEGY ---")
    print(f"Total Executions: {r20['Executions']} | Wins: {r20['Wins']}")
    print(f"1) Flat $1,000 Risk:       Equity = ${r20['Flat_Eq']:,.2f} | Max DD = ${r20['Flat_DD']:,.2f}")
    print(f"2) Goldilocks $300/$75:    Equity = ${r20['Gold_Eq']:,.2f} | Max DD = ${r20['Gold_DD']:,.2f}")
    print(f"3) 0.5% Compounding:       Equity = ${r20['Comp05_Eq']:,.2f} | Max DD = {r20['Comp05_DD']:.2f}%")
    print(f"4) 1.0% Compounding:       Equity = ${r20['Comp10_Eq']:,.2f} | Max DD = {r20['Comp10_DD']:.2f}%")
    print("\n" + "="*80)
