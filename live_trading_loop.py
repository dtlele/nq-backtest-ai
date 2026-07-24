import os
import sys
import time
import pytz
import numpy as np
import pandas as pd
from datetime import datetime, time as datetime_time
import MetaTrader5 as mt5

# Aggiungi il path principale del progetto
sys.path.append(r"C:\Users\Mauro\Documents\nq-backtest-clean")

from mt5_live_bot import MT5LiveBot, ET
from src.candidate_detector import detect_candidates
from src.session_context import build_session_context
from src.volume_profile import compute_volume_profile

# Day-similarity engine: gives a regime-aware size + skip decision at 10:00 ET
from src.day_similarity.open_signal import compute_open_signal, OpenSignal
from src.day_similarity.data_loader import slice_phase as _ss_slice_phase

def get_current_m5_bars(symbol, num_bars=100, broker_offset_hours=2):
    """
    Scarica le ultime `num_bars` candele M5 da MT5 e le converte in oggetti Bar compatibili.
    """
    from src import Bar
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, num_bars)
    if rates is None or len(rates) == 0:
        return []
        
    bars = []
    broker_offset = pytz.FixedOffset(broker_offset_hours * 60)
    
    for r in rates:
        # Converti il tempo server in UTC
        server_dt = datetime.fromtimestamp(r['time'], pytz.utc) - pd.Timedelta(hours=broker_offset_hours)
        bar_utc = server_dt.replace(tzinfo=pytz.utc)
        
        # Mappa i campi di MT5 nell'oggetto Bar del nostro framework
        b = Bar(
            timestamp=bar_utc,
            open=float(r['open']),
            high=float(r['high']),
            low=float(r['low']),
            close=float(r['close']),
            volume=int(r['tick_volume']),
            buy_volume=int(r['tick_volume'] // 2),  # Approssimazione per il test in tempo reale
            sell_volume=int(r['tick_volume'] // 2),
            delta=0,
            delta_pct=0.0,
            cvw=0.0,
            vwap=float(r['close']) # Semplificato
        )
        bars.append(b)
    return bars

def check_deterministic_signals(bars, bot):
    """
    Analizza le barre e determina se ci sono segnali operativi deterministici
    in base alle regole dei pattern storici (breakout dell'IB o sweep dell'IB).
    
    :param bars: Lista delle barre M5 recenti
    :param bot: Istanza di MT5LiveBot per accedere a VAL, VAH, POC e IB
    :return: (setup_name, direction, entry_price) se viene trovato un segnale, altrimenti (None, None, None)
    """
    if len(bars) < 3 or not bot.session_started:
        return None, None, None
        
    last_bar = bars[-1]
    prev_bar = bars[-2]
    current_price = last_bar.close
    
    # --------------------------------------------------------------------------
    # SETUP DETERMINISTICO 1: Breakout dell'Initial Balance (Trend Continuation)
    # --------------------------------------------------------------------------
    # Se il prezzo rompe ed accetta sopra il massimo dell'IB, cerchiamo un ingresso Long in trend
    if prev_bar.close <= bot.va_high and last_bar.close > bot.va_high:
        # Breakout rialzista confermato
        return "trend_long", "long", current_price
        
    # Se il prezzo rompe ed accetta sotto il minimo dell'IB, cerchiamo un ingresso Short in trend
    if prev_bar.close >= bot.va_low and last_bar.close < bot.va_low:
        # Breakout ribassista confermato
        return "trend_short", "short", current_price
        
    # --------------------------------------------------------------------------
    # SETUP DETERMINISTICO 2: Failed Auction / Sweep Fallito (Absorption)
    # --------------------------------------------------------------------------
    # Sweep del massimo dell'IB: il prezzo sale sopra VAH ma chiude sotto (Rejection)
    if last_bar.high > bot.va_high and last_bar.close < bot.va_high:
        return "absorb_short", "short", current_price
        
    # Sweep del minimo dell'IB: il prezzo scende sotto VAL ma chiude sopra (Rejection)
    if last_bar.low < bot.va_low and last_bar.close > bot.va_low:
        return "absorb_long", "long", current_price
        
    return None, None, None

def is_market_open():
    """Verifica se la sessione americana RTH è attiva (09:30 - 16:00 ET)."""
    now_et = datetime.now(ET)
    # RTH: lunedì - venerdì, dalle 09:30 alle 16:00
    if now_et.weekday() >= 5:
        return False
    rth_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    rth_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return rth_start <= now_et <= rth_end


# Module-level state for the once-per-day open signal
_last_open_signal_date = None


def _compute_today_open_signal(bars_m5, bot, broker_offset: int) -> OpenSignal:
    """Build a 1-min pre-market + IB slice for today and run the
    day-similarity engine.  Called once at 10:00 ET from the main loop.
    """
    from src.bar_aggregator import aggregate_to_bars
    from src.data_loader import load_day
    # Use the 1-min bars from the bot's tick buffer if available,
    # otherwise fall back to the cache.
    try:
        # Try to get 1-min bars from the bot
        bars_1min = getattr(bot, "m1_bars", None) or []
    except Exception:
        bars_1min = []

    if not bars_1min:
        # Fall back: read today's Databento tick file if present
        from src.day_similarity.ticks_loader import _load_one_file
        today_str = datetime.now(ET).strftime("%Y%m%d")
        path = rf"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-{today_str}.trades.csv"
        if os.path.exists(path):
            df = _load_one_file(path)
            if not df.empty:
                df["minute_et"] = (df["ts"].dt.tz_convert(ET).dt.hour * 60
                                    + df["ts"].dt.tz_convert(ET).dt.minute)
                df["date_et"] = pd.to_datetime(df["ts"].dt.tz_convert(ET).dt.date)
                pre = _ss_slice_phase(df, 0, 9*60+30)
                ib  = _ss_slice_phase(df, 9*60+30, 10*60)
            else:
                pre, ib = pd.DataFrame(), pd.DataFrame()
        else:
            pre, ib = pd.DataFrame(), pd.DataFrame()
    else:
        df = pd.DataFrame([{
            "ts": b.timestamp, "open": b.open, "high": b.high,
            "low": b.low, "close": b.close, "volume": b.volume,
        } for b in bars_1min])
        df["date_et"] = pd.to_datetime(df["ts"].dt.tz_convert(ET).dt.date)
        df["minute_et"] = (df["ts"].dt.tz_convert(ET).dt.hour * 60
                            + df["ts"].dt.tz_convert(ET).dt.minute)
        pre = _ss_slice_phase(df, 0, 9*60+30)
        ib  = _ss_slice_phase(df, 9*60+30, 10*60)

    last_tick = mt5.symbol_info_tick(symbol)
    current_price = float(last_tick.last) if last_tick else 0.0
    account_equity = float(bot.account_balance) if hasattr(bot, "account_balance") else 50000.0

    sig = compute_open_signal(
        pre_bars=pre, ib_bars=ib,
        current_price=current_price,
        account_equity=account_equity,
        base_risk_pct=0.005,
        min_contracts=1, max_contracts=20,
        symbol="MNQ",
    )
    return sig

def main_loop(symbol="MNQM26", broker_offset=3):
    """
    Loop principale deterministico in Python puro per il monitoraggio
    e l'esecuzione dei trade reali su MT5.
    """
    print("=" * 60)
    print("🚀 AVVIO DEL BOT DI TRADING LIVE DETERMINISTICO (PYTHON PURO)")
    print("=" * 60)
    
    bot = MT5LiveBot(symbol=symbol, account_balance=50000.0, broker_utc_offset_hours=broker_offset)
    if not bot.start():
        print("[ERROR] Impossibile connettersi a MT5. Arresto.")
        return
        
    print(f"[INFO] Regime di Volatilità Rilevato: {bot.regime} (ATR 5D: {bot.atr_5d:.2f} pt)")
    print("[INFO] Bot in ascolto del mercato... Aggiornamento ogni 5 secondi.")
    
    last_check_minute = -1
    
    try:
        while True:
            # 1. Controlla connessione
            if not mt5.terminal_info():
                print("[WARNING] Connessione persa. Riconnessione...")
                bot.start()
                
            # 2. Sincronizza flussi e dati volumetrici (Value Area, CVD, Mega Trades)
            bot.update_value_area()
            bot.sync_ticks_and_flows()
            
            # Attiva lo stato di sessione se siamo all'interno dell'orario operativo
            if is_market_open():
                bot.session_started = True
            else:
                bot.session_started = False
                
            # 3. Analisi delle barre chiuse (ad ogni chiusura di candela M5)
            now_dt = datetime.now(ET)
            if now_dt.minute % 5 == 0 and now_dt.minute != last_check_minute:
                last_check_minute = now_dt.minute
                
                # Scarica le ultime barre M5
                bars_m5 = get_current_m5_bars(symbol, num_bars=50, broker_offset_hours=broker_offset)
                if bars_m5:
                    # 3a. Day-similarity open signal (only at 10:00 ET, once per day)
                    if (now_dt.hour == 10 and now_dt.minute == 0
                            and now_dt.date() != _last_open_signal_date):
                        try:
                            _open_sig = _compute_today_open_signal(bars_m5, bot, broker_offset)
                            _last_open_signal_date = now_dt.date()
                            print(f"[OPEN-SIGNAL] {_open_sig.summary_line()}")
                        except Exception as _e:
                            print(f"[OPEN-SIGNAL] failed: {_e}")
                    
                    # Verifica la presenza di setup deterministici basati sulle regole quantitative
                    setup_name, direction, entry_price = check_deterministic_signals(bars_m5, bot)
                    
                    if setup_name and direction and entry_price:
                        # Passa i segnali all'esecutore con le 4 regole di gestione rischio
                        bot.validate_and_execute(
                            setup_name=setup_name,
                            signal_direction=direction,
                            entry_price=entry_price
                        )
            
            # Stampiamo lo status sul terminale locale in modo silenzioso ed efficiente
            current_tick = mt5.symbol_info_tick(symbol)
            last_price = current_tick.last if current_tick else 0.0
            print(f"[LIVE STATUS] Prezzo: {last_price:.2f} | CVD: {bot.session_cvd:+} | VAL: {bot.va_low:.2f} | VAH: {bot.va_high:.2f} | Mega Trades: {len(bot.mega_trades_levels)}", end="\r")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n[INFO] Arresto del bot deterministico in corso.")
    finally:
        bot.shutdown()

if __name__ == "__main__":
    # Avvio del bot deterministico per CFD su prop house (es. NAS100, US100)
    # Configurare il simbolo esatto del proprio broker MT5
    main_loop(symbol="NAS100", broker_offset=3)

