"""
Telegram Notifier con Cron ogni 5 minuti.
Analizza i ragionamenti dei trade invece di troncarli,
e mostra l'orario di avvio della run corrente.
"""
import sys
import json
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import requests
import datetime
from collections import defaultdict
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8745379821:AAE3Oa2CUjrbVzRPW_yJyOwnpQHD4RXvjZ8')
CHAT_ID    = os.environ.get('TELEGRAM_CHAT_ID', '-1003723252971')
BASE_DIR   = Path(__file__).parent.parent
TRADES_LOG = BASE_DIR / 'agent_memory' / 'trades_log.jsonl'
REASONING_LOG = BASE_DIR / 'agent_memory' / 'reasoning_log.jsonl'

# ── Run start time tracker ──────────────────────────────────────────────
MARKER_FILE = BASE_DIR / 'agent_memory' / 'run_start_marker.json'


def get_run_start() -> str:
    """Legge l'orario di avvio della run corrente dal marker file."""
    if MARKER_FILE.exists():
        try:
            data = json.loads(MARKER_FILE.read_text(encoding='utf-8'))
            return data.get('start_time', 'N/A')
        except:
            pass
    return 'N/A'

def get_run_range() -> tuple:
    """Legge il range di date dal marker file."""
    if MARKER_FILE.exists():
        try:
            data = json.loads(MARKER_FILE.read_text(encoding='utf-8'))
            r = data.get('range', '')
            if '→' in r:
                parts = r.split('→')
                return parts[0].strip(), parts[1].strip()
        except:
            pass
    return None, None


def set_run_start():
    """Scrive l'orario di avvio nel marker file (chiamare all'avvio del backtest)."""
    MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKER_FILE.write_text(json.dumps({
        'start_time': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    }), encoding='utf-8')


def analyze_reasoning(reason: str, direction: str, exit_reason: str, pnl: float) -> str:
    """
    Produce un'analisi sintetica del ragionamento invece di troncarlo.
    Estrae le informazioni chiave: setup, wall, delta, motivazione principale.
    """
    if not reason:
        return "Nessun reasoning disponibile."

    signals = []

    # Rileva segnali chiave nel ragionamento
    lower = reason.lower()
    if 'absorption' in lower:
        signals.append("assorbimento istituzionale rilevato")
    if 'initiative' in lower or 'aggression' in lower:
        signals.append("aggressione direzionale confermata")
    if 'delta' in lower and 'negative' in lower:
        signals.append("delta negativo")
    if 'delta' in lower and 'positive' in lower:
        signals.append("delta positivo")
    if 'divergence' in lower:
        signals.append("divergenza di delta rilevata")
    if 'trapped' in lower:
        signals.append("trader intrappolati presenti")
    if 'ib low' in lower or 'ib high' in lower:
        signals.append("rottura dell'Initial Balance")
    if 'imbalance' in lower:
        signals.append("fase di sbilanciamento attiva")
    if 'exhaustion' in lower or 'waning' in lower:
        signals.append("segnali di esaurimento del trend")

    # Estrai il numero di contratti big trades se presente
    import re
    big_trade_match = re.search(r'(\d{2,3})\s+(SELL|BUY|sell|buy)\s+(contracts|@)', reason)
    if big_trade_match:
        signals.append(f"Big Trade: {big_trade_match.group(1)} contratti {big_trade_match.group(2).upper()}")

    # Analisi esito
    if exit_reason == 'target':
        outcome_analysis = "Mossa istituzionale confermata e completata al target."
    elif exit_reason == 'stop':
        if 'divergence' in lower or 'trapped' in lower or 'exhaustion' in lower:
            outcome_analysis = "Segnale corretto ma momentum insufficiente per sostenere il trade."
        else:
            outcome_analysis = "Contro-reazione avversa ha invalidato il setup."
    elif 'trailing' in str(exit_reason):
        outcome_analysis = "Uscita in trailing profit — posizione gestita con successo."
    elif 'eod' in str(exit_reason):
        outcome_analysis = "Chiusura di fine sessione."
    else:
        outcome_analysis = "Uscita anticipata per cambio struttura."

    signal_str = " | ".join(signals) if signals else "Setup standard"
    return f"{signal_str}. {outcome_analysis}"


