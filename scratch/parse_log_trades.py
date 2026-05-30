import re

log_path = r'C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\.system_generated\tasks\task-8775.log'

wins = 0
losses = 0
scratches = 0
total_pnl = 0

print(f"{'Ora':<10} | {'Dir':<5} | {'Esito':<25} | {'PnL ($)':<10}")
print("-" * 60)

with open(log_path, 'r', encoding='utf-8') as f:
    # Actually wait, `session_buffer` contains "⚠️ [TRADE CLOSED]". 
    # But `session_buffer` isn't printed to stdout directly!
    # Ah!!! `handle_close` does: `session_buffer.append(...)` but it doesn't `print` it!
    # It only prints "[MONEY MANAGEMENT] Stop loss hit." or "Trailing stop hit in profit".
    pass
