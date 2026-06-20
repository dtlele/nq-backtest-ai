import json

trades_file = "c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl"
reasoning_file = "c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl"

reasonings = {}
with open(reasoning_file, "r") as f:
    for line in f:
        if not line.strip(): continue
        r = json.loads(line)
        key = (r.get("date"), r.get("bar_time_et"), r.get("trade_direction"))
        reasonings[key] = r.get("fabio_reasoning")

trades = []
with open(trades_file, "r") as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        trades.append(t)

stops = [t for t in trades if t.get('pnl_usd', 0) < 0 or t.get('exit_reason') in ['stop_hit', 'stop_loss']]

print("\nLast 5 Stopped Trades Analysis:")
for t in stops[-5:]:
    dt_utc = t.get('entry_time') # e.g. "2025-01-06T14:35:00+00:00"
    # To match reasoning: date and time_et
    # This is a bit tricky, let's just print the raw trade entry time and see if we can manually look it up
    # Wait, we can parse the ET time
    import datetime
    dt_obj = datetime.datetime.fromisoformat(dt_utc)
    from dateutil import tz
    dt_et = dt_obj.astimezone(tz.gettz('America/New_York'))
    
    date_str = dt_et.strftime('%Y-%m-%d')
    time_et_str = dt_et.strftime('%H:%M')
    direction = t.get('direction')
    
    reasoning = reasonings.get((date_str, time_et_str, direction), "Not found")
    
    print(f"Date: {date_str} {time_et_str} ET, PnL: {t.get('pnl_usd')}")
    print(f"Setup: {t.get('setup_type')}, Direction: {direction}")
    print(f"Entry: {t.get('entry_price')}, Stop: {t.get('stop_loss')}, Exit: {t.get('exit_price')}")
    print(f"Reasoning: {reasoning}")
    print("-" * 50)
