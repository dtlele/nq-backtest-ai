import json
import csv
from collections import defaultdict

# 1. Load Calendar
news_days = set()
try:
    with open('c:/Users/Mauro/Documents/nq-backtest/data/economic_calendar.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = row['datetime'].split('T')[0]
            news_days.add(dt)
except Exception as e:
    print('Error loading calendar:', e)

# 2. Load Trades
pnl_by_day = defaultdict(float)
trades_by_day = defaultdict(list)
try:
    with open('c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl', 'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                date = d.get('date', '')
                pnl = d.get('pnl_usd', 0)
                if date and pnl is not None:
                    pnl_by_day[date] += pnl
                    trades_by_day[date].append(d)
            except: pass
except Exception as e:
    print('Error loading trades:', e)

# 3. Analyze
sorted_days = sorted(pnl_by_day.items(), key=lambda x: x[1], reverse=True)

print('=== TOP 5 BEST DAYS ===')
for k, v in sorted_days[:5]:
    is_news = 'YES' if k in news_days else 'NO'
    wins = len([t for t in trades_by_day[k] if t.get('pnl_usd', 0) > 0])
    losses = len([t for t in trades_by_day[k] if t.get('pnl_usd', 0) <= 0])
    print(f'{k}: PnL=${v:.2f} | News: {is_news} | (W: {wins}, L: {losses})')

print('\n=== TOP 5 WORST DAYS ===')
for k, v in sorted_days[-5:]:
    is_news = 'YES' if k in news_days else 'NO'
    wins = len([t for t in trades_by_day[k] if t.get('pnl_usd', 0) > 0])
    losses = len([t for t in trades_by_day[k] if t.get('pnl_usd', 0) <= 0])
    print(f'{k}: PnL=${v:.2f} | News: {is_news} | (W: {wins}, L: {losses})')

print('\n=== OVERALL STATS ===')
news_pnl = sum(v for k, v in pnl_by_day.items() if k in news_days)
no_news_pnl = sum(v for k, v in pnl_by_day.items() if k not in news_days)
print(f'Total PnL on News Days: ${news_pnl:.2f}')
print(f'Total PnL on Normal Days: ${no_news_pnl:.2f}')
