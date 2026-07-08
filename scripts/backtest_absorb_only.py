import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import datetime
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr, get_session_label

ET = pytz.timezone("America/New_York")

def simulate_trade(bars, entry_idx, direction, sl, tp, base_contracts=2.5):
    # Simuliamo l'entrata esatta alla chiusura della candela M1 (l'ipotesi più conservativa)
    start_idx = entry_idx
    # Simulazione Tick-by-Tick: L'algoritmo rileva l'assorbimento nel vivo della candela.
    # Per il Long entriamo quasi sul minimo assoluto (High/Low) + 1 punto di latenza
    if direction == "long":
        entry_price = bars[start_idx].low + 1.0
    else:
        entry_price = bars[start_idx].high - 1.0
        
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

    # REGOLE V3 (V2 Caso A) per mappare i giorni/orari migliori
    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        v2_rules_a = json.load(f)["v2_case_a_coarse_sessions"]["rules"]

    low_vol_setups = {
        "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
        "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
        "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
    }

    results = []

    for s in seqs_combined:
        pattern = s["seq_pattern"]
        if pattern not in ["absorb_long", "absorb_short"]: continue # SOLO ABSORB
        
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        
        rule = v2_rules_a.get(pattern)
        if not rule: continue
        
        dt_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
        if dt_obj.strftime("%A") not in rule["days"]: continue
        
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        
        if not (9*60+30 <= t_val < 16*60): continue
        if get_session_label(t_val) not in rule["sessions"]: continue
        if rule.get("exclude_10am", False) and (9*60+55 <= t_val <= 10*60+5): continue
            
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
            
        # Filtri 10m/30m Level 3
        prior_10 = bars[idx_T-10 : idx_T]
        price_change_10 = prior_10[-1].close - prior_10[0].open
        if pattern == "absorb_long" and price_change_10 < -10: continue
        if pattern == "absorb_short" and price_change_10 > 10: continue
            
        prior_30 = bars[idx_T-30 : idx_T]
        sma_30 = sum(b.close for b in prior_30) / 30.0
        dist_sma = bars[idx_T].close - sma_30
        if pattern == "absorb_short" and dist_sma > -45: continue
        
        pnl, out = simulate_trade(bars, idx_T, direction, setup_info["sl"], setup_info["tp"], base_contracts=2.5)
        
        month_str = dt_obj.strftime("%Y-%m")
        results.append({"month": month_str, "pattern": pattern, "pnl": pnl, "out": out})

    df = pd.DataFrame(results)
    if df.empty:
        print("Nessun trade trovato.")
        return

    df['cum_pnl'] = df['pnl'].cumsum()
    df['peak'] = df['cum_pnl'].cummax()
    df['drawdown'] = df['peak'] - df['cum_pnl']
    exact_dd = df['drawdown'].max()
    
    print("\n=======================================================")
    print("BACKTEST ISOLATO: ESCLUSIVAMENTE 'ABSORB' (M1 Entry)")
    print("Logica: Absorb Long & Absorb Short | Master Strategy V3")
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
    gw = sum(p for p in df["pnl"] if p > 0)
    gl = abs(sum(p for p in df["pnl"] if p < 0))
    pf = gw/gl if gl > 0 else float('inf')
    
    print("\n--- SOMMARIO (SOLO ABSORB) ---")
    print(f"Trade Totali:                    {len(df)}")
    print(f"Profit Factor Globale:           {pf:.2f}")
    print(f"Win Rate Globale:                {(df['out'] == 'win').mean() * 100:.1f}%")
    print(f"Profitto Totale Netto:           ${total_pnl:,.2f}")
    
    pattern_breakdown = df.groupby('pattern').agg(
        Trades=('pnl', 'count'), PnL=('pnl', 'sum'), WR=('out', lambda x: (x=='win').mean()*100)
    ).round(2)
    print("\n--- BREAKDOWN PER SETUP ---")
    print(pattern_breakdown.to_string())

if __name__ == "__main__": main()
