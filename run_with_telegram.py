"""
Backtest runner con aggiornamenti Telegram ogni 2 minuti.
Lancia il backtest come subprocess e invia stats periodiche via Telegram MCP.
"""
import subprocess
import threading
import time
import json
import os
import sys
import requests
from datetime import datetime

TRADES_PATH = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
INTERVAL_SEC = 120  # 2 minuti

# --- Telegram via MCP HTTP (telegram-bridge) ---
def send_telegram(msg: str):
    """Invia messaggio Telegram tramite telegram-bridge MCP."""
    try:
        # Legge il token dal .env
        env_path = r"c:\Users\Mauro\Documents\nq-backtest\.env"
        token = None
        chat_id = None
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        token = line.strip().split('=', 1)[1].strip('"').strip("'")
                    if line.startswith('TELEGRAM_CHAT_ID='):
                        chat_id = line.strip().split('=', 1)[1].strip('"').strip("'")

        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
            print(f"  [TELEGRAM] Sent: {msg[:60]}...")
        else:
            print(f"  [TELEGRAM] No token/chat_id found in .env — skipping.")
    except Exception as e:
        print(f"  [TELEGRAM ERROR] {e}")

def read_trades():
    trades = []
    try:
        with open(TRADES_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        trades.append(json.loads(line))
                    except:
                        pass
    except:
        pass
    return trades

def build_stats(trades):
    if not trades:
        return "📊 <b>Backtest in corso</b>\n0 trade aperti."
    total = len(trades)
    wins = [t for t in trades if t.get('pnl_usd', 0) > 0]
    pnl = sum(t.get('pnl_usd', 0) for t in trades)
    wr = len(wins) / total * 100 if total else 0
    dates = sorted(set(t.get('date', '') for t in trades))
    last_date = dates[-1] if dates else '?'
    shorts = [t for t in trades if t.get('direction') == 'short']

    # max drawdown
    cumul, running, peak, max_dd = [], 0, 0, 0
    for t in trades:
        running += t.get('pnl_usd', 0)
        peak = max(peak, running)
        max_dd = max(max_dd, peak - running)

    msg = (
        f"📊 <b>Backtest Update</b> — {datetime.now().strftime('%H:%M')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 Ultima data: <b>{last_date}</b> ({len(dates)} gg)\n"
        f"📈 Trade totali: <b>{total}</b> (shorts: {len(shorts)})\n"
        f"🎯 Win Rate: <b>{wr:.1f}%</b> ({len(wins)}/{total})\n"
        f"💰 P&L netto: <b>${pnl:+,.2f}</b>\n"
        f"📉 Max Drawdown: <b>-${max_dd:,.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return msg

def telegram_loop(stop_event):
    """Thread che invia update ogni 2 minuti finché il processo gira."""
    time.sleep(30)  # attendi avvio iniziale
    while not stop_event.is_set():
        trades = read_trades()
        msg = build_stats(trades)
        send_telegram(msg)
        stop_event.wait(INTERVAL_SEC)

def main():
    print("=" * 60)
    print("  BACKTEST LAUNCHER con Telegram updates ogni 2 min")
    print("  Fixes attivi:")
    print("    ✅ LLM analizza ogni barra (contesto completo)")
    print("    ✅ Exec Veto volume < 4500 (non salta LLM)")
    print("    ✅ Short: 4 filtri (day_type+IB+no_squeeze+stop15-25)")
    print("    ✅ Stop buffer: 0.5pt (era 2pt)")
    print("    ✅ Entry proximity veto: < 2pt dal wall = battle zone")
    print("=" * 60)

    # Avvio telegram thread
    stop_event = threading.Event()
    tg_thread = threading.Thread(target=telegram_loop, args=(stop_event,), daemon=True)
    tg_thread.start()

    # Messaggio di avvio
    send_telegram(
        "🚀 <b>Backtest avviato!</b>\n"
        "📅 Periodo: Gen 2025 → Nov 2025\n"
        "📋 Strategy: fabio_andrea_predatory_4500\n"
        "⚙️ Fix attivi: exec_veto + short_4_filters + stop_0.5pt + proximity_veto\n"
        "⏱ Update ogni 2 minuti."
    )

    # Lancia il backtest come subprocess
    cmd = [
        sys.executable, "run_backtest.py",
        "--strategy", "fabio_andrea_predatory_4500",
        "--start-date", "20250101",
        "--end-date", "20251130",
        "--quiet"
    ]
    proc = subprocess.Popen(cmd, cwd=r"c:\Users\Mauro\Documents\nq-backtest",
                            stdout=sys.stdout, stderr=sys.stderr)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\n[INTERRUPTED]")
    finally:
        stop_event.set()

    # Report finale
    trades = read_trades()
    final_msg = build_stats(trades)
    final_msg = "✅ <b>BACKTEST COMPLETATO</b>\n" + final_msg
    send_telegram(final_msg)
    print("\n" + final_msg.replace('<b>', '').replace('</b>', ''))

if __name__ == '__main__':
    main()
