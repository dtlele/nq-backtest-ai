import json
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))

from build_knowledge_v2 import nlm_ask, nlm_use, NOTEBOOKS

TRADES_LOG = Path(r'c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl')

def run_audit():
    losses = []
    with open(TRADES_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            trade = json.loads(line)
            # Filter: Only August 2025 and only Stop exits
            if trade.get('exit_reason') == 'stop' and trade.get('date', '').startswith('2025-08'):
                losses.append(trade)
    
    print(f"Found {len(losses)} losing trades in AUGUST to audit.", flush=True)
    
    # Load existing results if any (Resume logic)
    results_path = Path('agent_memory/loss_audit_results.json')
    if results_path.exists():
        with open(results_path, 'r', encoding='utf-8') as f:
            audit_results = json.load(f)
    else:
        audit_results = []
    
    already_audited = { (t['trade']['date'], t['trade']['entry_time']) for t in audit_results }
    
    for trade in losses:
        date = trade['date']
        time = trade['entry_time']
        direction = trade['direction']
        reasoning = trade['fabio_reasoning']
        
        if (date, time) in already_audited:
            print(f"Skipping {date} {time} (Already audited)", flush=True)
            continue
            
        print(f"Auditing {date} {time} {direction}...", flush=True)
        
        # Inquiry for Fabio
        question = f"""
        POST-MORTEM AUDIT - TRADE LOSS on {date} at {time} ({direction})
        
        Original Reasoning: {reasoning}
        Result: Stopped out with PnL: {trade['pnl_usd']} USD.
        
        Based on your institutional rules (Sweep Defense, Surgical Stop, Structural Reset):
        1. Was the stop placement too tight (rumore) or was the thesis invalid (absorption)?
        2. Could we have avoided this entry? Was there a 'Failed Auction' or 'Imbalance Defense' failure we ignored?
        3. If the thesis was correct but we were stopped, where was the TRUE institutional wall?
        """
        
        try:
            print(f"  Querying Fabio...", flush=True)
            nlm_use(NOTEBOOKS['fabio'])
            fabio_answer = nlm_ask(question)
            
            print(f"  Querying Andrea...", flush=True)
            nlm_use(NOTEBOOKS['andrea'])
            andrea_answer = nlm_ask(question)
            
            audit_results.append({
                'trade': trade,
                'fabio_audit': fabio_answer,
                'andrea_audit': andrea_answer
            })
            
            # Save partial result (Save progress)
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(audit_results, f, indent=2)
                
        except Exception as e:
            print(f"ERROR on {date} {time}: {e}", flush=True)
            continue

    print("Audit complete.", flush=True)

if __name__ == "__main__":
    run_audit()
