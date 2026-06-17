import json
import os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars
from src.risk_manager import calculate_commissions
from src import Bar, NQ_TICK_SIZE

# Simulation config
INSTRUMENT = 'MNQ'
TICK_VALUE = 0.50 # $0.50 per tick for MNQ
TICK_SIZE = 0.25

def simulate_trade(direction, entry_price, stop_price, target_price, entry_time_str, date_str):
    try:
        # Convert timestamp
        entry_time = pd.to_datetime(entry_time_str)
        # Ensure it has UTC timezone
        if entry_time.tzinfo is None:
            entry_time = entry_time.tz_localize('UTC')
        else:
            entry_time = entry_time.tz_convert('UTC')
        entry_time = entry_time.to_pydatetime()
    except Exception as e:
        return {"error": f"invalid_time_format: {e}"}
    
    # Locate data file
    clean_date = date_str.replace('-', '')
    csv_path = f"C:/Users/Mauro/Documents/databento-data/glbx-mdp3-{clean_date}.trades.csv"
    if not os.path.exists(csv_path):
        return {"error": "file_not_found"}
        
    try:
        trades_raw = load_day(csv_path)
        bars = aggregate_to_bars(trades_raw, freq='1min')
    except Exception as e:
        return {"error": f"load_failed: {e}"}
        
    # Filter bars after entry_time
    # bar.timestamp is UTC
    bars_ny = [b for b in bars if b.timestamp >= entry_time]
    if not bars_ny:
        return {"error": f"no_bars_after_entry (entry_time: {entry_time}, first_bar: {bars[0].timestamp if bars else 'none'})"}
        
    # Let's simulate
    contracts = 1 # assume 1 contract for simplicity
    exit_price = None
    exit_reason = None
    exit_bar = None
    
    for i, bar in enumerate(bars_ny):
        is_first = (i == 0)
        
        if direction == 'long':
            # Check target first, to match trade_simulator.py
            if bar.high >= target_price:
                exit_price = target_price
                exit_reason = 'target'
                exit_bar = bar
                break
            if bar.low <= stop_price:
                # In first bar, check if close confirms stop-out to be causality-safe
                if is_first:
                    if bar.close <= stop_price:
                        exit_price = stop_price
                        exit_reason = 'stop'
                        exit_bar = bar
                        break
                else:
                    exit_price = stop_price
                    exit_reason = 'stop'
                    exit_bar = bar
                    break
        else: # short
            if bar.low <= target_price:
                exit_price = target_price
                exit_reason = 'target'
                exit_bar = bar
                break
            if bar.high >= stop_price:
                if is_first:
                    if bar.close >= stop_price:
                        exit_price = stop_price
                        exit_reason = 'stop'
                        exit_bar = bar
                        break
                else:
                    exit_price = stop_price
                    exit_reason = 'stop'
                    exit_bar = bar
                    break
    
    if exit_price is None:
        # EOD close
        exit_bar = bars_ny[-1]
        exit_price = exit_bar.close
        exit_reason = 'eod'
        
    sign = 1 if direction == 'long' else -1
    pnl_ticks = sign * (exit_price - entry_price) / TICK_SIZE
    gross_pnl = pnl_ticks * TICK_VALUE * contracts
    commissions = calculate_commissions(contracts, instrument=INSTRUMENT)
    net_pnl = gross_pnl - commissions
    
    return {
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "exit_time": exit_bar.timestamp.isoformat(),
        "pnl_ticks": pnl_ticks,
        "pnl_usd": net_pnl,
        "is_win": net_pnl > 0
    }

