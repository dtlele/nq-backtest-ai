import json
from pathlib import Path

def analyze_log(log_path, desc):
    path = Path(log_path)
    if not path.exists():
        print(f"File not found: {log_path}")
        return
    
    trades = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    trades.append(json.loads(line))
                except:
                    pass
    
    total_trades = len(trades)
    targets = sum(1 for t in trades if t.get('exit_reason') == 'target')
    stops = sum(1 for t in trades if t.get('exit_reason') == 'stop')
    pnl = sum(t.get('pnl_usd', 0) for t in trades)
    
    print(f"\n--- {desc} ---")
    print(f"Total Trades: {total_trades}")
    print(f"Targets: {targets} | Stops: {stops}")
    print(f"Total PnL: ${pnl:.2f}")
    
    for t in trades[:5]:
        print(f"  {t.get('date')} {t.get('entry_time')} | {t.get('direction').upper()} | {t.get('setup_type')} | Exit: {t.get('exit_reason')} | PnL: ${t.get('pnl_usd', 0):.2f}")
        print(f"    Fabio Reason: {t.get('fabio_reasoning', '')[:100]}...")

analyze_log('agent_memory/trades_log.jsonl', 'CURRENT RUN (Modular Prompt)')
analyze_log('agent_memory/trades_log_gemini_feb_week1.jsonl', 'PREVIOUS GEMINI RUN (Feb Week 1)')
analyze_log('agent_memory/trades_log_ds_feb_ultimate_v2.jsonl', 'PREVIOUS DEEPSEEK RUN (Feb Ultimate V2)')
