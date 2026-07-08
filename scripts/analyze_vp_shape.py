import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import datetime

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, get_session_label

ET = pytz.timezone("America/New_York")

def simulate_mfe(bars, entry_idx, direction):
    entry_price = bars[entry_idx].close
    mfe = 0.0
    for i in range(entry_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        if t_et.hour >= 16: break
            
        if direction == "long":
            ext = bar.high - entry_price
        else:
            ext = entry_price - bar.low
            
        if ext > mfe: mfe = ext
    return mfe

def calc_vp_shape(bars, up_to_idx):
    price_vol = {}
    day_high = -float('inf')
    day_low = float('inf')
    
    for i in range(up_to_idx):
        b = bars[i]
        t_et = b.timestamp.astimezone(ET)
        if t_et.hour < 9 or (t_et.hour == 9 and t_et.minute < 30):
            continue 
            
        h, l = b.high, b.low
        if h > day_high: day_high = h
        if l < day_low: day_low = l
        
        # Invece del volume (che manca in MockBar), usiamo il tempo (TPO Profile - Standard Market Profile)
        for p in range(int(l), int(h) + 1):
            price_vol[p] = price_vol.get(p, 0) + 1
                
    if not price_vol: return "Unknown", 0, 0, 0
    
    poc = max(price_vol.items(), key=lambda x: x[1])[0]
    range_total = day_high - day_low
    if range_total == 0: return "D-shape (Balanced)", poc, day_high, day_low
    
    poc_pct = (poc - day_low) / range_total
    
    if poc_pct >= 0.66:
        shape = "p-shape (Top Heavy)"
    elif poc_pct <= 0.33:
        shape = "b-shape (Bottom Heavy)"
    else:
        shape = "D-shape (Balanced)"
        
    return shape, poc, day_high, day_low

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates: get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        s25 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        s26 = json.load(f)
    seqs_combined = s25 + s26

    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        v2_rules = json.load(f)["v2_case_a_coarse_sessions"]["rules"]

    results = []

    for s in seqs_combined:
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        # Filtro Livello 1 (V2)
        rule = v2_rules.get(pattern)
        if not rule: continue
        dt_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
        if dt_obj.strftime("%A") not in rule["days"]: continue
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        if not (9*60+30 <= t_val < 16*60): continue
        if get_session_label(t_val) not in rule["sessions"]: continue
        if rule.get("exclude_10am", False) and (9*60+55 <= t_val <= 10*60+5): continue
        
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            if b.timestamp.astimezone(ET).strftime("%H:%M") == time_str:
                idx_T = i; break
        if idx_T < 30: continue
            
        # Filtro Livello 2 (10m Buildup)
        prior_10 = bars[idx_T-10 : idx_T]
        p_chg = prior_10[-1].close - prior_10[0].open
        v10 = False
        if pattern == "absorb_long" and p_chg >= -10: v10 = True 
        elif pattern == "trend_long" and p_chg > 0: v10 = True 
        elif pattern == "absorb_short" and p_chg <= 10: v10 = True 
        elif pattern == "trend_short" and p_chg < 0: v10 = True 
        if not v10: continue
            
        # Filtro Livello 3 (30m Extension)
        prior_30 = bars[idx_T-30 : idx_T]
        sma_30 = sum(b.close for b in prior_30) / 30.0
        dist_sma = bars[idx_T].close - sma_30
        if pattern == "trend_long" and dist_sma < 35: continue
        if pattern == "absorb_short" and dist_sma > -45: continue
            
        direction = "long" if "long" in pattern else "short"
        
        # 1. Calcolo MFE (Estensione Massima)
        mfe = simulate_mfe(bars, idx_T, direction)
        
        # 2. Calcolo VP Shape (Dall'apertura al momento del trade)
        vp_shape, poc, d_high, d_low = calc_vp_shape(bars, idx_T)
        
        results.append({
            "pattern": pattern,
            "vp_shape": vp_shape,
            "mfe": mfe,
            "poc_dist": bars[idx_T].close - poc  # Distanza del trade dal POC
        })

    df = pd.DataFrame(results)
    
    print("\n=======================================================")
    print("CLASSIFICAZIONE VP SHAPE & ESTENSIONE TRADE")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        print(f"--- SETUP: {pat.upper()} (N={len(sub)}) ---")
        print(f"  Estensione Max Media (MFE prima delle 16:00): {sub['mfe'].mean():.1f} punti")
        
        shapes = sub["vp_shape"].value_counts(normalize=True) * 100
        print("  Distribuzione Forma Giornata (VP Shape):")
        for k, v in shapes.items():
            print(f"    - {k}: {v:.1f}% dei trade")
            
        print(f"  Distanza media dal POC: {sub['poc_dist'].mean():+.1f} punti\n")

if __name__ == "__main__": main()
