import numpy as np
import pandas as pd
import glob
import os
from numba import njit
import time

@njit
def compute_emas(close_p, periods):
    res = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = np.zeros_like(close_p)
        ema[0] = close_p[0]
        for i in range(1, len(close_p)):
            ema[i] = (close_p[i] - ema[i-1]) * alpha + ema[i-1]
        res.append(ema)
    return res

@njit
def compute_atr(high_p, low_p, close_p, period=14):
    atr = np.zeros_like(close_p)
    tr = np.zeros_like(close_p)
    tr[0] = high_p[0] - low_p[0]
    atr[0] = tr[0]
    for i in range(1, len(close_p)):
        hl = high_p[i] - low_p[i]
        hc = np.abs(high_p[i] - close_p[i-1])
        lc = np.abs(low_p[i] - close_p[i-1])
        tr[i] = max(hl, hc, lc)
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

@njit
def compute_sma(data, period):
    sma = np.zeros_like(data)
    for i in range(period, len(data)):
        sma[i] = np.mean(data[i-period:i])
    return sma

@njit
def run_engine_fast(open_p, high_p, low_p, close_p, f_ema, s_ema, atr, atr_sma, rr_target):
    friction = 0.5
    in_trade = False
    trade_risk = 0.0
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    
    trades_rr = []
    
    for i in range(1, len(open_p) - 1):
        if not in_trade:
            crossover_long = f_ema[i-1] <= s_ema[i-1] and f_ema[i] > s_ema[i]
            if crossover_long:
                trade_risk = 2.0 * atr[i]
                if trade_risk < 5.0: trade_risk = 5.0
                
                entry_p = open_p[i+1]
                sl_p = entry_p - trade_risk
                tp_p = entry_p + trade_risk * rr_target
                in_trade = True
        
        if in_trade:
            curr_low = low_p[i+1]
            curr_high = high_p[i+1]
            
            if curr_low <= sl_p:
                exit_px = sl_p
                if open_p[i+1] < sl_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                rr_earned = pnl_pts / trade_risk
                trades_rr.append(rr_earned)
                in_trade = False
                
            elif curr_high >= tp_p:
                exit_px = tp_p
                if open_p[i+1] > tp_p: exit_px = open_p[i+1]
                pnl_pts = exit_px - entry_p - friction
                rr_earned = pnl_pts / trade_risk
                trades_rr.append(rr_earned)
                in_trade = False
                
    return trades_rr

def main():
    print("Loading data...")
    d = 'C:/Users/kingcuber/.gemini/antigravity-ide/scratch/FX-1-Minute-Data/output/nsxusd'
    dfs = []
    for f in glob.glob(os.path.join(d, '*.csv')):
        try:
            _df = pd.read_csv(f, sep=';', header=None, names=['date','open','high','low','close','volume'])
            _df['datetime'] = pd.to_datetime(_df['date'], format='%Y%m%d %H%M%S')
            _df = _df.set_index('datetime'); dfs.append(_df)
        except: pass
    df = pd.concat(dfs).sort_index()
    df15 = df.resample('15min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    op, hi, lo, cl = df15['open'].values, df15['high'].values, df15['low'].values, df15['close'].values
    print(f"Loaded {len(cl)} candles.")
    
    atr = compute_atr(hi, lo, cl, 14)
    atr_sma = compute_sma(atr, 50)
    
    fast_emas_to_test = list(range(5, 105, 5))
    slow_emas_to_test = list(range(10, 205, 5))
    
    # Precompute all EMAs
    ema_dict = {}
    periods = sorted(list(set(fast_emas_to_test + slow_emas_to_test)))
    computed_emas = compute_emas(cl, periods)
    for p, e in zip(periods, computed_emas):
        ema_dict[p] = e
        
    rrs_to_test = [5.0, 7.0, 10.0, 15.0, 20.0]
    
    results = []
    years = 14.167
    
    # Compile numba function first
    _ = run_engine_fast(op[:1000], hi[:1000], lo[:1000], cl[:1000], ema_dict[5][:1000], ema_dict[10][:1000], atr[:1000], atr_sma[:1000], 5.0)
    
    total = len(fast_emas_to_test) * len(slow_emas_to_test) * len(rrs_to_test)
    count = 0
    t0 = time.time()
    
    for f_p in fast_emas_to_test:
        for s_p in slow_emas_to_test:
            if f_p >= s_p: continue
            for rr in rrs_to_test:
                f_ema = ema_dict[f_p]
                s_ema = ema_dict[s_p]
                
                trades_rr_list = run_engine_fast(op, hi, lo, cl, f_ema, s_ema, atr, atr_sma, rr)
                trades_rr = np.array(trades_rr_list)
                
                n_trades = len(trades_rr)
                if n_trades == 0: continue
                
                wins = np.sum(trades_rr > 0)
                win_rate = wins / n_trades * 100
                
                eq = np.zeros(n_trades + 1)
                eq[0] = 100000
                for i in range(n_trades):
                    eq[i+1] = eq[i] + trades_rr[i] * 1000.0
                    
                final_eq = eq[-1] - 100000.0
                pk = np.maximum.accumulate(eq)
                max_dd = np.max(pk - eq)
                
                tpy = n_trades / years
                std = np.std(trades_rr * 1000.0)
                if std > 0:
                    sharpe = (np.mean(trades_rr * 1000.0) / std) * np.sqrt(tpy)
                else:
                    sharpe = 0
                
                results.append({
                    'EMA Combo': f'{f_p}/{s_p}',
                    'RR': rr,
                    'Executions': n_trades,
                    'Win Rate': win_rate,
                    'Net Profit ($1k)': final_eq,
                    'Max DD': max_dd,
                    'Sharpe': sharpe
                })
                
                count += 1
                if count % 500 == 0:
                    print(f"Done {count} combinations...")

    t1 = time.time()
    print(f"Finished in {t1-t0:.1f}s")
    
    res_df = pd.DataFrame(results)
    # Sort globally by Sharpe
    res_df = res_df.sort_values('Sharpe', ascending=False)
    
    print("\n=======================================================")
    print(" TOP 30 STRATEGIES ACROSS ALL EMA COMBINATIONS & RRs   ")
    print("=======================================================")
    print(res_df.head(30).to_string(index=False))

if __name__ == '__main__':
    main()
