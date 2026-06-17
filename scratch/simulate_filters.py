import json
from datetime import datetime
import pytz

def parse_time_et(iso_str):
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'
    dt_utc = datetime.fromisoformat(iso_str)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
    dt_et = dt_utc.astimezone(pytz.timezone('America/New_York'))
    return dt_et

trades = []
with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if not line.strip(): continue
        trades.append(json.loads(line))

print(f"Total trades loaded: {len(trades)}")

def analyze(filtered_trades, label):
    wins = [t for t in filtered_trades if t.get('pnl_usd', 0.0) > 0]
    losses = [t for t in filtered_trades if t.get('pnl_usd', 0.0) < 0]
    
    net_pnl = sum(t.get('pnl_usd', 0.0) for t in filtered_trades)
    win_rate = (len(wins) / len(filtered_trades)) * 100 if filtered_trades else 0.0
    
    total_win = sum(t.get('pnl_usd', 0.0) for t in wins)
    total_loss = sum(t.get('pnl_usd', 0.0) for t in losses)
    
    avg_win = total_win / len(wins) if wins else 0.0
    avg_loss = total_loss / len(losses) if losses else 0.0
    profit_factor = abs(total_win / total_loss) if total_loss != 0 else float('inf')
    
    # Calculate drawdown
    peak = 0.0
    current = 0.0
    max_dd = 0.0
    for t in filtered_trades:
        current += t.get('pnl_usd', 0.0)
        if current > peak:
            peak = current
        dd = peak - current
        if dd > max_dd:
            max_dd = dd
            
    print(f"\n=== {label} ===")
    print(f"Trades Count: {len(filtered_trades)}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)} | Win Rate: {win_rate:.1f}%")
    print(f"Net PnL: ${net_pnl:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
    print(f"Max Peak-to-Valley Drawdown: ${max_dd:.2f}")

# 1. Baseline
analyze(trades, "BASELINE (All Trades)")

# 2. Long Only
long_only = [t for t in trades if t.get('direction') == 'long']
analyze(long_only, "LONG ONLY")

# 3. Time window only: 09:30 to 11:00 ET (which corresponds to 09:35 - 10:59 ET entries)
time_only = []
for t in trades:
    dt = parse_time_et(t.get('entry_time'))
    # Hour 9 or 10
    if dt.hour == 9 or dt.hour == 10:
        time_only.append(t)
analyze(time_only, "TIME WINDOW ONLY (09:30 - 11:00 ET)")

# 4. Long Only + Time Window (09:30 - 11:00 ET)
both = []
for t in trades:
    if t.get('direction') != 'long': continue
    dt = parse_time_et(t.get('entry_time'))
    if dt.hour == 9 or dt.hour == 10:
        both.append(t)
analyze(both, "LONG ONLY + TIME WINDOW (09:30 - 11:00 ET)")
