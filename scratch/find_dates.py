import json
import os

trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"

reasoning_by_date_time = {}
with open(reasoning_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            d = json.loads(line)
            # Store volume for matching
            reasoning_by_date_time[(d['date'], d['bar_time_et'])] = d.get('bar_volume', 0)
        except:
            pass

print("=== Trades with bar volume >= 4500 ===")
import datetime
import pytz

with open(trades_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            t = json.loads(line)
            date_str = t.get('date', '')
            entry_time_str = t.get('entry_time')
            dt = datetime.datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
            dt_et = dt.astimezone(pytz.timezone("America/New_York"))
            et_time_str = dt_et.strftime("%H:%M")
            
            # Find matching reasoning volume
            vol = reasoning_by_date_time.get((date_str, et_time_str), 0)
            if vol == 0:
                # check nearby
                h_trade, m_trade = dt_et.hour, dt_et.minute
                best_diff = 999
                for (r_date, r_time_str), r_vol in reasoning_by_date_time.items():
                    if r_date != date_str:
                        continue
                    h_r, m_r = map(int, r_time_str.split(':'))
                    diff = abs((h_trade * 60 + m_trade) - (h_r * 60 + m_r))
                    if diff < best_diff and diff <= 10:
                        best_diff = diff
                        vol = r_vol
                        
            if vol >= 4500:
                print(f"Date: {date_str} | Time (ET): {et_time_str} | Vol: {vol} | PnL: ${t.get('pnl_usd'):.2f} | Contracts: {t.get('contracts')}")
        except Exception as e:
            pass
