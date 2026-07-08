import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

from src.data_loader import list_data_files, load_day
from src.bar_aggregator import aggregate_to_bars
from src.bt_narrative_engine import extract_big_trade_nodes
from src.agents.bt_narrative_agent import analyze_bt_node

def filter_ny_window(bars):
    return [b for b in bars if 9 <= b.timestamp.hour < 16 or (b.timestamp.hour == 16 and b.timestamp.minute == 0)]

LOG_FILE = Path(__file__).parent / 'agent_memory' / 'bt_narrative_log.jsonl'

def main():
    parser = argparse.ArgumentParser(description="Big Trade Node-to-Node Narrative Backtester")
    parser.add_argument('--start-date', type=str, required=True, help="YYYYMMDD")
    parser.add_argument('--end-date', type=str, required=True, help="YYYYMMDD")
    parser.add_argument('--data-dir', type=str, required=True, help="Path to databento-data")
    args = parser.parse_args()

    files = list_data_files(args.data_dir)
    dates_to_run = []
    for f in files:
        # Example filename: glbx-mdp3-20251023.trades.csv
        basename = os.path.basename(f)
        parts = basename.split('-')
        if len(parts) >= 3:
            date_part = parts[2].split('.')[0]
            if args.start_date <= date_part <= args.end_date:
                dates_to_run.append((date_part, f))
    
    dates_to_run.sort()
    
    if not dates_to_run:
        print("No dates found in the specified range.")
        return

    # Ensure log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear logs for the dates we are about to run
    date_strings = [d[0] for d in dates_to_run]
    if LOG_FILE.exists():
        lines_to_keep = []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get('date') not in date_strings:
                            lines_to_keep.append(line)
                    except:
                        pass
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines_to_keep)
            
    for date_str, file_path in dates_to_run:
        if not Path(file_path).exists():
            print(f"Skipping {date_str}: file not found.")
            continue
            
        print(f"\nProcessing {date_str} (Node-to-Node)...")
        
        from src.candidate_detector import detect_m1_candidates
        from src.session_context import build_session_context
        
        trades_raw = load_day(str(file_path))
        m1_bars_all = aggregate_to_bars(trades_raw, freq='1min')
        m1_bars = filter_ny_window(m1_bars_all)
        
        # Build minimal ctx
        ctx = build_session_context(date_str, m1_bars, vp=None)
        
        # Populate big_trades for each bar using candidate_detector
        for idx, bar in enumerate(m1_bars):
            m1_history = m1_bars[:idx]
            detect_m1_candidates(bar, [], ctx, m1_history=m1_history)
        
        if not m1_bars:
            print("  No M1 bars generated.")
            continue
            
        # Extract Big Trade Nodes
        nodes = extract_big_trade_nodes(m1_bars)
        print(f"  Found {len(nodes)} Big Trade Nodes.")
        
        for idx, node in enumerate(nodes):
            print(f"  [NODE {idx+1}/{len(nodes)}] {node.current_time.strftime('%H:%M')} ET | Price: {node.current_price:.2f}")
            
            # Analyze
            analysis = analyze_bt_node(node)
            
            # Log
            log_entry = {
                "date": date_str,
                "node_index": idx,
                "time_utc": node.current_time.isoformat(),
                "time_et": node.current_time.strftime('%H:%M'),
                "price": node.current_price,
                "trades": [{"side": t.side, "size": t.size, "price": t.price} for t in node.current_trades],
                "elapsed_mins": node.elapsed_mins,
                "price_change": node.price_change,
                "cumulative_delta": node.cumulative_delta,
                "max_excursion": node.max_excursion,
                "min_excursion": node.min_excursion,
                "narrative": analysis.get("narrative", ""),
                "classification": analysis.get("classification", ""),
                "entry_decision": analysis.get("entry_decision", "none"),
                "confidence": analysis.get("confidence", 0),
                "stop_loss": analysis.get("stop_loss"),
                "logged_at": datetime.now(timezone.utc).isoformat()
            }
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
            print(f"    -> {analysis.get('classification')} | Action: {analysis.get('entry_decision')} | Conf: {analysis.get('confidence')}")
            
if __name__ == '__main__':
    main()
