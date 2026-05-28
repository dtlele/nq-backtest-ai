import json
from pathlib import Path

# Paths to past logs
LOG_DIR = Path("C:/Users/Mauro/Documents/nq-backtest/agent_memory")
LOG_FILES = [
    ("Gemini Week 1 (Positive)", LOG_DIR / "trades_log_gemini_feb_week1.jsonl"),
    ("DS Restrictive", LOG_DIR / "trades_log_ds_feb_restrictive.jsonl"),
    ("DS Pure No Money Mgmt (56 Trades)", LOG_DIR / "trades_log_ds_feb_no_money_mgmt.jsonl")
]

def analyze_file(name, path):
    if not path.exists():
        print(f"File not found: {path}")
        return
    
    trades = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    trades.append(json.loads(line))
                except Exception:
                    pass
                
    print(f"\n=======================================================")
    print(f"ANALISI STATISTICA: {name} ({len(trades)} trade)")
    print(f"=======================================================")
    
    # Group by setup_type
    setups = {}
    for t in trades:
        st = t.get("setup_type", "none")
        conf = t.get("final_confidence", t.get("confidence", 0))
        pnl = t.get("pnl_usd", 0.0)
        exit_r = t.get("exit_reason", "none")
        
        setups.setdefault(st, []).append({
            "conf": conf,
            "pnl": pnl,
            "exit": exit_r
        })
        
    for st, records in setups.items():
        print(f"\n-> Setup: {st.upper()} ({len(records)} operazioni)")
        # Sort by confidence
        records.sort(key=lambda x: x["conf"])
        
        # Calculate stats per confidence brackets
        brackets = {}
        for r in records:
            c = r["conf"]
            # group by brackets: <70, 70-79, >=80
            if c < 70:
                b_name = "< 70"
            elif 70 <= c < 80:
                b_name = "70 - 79"
            else:
                b_name = ">= 80"
            brackets.setdefault(b_name, []).append(r)
            
        for b_name, b_records in sorted(brackets.items()):
            wins = sum(1 for r in b_records if r["pnl"] > 0)
            losses = sum(1 for r in b_records if r["pnl"] <= 0)
            tot_pnl = sum(r["pnl"] for r in b_records)
            win_rate = (wins / len(b_records)) * 100 if len(b_records) > 0 else 0
            print(f"  * Confidenza {b_name}: {len(b_records)} trade | WR: {win_rate:.1f}% | P&L: {tot_pnl:+.2f}$  (Target: {wins}, Stop: {losses})")

if __name__ == "__main__":
    for name, path in LOG_FILES:
        analyze_file(name, path)
