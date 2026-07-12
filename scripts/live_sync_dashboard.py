import time, json, os
from pathlib import Path

STATUS_PATH = Path("dashboard/public/data/status.json")
SESSION_PATH = Path("agent_memory/session_state.json")
TRADES_PATH = Path("agent_memory/trades_log.jsonl")
DATA_DIR = Path("dashboard/public/data")

def loop():
    print("Starting live sync for dashboard...")
    while True:
        try:
            if not SESSION_PATH.exists():
                time.sleep(5)
                continue
                
            with open(SESSION_PATH, 'r', encoding='utf-8') as f:
                session = json.load(f)
                
            date_str = session.get("date")
            if not date_str:
                time.sleep(5)
                continue
                
            # Update status.json
            if STATUS_PATH.exists():
                with open(STATUS_PATH, 'r', encoding='utf-8') as f:
                    status = json.load(f)
            else:
                status = {}
                
            status["LIVE_SESSION_STATE"] = session
            if "ANALYZED_DATES" not in status:
                status["ANALYZED_DATES"] = []
            if date_str not in status["ANALYZED_DATES"]:
                status["ANALYZED_DATES"].append(date_str)
                status["ANALYZED_DATES"].sort()
                
            # Parse reasoning_log.jsonl and populate ALL_REASONINGS
            all_reasonings = []
            REASONING_PATH = Path("agent_memory/reasoning_log.jsonl")
            if REASONING_PATH.exists():
                with open(REASONING_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                all_reasonings.append(json.loads(line))
                            except: pass
            status["ALL_REASONINGS"] = all_reasonings
            
            all_trades = []
            OPTIMAL_PATH = Path("agent_memory/optimal_backtest_trades.json")
            if OPTIMAL_PATH.exists():
                try:
                    with open(OPTIMAL_PATH, 'r', encoding='utf-8') as f:
                        opts = json.load(f)
                        for o in opts:
                            d = o.get("date", "")
                            if len(d) == 8 and "-" not in d:
                                o["date"] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                        all_trades.extend(opts)
                except:
                    pass
                    
            if TRADES_PATH.exists():
                with open(TRADES_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                trade = json.loads(line)
                                if 'pnl_usd' in trade and 'pnl' not in trade:
                                    trade['pnl'] = trade['pnl_usd']
                                all_trades.append(trade)
                            except:
                                pass
            status["ALL_TRADES"] = all_trades
            
            # Rebuild MOCK_SESSIONS and MOCK_KPI
            groups = {}
            for t in all_trades:
                d = t.get("date")
                if not d: continue
                if d not in groups: groups[d] = []
                groups[d].append(t)
                
            mock_sessions = []
            for d in sorted(groups.keys()):
                day_trades = groups[d]
                wins = len([t for t in day_trades if t.get("pnl", 0) > 0])
                losses = len([t for t in day_trades if t.get("pnl", 0) <= 0])
                pnl = sum(t.get("pnl", 0) for t in day_trades)
                mock_sessions.append({
                    "date": d,
                    "trades": len(day_trades),
                    "wins": wins,
                    "losses": losses,
                    "pnl": pnl,
                    "proposals": len(day_trades)
                })
            status["MOCK_SESSIONS"] = mock_sessions
            status["ALL_PROPOSALS"] = all_trades
            
            temp_path = STATUS_PATH.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2)
            try:
                temp_path.replace(STATUS_PATH)
            except PermissionError:
                with open(STATUS_PATH, 'w', encoding='utf-8') as f:
                    json.dump(status, f, indent=2)
                
            # Create a dummy day file if it doesn't exist so dashboard doesn't 404
            day_file = DATA_DIR / f"{date_str}.json"
            if not day_file.exists():
                dummy_payload = {
                    "date": date_str,
                    "m1_ny": [],
                    "m5_ny": [],
                    "vwap": {},
                    "big_trades": [],
                    "vp": {},
                    "prev_day_vp": {},
                    "dev_va": [],
                    "ib": {"high": session.get("ib_high"), "low": session.get("ib_low")}
                }
                with open(day_file, 'w', encoding='utf-8') as f:
                    json.dump(dummy_payload, f)
                    
            time.sleep(2)
        except Exception as e:
            print(f"Sync error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    loop()