def main():
    vetoes = []
    
    # Load all reasoning logs
    log_files = [
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl.bak_202507',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl.pre_may19_clean',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log_backup.jsonl'
    ]
    
    seen = set()
    for lf in log_files:
        if not os.path.exists(lf): continue
        print(f"Reading {lf}...")
        with open(lf, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                
                # Unique identifier
                date = r.get('date')
                ts = r.get('bar_time_utc') or r.get('timestamp') or r.get('entry_time') or r.get('logged_at')
                if not date or not ts: continue
                key = (date, ts)
                if key in seen: continue
                seen.add(key)
                
                fabio_conf = r.get('fabio_confidence', 0)
                # Check if Fabio wanted to trade (confidence >= 75)
                # and Andrea vetoed
                no_trade_reason = r.get('no_trade_reason') or ''
                is_veto = 'andrea_veto' in no_trade_reason or r.get('andrea_confirmation') is False
                
                if fabio_conf >= 75 and is_veto:
                    entry = r.get('fabio_entry') or r.get('entry')
                    stop = r.get('fabio_stop') or r.get('stop')
                    target = r.get('fabio_target') or r.get('target')
                    direction = r.get('fabio_direction') or r.get('direction')
                    
                    if entry and stop and target and direction and direction != 'none':
                        vetoes.append({
                            "date": date,
                            "timestamp": ts,
                            "direction": direction,
                            "entry": float(entry),
                            "stop": float(stop),
                            "target": float(target),
                            "fabio_reasoning": r.get('fabio_reasoning'),
                            "andrea_reasoning": r.get('andrea_reasoning'),
                            "no_trade_reason": no_trade_reason
                        })
                        
    print(f"Found {len(vetoes)} unique vetoed candidate trades.")
    
    # Now simulate
    results = []
    wins = 0
    losses = 0
    eod = 0
    total_pnl = 0.0
    missing_files = 0
    errors = {}
    
    print("\nSimulating outcomes...")
    for v in vetoes:
        sim = simulate_trade(v['direction'], v['entry'], v['stop'], v['target'], v['timestamp'], v['date'])
        if not sim:
            continue
        if "error" in sim:
            err = sim["error"]
            if err == "file_not_found":
                missing_files += 1
            else:
                # Group other errors
                err_type = err.split(':')[0]
                errors[err_type] = errors.get(err_type, 0) + 1
            continue
            
        v['sim_exit_reason'] = sim['exit_reason']
        v['sim_pnl_usd'] = sim['pnl_usd']
        v['sim_is_win'] = sim['is_win']
        v['sim_exit_price'] = sim['exit_price']
        
        total_pnl += sim['pnl_usd']
        if sim['exit_reason'] == 'target':
            wins += 1
        elif sim['exit_reason'] == 'stop':
            losses += 1
        elif sim['exit_reason'] == 'eod':
            eod += 1
            if sim['is_win']:
                wins += 1
            else:
                losses += 1
                
        results.append(v)
        
    print(f"\nSimulation Results of Vetoed Trades:")
    print(f"Total simulated vetoed trades: {len(results)}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"EOD exits: {eod}")
    win_rate = (wins / len(results) * 100) if results else 0
    print(f"Win Rate of vetoed trades: {win_rate:.2f}%")
    print(f"Net PnL missed (total of vetoed trades): ${total_pnl:.2f}")
    print(f"Missing data files: {missing_files}")
    print(f"Errors summary: {errors}")
    
    # Save detail results
    with open('scratch/veto_simulation_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    # Write a summary report
    summary = []
    summary.append("# 📊 Analisi di Impatto del Veto di Andrea (Andrea Cimi Agent)")
    summary.append(f"Questa analisi ha simulato il comportamento storico dei trade che **Fabio voleva aprire** (confidenza >= 75%) ma che **Andrea ha bloccato col suo Veto** (confidenza < 40 o conferma = False).\n")
    summary.append(f"### 📈 Metriche Generali")
    summary.append(f"- **Trade Totali Analizzati (con dati storici disponibili):** {len(results)}")
    summary.append(f"- **Trade Vincenti (Hit Target o Chiusura EOD in profitto):** {wins}")
    summary.append(f"- **Trade Perdenti (Hit Stop o Chiusura EOD in perdita):** {losses}")
    summary.append(f"- **Win Rate dei trade scartati:** {win_rate:.2f}%")
    summary.append(f"- **PnL Netto Perso (Valore dei trade scartati):** **${total_pnl:.2f}** (su base 1 contratto MNQ)")
    summary.append(f"\n> **IMPATTO:** Se il PnL Netto Perso è **positivo**, significa che Andrea ci è costata denaro facendoci perdere trade vincenti. Se è **negativo**, Andrea ci ha salvato da perdite nette, confermando l'utilità del filtro.")
    
    summary.append("\n### 📋 Dettaglio dei Trade Scartati e relativo Outcome Reale")
    for r in results[:30]:
        outcome_icon = "✅ (WIN)" if r['sim_is_win'] else "❌ (LOSS)"
        summary.append(f"#### Data: {r['date']} alle {r['timestamp']}")
        summary.append(f"- **Setup proposto da Fabio:** {r['direction'].upper()} a {r['entry']} | Stop: {r['stop']} | Target: {r['target']}")
        summary.append(f"- **Ragione del Veto di Andrea:** *{r['no_trade_reason']}*")
        summary.append(f"- **Esito Reale nella simulazione:** {outcome_icon} | Uscita a {r['sim_exit_price']} per {r['sim_exit_reason']} | PnL: **${r['sim_pnl_usd']:.2f}**")
        summary.append("")
        
    with open('scratch/andrea_impact_report.md', 'w', encoding='utf-8') as f:
        f.write("\n".join(summary))
        
if __name__ == '__main__':
    main()
