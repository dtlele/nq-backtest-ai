#!/usr/bin/env python3
"""
Analizza il trailing stop dei 2 trade vincenti V4 Flash usando i M1 data.

Legge i trade dal log e ricostruisce l'attività M1 (gestita da APM)
per capire come il trailing stop si è mosso durante la vita del trade.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import re
import csv

# Mappa dei trade da analizzare
TRADES_TO_ANALYZE = [
    {
        'date': '2025-02-04',
        'direction': 'long',
        'entry_price': 21633.50,
        'stop_initial': None,  # Sarà letto dal log
        'target': None,  # Sarà letto dal log
        'exit_time_utc': '14:43',  # 14:43 UTC exit
        'pnl_usd': 53.88,
        'exit_reason': 'trailing_stop',
    },
    {
        'date': '2025-02-06',
        'direction': 'long',
        'entry_price': 21763.25,
        'stop_initial': None,
        'target': None,
        'exit_time_utc': '15:11',
        'pnl_usd': 42.26,
        'exit_reason': 'trailing_stop',
    },
]

# Cerca le M1 trades data files (Databento)
DATA_DIR = Path("C:/Users/Mauro/Documents/databento-data")

def load_m1_trades_for_day(date_str):
    """Carica le M1 trades per una data specifica dal file Databento aggregato."""
    date_compact = date_str.replace("-", "")
    fname = f"glbx-mdp3-{date_compact}.trades.csv"
    fpath = DATA_DIR / fname
    if not fpath.exists():
        return None
    print(f"  M1 data file: {fpath.name} ({fpath.stat().st_size / 1024 / 1024:.1f} MB)")
    return fpath

def parse_timestamp(ts_str):
    """Parse a timestamp string to datetime."""
    # Vari formati: 2025-02-04T20:07:00+00:00
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            pass
    return None

def analyze_trade_trailing(trade_info, log_path):
    """Analizza il trailing stop di un singolo trade leggendo il log."""
    print(f"\n{'='*80}")
    print(f"TRADE: {trade_info['date']} {trade_info['direction'].upper()} @ {trade_info['entry_price']}")
    print(f"  Exit: {trade_info['exit_time_utc']} UTC, PnL: ${trade_info['pnl_usd']:.2f}")
    print(f"{'='*80}")

    # Leggi il log
    if not os.path.exists(log_path):
        print(f"  Log non trovato: {log_path}")
        return None

    # Trova le MANAGEMENT events per questa data
    management_events = []
    with open(log_path) as f:
        for line in f:
            if trade_info['date'] not in line:
                continue
            if 'MANAGEMENT' in line or 'Active LONG' in line or 'Active SHORT' in line:
                # Estrai timestamp e decision
                m = re.search(r'(\d{2}:\d{2}) UTC', line)
                ts_str = m.group(1) if m else '??'
                decision = 'HOLD'
                if 'TRAIL' in line: decision = 'TRAIL'
                if 'stop' in line.lower() and 'STOP WICK' not in line: decision = 'STOP'
                if 'STOP WICK' in line: decision = 'STOP_WICK'
                # Reasoning
                reason = ''
                m2 = re.search(r'Reasoning:\s*([^|\n]+)', line)
                if m2: reason = m2.group(1).strip()[:120]

                # Contesto long/short
                ctx = 'LONG' if 'Active LONG' in line else 'SHORT'

                management_events.append({
                    'time': ts_str,
                    'decision': decision,
                    'reasoning': reason,
                    'context': ctx,
                })

    # Filtra per LONG/SHORT e timeframe del trade
    relevant_events = [e for e in management_events
                      if e['context'] == trade_info['direction'].upper()]

    print(f"\n  MANAGEMENT EVENTS ({len(relevant_events)} totali):")
    for e in relevant_events:
        print(f"    {e['time']} UTC: {e['decision']:<12} | {e['reasoning']}")

    # Conta decision types
    from collections import Counter
    decisions = Counter(e['decision'] for e in relevant_events)
    print(f"\n  Decision distribution:")
    for d, c in decisions.most_common():
        print(f"    {d}: {c}")

    return relevant_events

def analyze_m1_price_path(trade_info, m1_file):
    """Analizza il path M1 del prezzo durante il trade."""
    print(f"\n  M1 PRICE PATH:")
    print(f"  (caricamento {m1_file.name}, solo lettura parziale)")

    # Per ora solo stat descrittive del file
    file_size = m1_file.stat().st_size / 1024 / 1024
    print(f"    File size: {file_size:.1f} MB")

    # Conta quante righe (trades) - stima
    with open(m1_file, 'rb') as f:
        # Conta solo i newline per velocità
        line_count = sum(1 for _ in f)
    print(f"    Trade records: ~{line_count}")

    return line_count

def main():
    LOG_PATH = "output/test_v4flash_v8bweek_20260802_1218.log"

    print("="*80)
    print("ANALISI TRAILING STOP M1 - TRADE VINCENTI V4 FLASH (4-11 Feb 2025)")
    print("="*80)

    for trade in TRADES_TO_ANALYZE:
        # 1. Analizza MANAGEMENT events dal log
        events = analyze_trade_trailing(trade, LOG_PATH)

        # 2. Carica M1 data file
        m1_file = load_m1_trades_for_day(trade['date'])
        if m1_file:
            analyze_m1_price_path(trade, m1_file)

    print()
    print("="*80)
    print("CONCLUSIONI")
    print("="*80)
    print("I 2 trade vincenti (+$96.14 totale) sono stati gestiti dal trailing stop")
    print("attraverso il sistema APM (Active Position Manager) che gira su M1 bars.")
    print()
    print("Prossimi step per analisi M1 dettagliata:")
    print("  1. Verificare i prezzi M1 esatti al momento del trail decision")
    print("  2. Ricostruire il path del prezzo M1 per minuto")
    print("  3. Confermare che il trailing lock al 50% (1.5R) sia scattato")
    print("  4. Verificare timing del 75% lock al 2.5R")
    print()
    print("Comando per analisi M1 dettagliata (se servono i prezzi M1):")
    print("  python -c \"import pandas as pd; df = pd.read_csv('glbx-mdp3-20250204.trades.csv'); ...\"")

if __name__ == "__main__":
    main()
