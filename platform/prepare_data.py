import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "agent_memory" / "reasoning_log.jsonl"
TRADES_FILE = BASE_DIR / "agent_memory" / "trades_log.jsonl"
OUTPUT_FILE = BASE_DIR / "platform" / "static" / "data.json"

def prepare_data():
    candidates_dict = {}
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    c = json.loads(line)
                    candidates_dict[c.get("bar_time_utc")] = c
    candidates = list(candidates_dict.values())
    
    trades_dict = {}
    if TRADES_FILE.exists():
        with open(TRADES_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    t = json.loads(line)
                    trades_dict[t.get("entry_time")] = t
    trades = list(trades_dict.values())
                    
    # Group candidates by date
    days = {}
    for c in candidates:
        d = c["date"]
        if d not in days:
            days[d] = {"date": d, "candidates": [], "trades": []}
        days[d]["candidates"].append(c)
        
    for t in trades:
        d = t.get("date")
        if d in days:
            days[d]["trades"].append(t)
            # Find the corresponding candidate and update it
            for c in days[d]["candidates"]:
                if c.get("bar_time_utc") == t.get("entry_time"):
                    c["decision"] = "trade"
                    c["trade_direction"] = t.get("direction")
                    c["trade_pnl_ticks"] = t.get("pnl_ticks")
                    c["trade_setup"] = t.get("setup_type")
                    c["trade_entry"] = t.get("entry")
                    c["trade_stop"] = t.get("stop")
                    c["trade_target"] = t.get("target")
                    break
            
    # Calculate PNL from pre-calculated pnl_usd in trades
    total_pnl_usd = sum(float(t.get("pnl_usd", 0) or 0) for t in trades)
            
    data = {
        "days": list(days.values()),
        "summary": {
            "total_candidates": len(candidates),
            "total_trades": len(trades),
            "pnl": total_pnl_usd,
            "win_rate": (sum(1 for t in trades if float(t.get("pnl_ticks", 0) or 0) > 0) / len(trades) * 100) if trades else 0
        }
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"Data prepared: {len(candidates)} candidates, {len(trades)} trades across {len(days)} days.")

if __name__ == "__main__":
    prepare_data()
