import json

def find_bar(filepath, date, bar_time, encoding='utf-8-sig'):
    try:
        lines = open(filepath, encoding=encoding).readlines()
    except:
        lines = open(filepath, encoding='utf-8').readlines()
    for l in lines:
        if not l.strip():
            continue
        try:
            d = json.loads(l)
            if d.get('date') == date and d.get('bar_time_et') == bar_time:
                return d
        except:
            pass
    return None

TARGET_BARS = ['09:48', '09:55', '09:59', '10:32']
DATE = '2025-03-10'

current_log = 'agent_memory/reasoning_log.jsonl'
backup_log = 'agent_memory/reasoning_log_backup.jsonl'

MARKET_KEYS = [
    'bar_open', 'bar_high', 'bar_low', 'bar_close',
    'bar_volume', 'bar_delta',
    'wall_level', 'wall_side', 'wall_max_size', 'wall_trade_count',
    'proximity_to', 'proximity_level',
    'ib_high', 'ib_low', 'ib_range',
    'poc', 'va_high', 'va_low',
    'day_type',
]

for bar_time in TARGET_BARS:
    curr = find_bar(current_log, DATE, bar_time)
    bkp  = find_bar(backup_log, DATE, bar_time)

    print(f"\n{'='*60}")
    print(f"BARRA {bar_time}  |  ORIGINALE(bkp) vs ATTUALE(curr)")
    print(f"{'='*60}")

    if not curr:
        print("  [ATTUALE] Non ancora analizzata.")
    if not bkp:
        print("  [ORIGINALE] Non presente nel backup.")

    if curr and bkp:
        print(f"{'Campo':<25} {'ORIGINALE':>15} {'ATTUALE':>15}  {'DIFF?'}")
        print("-"*65)
        for k in MARKET_KEYS:
            v_bkp  = bkp.get(k, 'N/A')
            v_curr = curr.get(k, 'N/A')
            diff = "⚠️ DIVERSO" if str(v_bkp) != str(v_curr) else ""
            print(f"  {k:<23} {str(v_bkp):>15} {str(v_curr):>15}  {diff}")

        print()
        print(f"  CONF ORIGINALE : {bkp.get('fabio_confidence')}  ({bkp.get('decision')})")
        print(f"  CONF ATTUALE   : {curr.get('fabio_confidence')}  ({curr.get('decision')})")
        print()
        print(f"  REASONING ORIGINALE:")
        print(f"    {bkp.get('fabio_reasoning','')[:300]}")
        print()
        print(f"  REASONING ATTUALE:")
        print(f"    {curr.get('fabio_reasoning','')[:300]}")
