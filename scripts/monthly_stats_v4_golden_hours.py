import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import datetime

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr

ET = pytz.timezone("America/New_York")

def simulate_trade(bars, entry_idx, direction, sl, tp, delay_minutes=0, base_contracts=2.5):
    start_idx = min(entry_idx + delay_minutes, len(bars) - 1)
    entry_price = bars[start_idx].close
    outcome = None
    pnl_pts = 0.0
    
    for i in range(start_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if t_et.hour == 16 and t_et.minute >= 55:
            outcome = "eod"
            pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
            break
            
        if direction == "long":
            if bar.low <= entry_price - sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.high >= entry_price + tp + 0.25:
                pnl_pts = tp; outcome = "win"; break
        else:
            if bar.high >= entry_price + sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.low <= entry_price - tp - 0.25:
                pnl_pts = tp; outcome = "win"; break
                
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates: get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026

    low_vol_setups = {
        "trend_long": {"direction": "long", "sl": 39.0, "tp": 120.0},
        "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
        "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
        "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "trend_long": {"direction": "long", "sl": 22.0, "tp": 113.0},
        "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
        "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
        "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
    }

    results = []

    for s in seqs_combined:
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        dt_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        
        valid_time = False
        if (h == 9 and m >= 30) or (h == 12):
            valid_time = True
            
        if 9*60+55 <= t_val <= 10*60+5:
            valid_time = False
            
        if not valid_time:
            continue
            
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            if b.timestamp.astimezone(ET).strftime("%H:%M") == time_str:
                idx_T = i; break
        if idx_T < 30: continue
            
        prior_10 = bars[idx_T-10 : idx_T]
        price_change_10 = prior_10[-1].close - prior_10[0].open
        valid_10m = False
        if pattern == "absorb_long" and price_change_10 >= -10: valid_10m = True 
        elif pattern == "trend_long" and price_change_10 > 0: valid_10m = True 
        elif pattern == "absorb_short" and price_change_10 <= 10: valid_10m = True 
        elif pattern == "trend_short" and price_change_10 < 0: valid_10m = True 
        if not valid_10m: continue
            
        prior_30 = bars[idx_T-30 : idx_T]
        sma_30 = sum(b.close for b in prior_30) / 30.0
        dist_sma = bars[idx_T].close - sma_30
        if pattern == "trend_long" and dist_sma < 35: continue
        if pattern == "absorb_short" and dist_sma > -45: continue
        
        delay = 1 if pattern == "trend_short" else 0
        pnl, out = simulate_trade(bars, idx_T, direction, setup_info["sl"], setup_info["tp"], delay_minutes=delay, base_contracts=2.5)
        
        month_str = dt_obj.strftime("%Y-%m")
        results.append({"month": month_str, "pnl": pnl, "out": out})

    df = pd.DataFrame(results)
    df['cum_pnl'] = df['pnl'].cumsum()
    df['peak'] = df['cum_pnl'].cummax()
    df['drawdown'] = df['peak'] - df['cum_pnl']
    exact_dd = df['drawdown'].max()
    
    print("\n=======================================================")
    print("STATISTICHE MENSILI - 'GOLDEN HOURS' (09:30-10:00 & 12:00-13:00)")
    print("Account: Prop Firm $50K | Size: 2.5 Mini NQ (25 Micro)")
    print(f"MAX DRAWDOWN STORICO (Trade-by-Trade): ${exact_dd:,.2f}")
    print("=======================================================\n")
    
    monthly = df.groupby('month').agg(
        Trades=('pnl', 'count'),
        Net_PnL=('pnl', 'sum'),
        Win_Rate=('out', lambda x: (x == 'win').mean() * 100)
    ).round(2)
    
    monthly['Cum_PnL'] = monthly['Net_PnL'].cumsum()
    monthly['Peak'] = monthly['Cum_PnL'].cummax()
    monthly['Drawdown'] = monthly['Peak'] - monthly['Cum_PnL']
    
    print(monthly.to_string())
    
    total_pnl = monthly['Net_PnL'].sum()
    avg_month = monthly['Net_PnL'].mean()
    win_months = (monthly['Net_PnL'] > 0).sum()
    loss_months = (monthly['Net_PnL'] < 0).sum()
    
    gw = sum(p for p in df["pnl"] if p > 0)
    gl = abs(sum(p for p in df["pnl"] if p < 0))
    pf = gw/gl if gl > 0 else float('inf')
    
    print("\n--- SOMMARIO ---")
    print(f"Trade Totali (18 Mesi):          {len(df)}")
    print(f"Profit Factor Globale:           {pf:.2f}")
    print(f"Win Rate Globale:                {(df['out'] == 'win').mean() * 100:.1f}%")
    print(f"Profitto Totale Netto:           ${total_pnl:,.2f}")
    print(f"Profitto Medio Mensile:          ${avg_month:,.2f}")
    print(f"Mesi in Profitto vs Perdita:     {win_months} Vincenti / {loss_months} Perdenti")
    print(f"Max Drawdown Mensile Globale:    ${monthly['Drawdown'].max():,.2f}")

    import numpy as np
    pnls = df['pnl'].tolist()
    N_SIM = 10000
    max_dds = []
    
    for _ in range(N_SIM):
        shuffled = np.random.permutation(pnls)
        cum = np.cumsum(shuffled)
        peaks = np.maximum.accumulate(cum)
        dds = peaks - cum
        max_dds.append(np.max(dds))
        
    max_dds = np.array(max_dds)
    p50 = np.percentile(max_dds, 50)
    p95 = np.percentile(max_dds, 95)
    p99 = np.percentile(max_dds, 99)
    prob_fail = np.mean(max_dds >= 2500.0) * 100
    
    print("\n=======================================================")
    print("MONTECARLO STRESS TEST (10.000 Simulazioni - Size 2.5)")
    print("=======================================================\n")
    print(f"Drawdown Mediano (50% dei casi): ${p50:,.2f}")
    print(f"Drawdown 95° Percentile:         ${p95:,.2f}")
    print(f"Drawdown 99° Percentile:         ${p99:,.2f} (Peggiore dei casi)")
    print(f"\nProbabilita' di bruciare il conto Prop ($2.500 Limit): {prob_fail:.2f}%")

if __name__ == "__main__": main()
