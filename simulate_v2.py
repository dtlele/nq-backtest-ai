import json
from datetime import datetime

v2_file = r"C:\Users\Mauro\Documents\nq-backtest\dashboard\public\data\v2_proposals.json"
data_file = r"C:\Users\Mauro\Documents\nq-backtest\dashboard\public\data\2025-04-30.json"

with open(v2_file, "r") as f:
    proposals = json.load(f)

import pytz

try:
    with open(data_file, "r") as f:
        daily_data = json.load(f)
        bars = daily_data.get("m5_ny", [])
except Exception as e:
    print(f"Errore caricamento dati: {e}")
    bars = []

ny_tz = pytz.timezone('America/New_York')
for b in bars:
    dt = datetime.fromtimestamp(b["time"], pytz.utc).astimezone(ny_tz)
    b["time_et"] = dt.strftime("%H:%M")

# Dizionario dei bars per tempo et
bar_dict = {b.get("time_et"): b for b in bars}
bar_list = sorted(bars, key=lambda x: x["time"])

wins = 0
losses = 0
total_pnl_pts = 0.0

for p in proposals:
    if p.get("decision") == "trade":
        entry = p.get("entry")
        sl = p.get("stop")
        tp = p.get("target")
        direction = p.get("direction")
        bar_time = p.get("bar_time_et")
        
        if not (entry and sl and tp):
            continue
            
        # Trova indice bar
        idx = -1
        for i, b in enumerate(bar_list):
            if b.get("time_et") == bar_time:
                idx = i
                break
                
        if idx == -1: continue
        
        # Simula dalle barre successive
        result = None
        for b in bar_list[idx+1:]:
            h = b.get("high")
            l = b.get("low")
            
            if direction == "long":
                if l <= sl:
                    result = "loss"
                    total_pnl_pts -= (entry - sl)
                    break
                if h >= tp:
                    result = "win"
                    total_pnl_pts += (tp - entry)
                    break
            elif direction == "short":
                if h >= sl:
                    result = "loss"
                    total_pnl_pts -= (sl - entry)
                    break
                if l <= tp:
                    result = "win"
                    total_pnl_pts += (entry - tp)
                    break
                    
        if result == "win": wins += 1
        elif result == "loss": losses += 1

total_trades = wins + losses
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print(f"Statistiche V2 per 30 Aprile 2025:")
print(f"---------------------------------")
print(f"Totale Trade Simulatili: {total_trades}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"PnL (Punti NQ stima): {total_pnl_pts:.2f} pts")
print(f"PnL ($ 20/pt): ${total_pnl_pts * 20:.2f}")