def load_recent_trades(days: int = 3) -> list:
    """Carica i trade recenti degli ultimi N giorni."""
    trades = []
    if not TRADES_LOG.exists():
        return trades
    try:
        with open(TRADES_LOG, 'r', encoding='utf-8-sig') as f:
            for line in f:
                if line.strip():
                    try:
                        trades.append(json.loads(line))
                    except:
                        pass
    except:
        pass

    # Filtra prima per range della run attuale se presente
    start_date, end_date = get_run_range()
    if start_date and end_date:
        trades = [t for t in trades if start_date <= t.get('date', '') <= end_date]

    # Prendi solo gli ultimi N giorni distinti tra quelli filtrati
    dates = sorted(set(t.get('date','') for t in trades if t.get('date')))
    cutoff = dates[-days] if len(dates) >= days else (dates[0] if dates else '')
    return [t for t in trades if t.get('date','') >= cutoff]


def build_message() -> str:
    """Costruisce il messaggio Telegram completo."""
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    run_start = get_run_start()

    trades = load_recent_trades(days=5)
    if not trades:
        return f"<b>📊 NQ Backtest — {now}</b>\n<pre>Nessun trade disponibile.</pre>"

    # Statistiche per giornata
    by_date = defaultdict(list)
    for t in trades:
        by_date[t.get('date','?')].append(t)

    lines = []
    lines.append(f"🕐 Aggiornamento: {now}")
    lines.append(f"🚀 Avvio run: {run_start}")
    lines.append("")

    # Tabella giornaliera
    lines.append(f"{'Data':<12} {'T':>3} {'W/L':>6} {'WR%':>6} {'P&L':>9}")
    lines.append("-" * 42)
    total_pnl = 0.0
    for date in sorted(by_date.keys()):
        day = by_date[date]
        wins = sum(1 for t in day if t.get('pnl_usd', 0) > 10)
        losses = sum(1 for t in day if t.get('pnl_usd', 0) < -10)
        scratches = len(day) - wins - losses
        pnl = sum(t.get('pnl_usd', 0) for t in day)
        total_pnl += pnl
        wr = (wins / len(day) * 100) if day else 0
        wl = f"{wins}/{losses}"
        pnl_str = f"+${pnl:.0f}" if pnl >= 0 else f"-${abs(pnl):.0f}"
        lines.append(f"{date:<12} {len(day):>3} {wl:>6} {wr:>5.0f}% {pnl_str:>9}")

    lines.append("-" * 42)
    tot_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
    lines.append(f"{'TOTALE':<12} {'':>3} {'':>6} {'':>6} {tot_str:>9}")
    lines.append("")

    # Ultimi 5 trade con analisi
    all_sorted = sorted(trades, key=lambda t: (t.get('date',''), t.get('entry_time','')))
    last_5 = all_sorted[-5:]
    lines.append("📋 ULTIMI TRADE - ANALISI:")
    lines.append("─" * 42)

    for t in last_5:
        date = t.get('date','?')
        et = t.get('entry_time','')[11:16]
        direction = t.get('direction','?').upper()
        pnl = t.get('pnl_usd', 0)
        exit_r = t.get('exit_reason','?')
        conf = t.get('final_confidence', '?')

        icon = "[WIN]" if pnl > 10 else ("[LOSS]" if pnl < -10 else "[SCR]")
        pnl_str = f"+${pnl:.1f}" if pnl >= 0 else f"-${abs(pnl):.1f}"

        lines.append(f"{icon} {date} {et} {direction} {pnl_str} (conf:{conf}%)")
        lines.append(f"   Livelli: in={t.get('entry')} sl={t.get('stop')} tp={t.get('target')}")

        analysis = analyze_reasoning(
            t.get('fabio_reasoning',''),
            direction,
            str(exit_r),
            pnl
        )
        lines.append(f"   Analisi: {analysis}")
        lines.append("")

    return f"<b>📊 NQ Backtest Fabio</b>\n<pre>{''.join(l + chr(10) for l in lines)}</pre>"


def send_telegram(message: str):
    """Invia il messaggio a Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("Messaggio Telegram inviato con successo!")
        else:
            print(f"Errore Telegram: {r.text}")
    except Exception as e:
        print(f"Errore connessione Telegram: {e}")


if __name__ == "__main__":
    msg = build_message()
    print(msg)
    send_telegram(msg)
