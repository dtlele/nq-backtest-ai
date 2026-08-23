"""
WebSocket Server principale per DeepPrint Pro.

Gestisce:
- Replay storico di barre M1/M5 da Databento CSV
- Calcolo Volume Profile progressivo
- Invio sessione context (IB, day_type, GEX)
- Segnali agenti LLM (opzionale)
- Comandi client: play/pause/step/speed/date

Avvio: python -m platform.ws_server
   oppure: python platform/ws_server.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import traceback

# Aggiungi project root a sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import websockets
except ImportError:
    print("ERRORE: websockets non installato. Esegui: pip install websockets")
    sys.exit(1)

# Import configurazione direttamente dal file (evita conflitto con built-in 'platform')
import importlib.util
_config_path = PROJECT_ROOT / "platform" / "config.py"
_spec = importlib.util.spec_from_file_location("deepprint_config", _config_path)
_config_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_mod)

WS_HOST = _config_mod.WS_HOST
WS_PORT = _config_mod.WS_PORT
DEFAULT_REPLAY_SPEED = _config_mod.DEFAULT_REPLAY_SPEED
MAX_REPLAY_SPEED = _config_mod.MAX_REPLAY_SPEED
MAX_CANDLES_IN_MEMORY = _config_mod.MAX_CANDLES_IN_MEMORY
VP_UPDATE_EVERY_N_BARS = _config_mod.VP_UPDATE_EVERY_N_BARS
NQ_TICK_SIZE = _config_mod.NQ_TICK_SIZE
NQ_BIG_TRADE_THRESHOLD = _config_mod.NQ_BIG_TRADE_THRESHOLD
IB_DURATION_MIN = _config_mod.IB_DURATION_MIN
NY_OPEN_H = _config_mod.NY_OPEN_H
NY_OPEN_M = _config_mod.NY_OPEN_M
FABIO_START_H = _config_mod.FABIO_START_H
FABIO_START_M = _config_mod.FABIO_START_M
FABIO_END_H = _config_mod.FABIO_END_H
FABIO_END_M = _config_mod.FABIO_END_M
CACHE_OHLC_DIR = _config_mod.CACHE_OHLC_DIR

# Import DataService direttamente
_ds_path = PROJECT_ROOT / "platform" / "data_service.py"
_spec2 = importlib.util.spec_from_file_location("deepprint_data_service", _ds_path)
_ds_mod = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_ds_mod)
DataService = _ds_mod.DataService

# Import CleanBridge (dati agenti da nq-backtest-clean)
_cb_path = PROJECT_ROOT / "platform" / "clean_bridge.py"
_spec3 = importlib.util.spec_from_file_location("clean_bridge", _cb_path)
_cb_mod = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(_cb_mod)
get_bridge = _cb_mod.get_bridge

import pytz
from src.volume_profile import compute_volume_profile
from src.session_context import (
    build_session_context, compute_ib, classify_day_type,
    filter_overnight_window, filter_ny_window
)

ET = pytz.timezone('America/New_York')


# ─────────────────────────────────────────────────────────────────────────────
# Serializzatori JSON
# ─────────────────────────────────────────────────────────────────────────────

def _compute_imbalance(bid_vol: int, ask_vol: int) -> str:
    """Rileva imbalance tra bid e ask."""
    if ask_vol > bid_vol * 3 and ask_vol > 50:
        return 'ask'
    if bid_vol > ask_vol * 3 and bid_vol > 50:
        return 'bid'
    return 'none'


def _build_candle_message(bar, vp=None, ctx=None, running_cvd: int = 0) -> dict:
    """
    Costruisce il messaggio candle_update da inviare al frontend.
    Include livelli footprint bid×ask completi.
    """
    # Footprint levels completi dalla barra
    fp_levels = getattr(bar, '_fp_levels', [])

    # Costruisce levels con metadata VP
    poc_price = vp.poc if vp else None
    vah = vp.va_high if vp else None
    val = vp.va_low if vp else None
    hvn_set = set(round(p, 2) for p in (vp.hvn_levels if vp else []))
    lvn_set = set(round(p, 2) for p in (vp.lvn_levels if vp else []))

    ib_high = ctx.ib_high if ctx else None
    ib_low  = ctx.ib_low  if ctx else None

    levels_out = []
    for lvl in fp_levels:
        price = lvl['price']
        bid_v = lvl['bid_vol']
        ask_v = lvl['ask_vol']
        total = bid_v + ask_v
        delta_lvl = ask_v - bid_v
        imb = _compute_imbalance(bid_v, ask_v)

        price_r = round(price, 2)
        levels_out.append({
            'price':    round(price, 2),
            'bidVol':   bid_v,
            'askVol':   ask_v,
            'delta':    delta_lvl,
            'imbalance': imb,
            'isPoc':    poc_price is not None and abs(price - poc_price) < NQ_TICK_SIZE * 0.5,
            'isHvn':    price_r in hvn_set,
            'isLvn':    price_r in lvn_set,
            'isVah':    vah is not None and abs(price - vah) < NQ_TICK_SIZE * 0.5,
            'isVal':    val is not None and abs(price - val) < NQ_TICK_SIZE * 0.5,
            'isIbHigh': ib_high is not None and abs(price - ib_high) < NQ_TICK_SIZE * 0.5,
            'isIbLow':  ib_low  is not None and abs(price - ib_low)  < NQ_TICK_SIZE * 0.5,
        })

    # Big trades (bolle istituzionali)
    big_trades_out = []
    for t in bar.big_trades:
        big_trades_out.append({
            'price':     round(t.price, 2),
            'size':      t.size,
            'side':      t.side,
            'timestamp': t.ts_event.isoformat() if hasattr(t.ts_event, 'isoformat') else str(t.ts_event),
        })

    return {
        'type': 'candle_update',
        'timeframe': '1m',
        'data': {
            'barTimeUtc':  bar.timestamp.isoformat() if hasattr(bar.timestamp, 'isoformat') else str(bar.timestamp),
            'barOpen':     round(bar.open, 2),
            'barHigh':     round(bar.high, 2),
            'barLow':      round(bar.low, 2),
            'barClose':    round(bar.close, 2),
            'barVolume':   int(bar.volume),
            'barBuyVolume':  int(bar.buy_volume),
            'barSellVolume': int(bar.sell_volume),
            'barDelta':    int(bar.delta),
            'barDeltaPct': round(float(bar.delta_pct), 2),
            'barCvd':      running_cvd,
            'barVwap':     round(float(bar.vwap), 2),
            'levels':      levels_out,
            'bigTrades':   big_trades_out,
        }
    }


def _build_vp_message(vp, bars_m1: list) -> dict:
    """Costruisce il messaggio volume_profile_update."""
    if not vp:
        return {'type': 'volume_profile_update', 'data': None}

    # Calcola profilo completo (volume per livello)
    price_vol: dict = {}
    for bar in bars_m1:
        p_low  = round(bar.low  / NQ_TICK_SIZE) * NQ_TICK_SIZE
        p_high = round(bar.high / NQ_TICK_SIZE) * NQ_TICK_SIZE
        ticks  = max(1, round((p_high - p_low) / NQ_TICK_SIZE) + 1)
        vol_per_tick = bar.volume / ticks
        p = p_low
        while p <= p_high + 1e-9:
            key = round(p / NQ_TICK_SIZE) * NQ_TICK_SIZE
            price_vol[key] = price_vol.get(key, 0) + vol_per_tick
            p += NQ_TICK_SIZE

    total_vol = sum(price_vol.values()) if price_vol else 1
    profile = sorted(
        [{'price': round(p, 2), 'volume': round(v, 1), 'pct': round(v / total_vol * 100, 2)}
         for p, v in price_vol.items()],
        key=lambda x: -x['price']
    )

    return {
        'type': 'volume_profile_update',
        'data': {
            'poc':       round(vp.poc, 2),
            'vaHigh':    round(vp.va_high, 2),
            'vaLow':     round(vp.va_low, 2),
            'hvnLevels': [round(p, 2) for p in vp.hvn_levels],
            'lvnLevels': [round(p, 2) for p in vp.lvn_levels],
            'profile':   profile,
        }
    }


def _build_session_context_message(ctx) -> dict:
    """Costruisce il messaggio session_context."""
    if not ctx:
        return {'type': 'session_context', 'data': None}
    return {
        'type': 'session_context',
        'data': {
            'ibHigh':         round(float(ctx.ib_high), 2),
            'ibLow':          round(float(ctx.ib_low), 2),
            'ibRange':        round(float(ctx.ib_range), 2),
            'ibComplete':     bool(ctx.ib_complete),
            'dayType':        str(ctx.day_type),
            'gexRegime':      str(getattr(ctx, 'gex_regime', 'unknown')),
            'zeroGammaLevel': round(float(getattr(ctx, 'zero_gamma_level', 0.0)), 2),
            'callWall':       round(float(getattr(ctx, 'call_wall', 0.0)), 2),
            'putWall':        round(float(getattr(ctx, 'put_wall', 0.0)), 2),
        }
    }


def _build_replay_status_message(mode, date, bar_idx, total_bars, speed) -> dict:
    return {
        'type': 'replay_status',
        'data': {
            'mode':          mode,
            'currentDate':   date,
            'currentBarIdx': bar_idx,
            'totalBars':     total_bars,
            'speedMultiplier': speed,
        }
    }


def _build_available_dates_message(dates: list) -> dict:
    return {
        'type': 'available_dates',
        'data': {'dates': dates}
    }


def _build_trade_markers_message(date: str) -> dict:
    """Costruisce il messaggio trade_markers dal CleanBridge."""
    try:
        bridge = get_bridge()
        trades = bridge.get_trade_markers(date)
    except Exception as e:
        print(f"[Server] Errore bridge.get_trade_markers({date}): {e}")
        trades = []
    return {
        'type': 'trade_markers',
        'data': {'date': date, 'trades': trades}
    }


def _build_daily_roadmap_message(date: str) -> dict:
    """Costruisce il messaggio daily_roadmap dal CleanBridge."""
    try:
        bridge = get_bridge()
        roadmap = bridge.get_daily_roadmap(date)
    except Exception as e:
        print(f"[Server] Errore bridge.get_daily_roadmap({date}): {e}")
        roadmap = None
    return {
        'type': 'daily_roadmap',
        'data': roadmap  # Può essere None se non disponibile
    }


def _build_memory_stats_message() -> dict:
    """Costruisce il messaggio memory_stats dal CleanBridge."""
    try:
        bridge = get_bridge()
        stats = bridge.get_memory_stats()
    except Exception as e:
        print(f"[Server] Errore bridge.get_memory_stats(): {e}")
        stats = []
    return {
        'type': 'memory_stats',
        'data': {'stats': stats}
    }


def _build_agent_signals_batch(date: str) -> dict:
    """Costruisce il messaggio agent_signals_batch dal CleanBridge."""
    try:
        bridge = get_bridge()
        signals = bridge.get_agent_signals(date)
    except Exception as e:
        print(f"[Server] Errore bridge.get_agent_signals({date}): {e}")
        signals = []
    return {
        'type': 'agent_signals_batch',
        'data': {'date': date, 'signals': signals}
    }


# ─────────────────────────────────────────────────────────────────────────────
# Server principale
# ─────────────────────────────────────────────────────────────────────────────

class DeepPrintServer:
    """
    Server WebSocket asincrono per DeepPrint Pro.

    Gestisce replay storico da CSV Databento con:
    - Footprint M1 completo (bid×ask per livello)
    - Volume Profile progressivo
    - Session Context (IB, day_type, GEX)
    - Comandi client: play/pause/step/speed/date/seek
    """

    def __init__(self):
        self.clients: set = set()
        self.data_service = DataService()
        self.available_dates = self.data_service.list_available_dates()

        # Replay state
        self.mode          = 'paused'   # 'replay' | 'paused'
        self.replay_speed  = DEFAULT_REPLAY_SPEED
        self.replay_paused = True
        self.replay_date   = self.available_dates[-1] if self.available_dates else None

        # Dati sessione corrente
        self.bars_m1:  list = []
        self.bars_m5:  list = []
        self.bar_idx:  int  = 0
        self.session_ctx    = None
        self.current_vp     = None
        self.running_cvd    = 0

        # Evento per sincronizzazione step
        self._step_event = asyncio.Event()
        self._step_forward = False
        self._step_back    = False

        # Carica la data più recente all'avvio
        if self.replay_date:
            self._load_date_sync(self.replay_date)

    def _load_date_sync(self, date: str):
        """Carica i dati per una data (chiamata sincrona all'init)."""
        try:
            self.bars_m1, self.bars_m5 = self.data_service.load_date(date)
            self.bar_idx   = 0
            self.running_cvd = 0
            self.current_vp  = None
            self.session_ctx = None
            self.replay_date = date
            print(f"[Server] Data caricata: {date} — {len(self.bars_m1)} barre M1")
        except Exception as e:
            print(f"[Server] Errore caricamento {date}: {e}")
            traceback.print_exc()

    async def _load_date_async(self, date: str):
        """Carica i dati per una data in modo asincrono (non blocca event loop)."""
        loop = asyncio.get_event_loop()
        try:
            bars_m1, bars_m5 = await loop.run_in_executor(
                None, self.data_service.load_date, date
            )
            self.bars_m1   = bars_m1
            self.bars_m5   = bars_m5
            self.bar_idx   = 0
            self.running_cvd = 0
            self.current_vp  = None
            self.session_ctx = None
            self.replay_date = date
            print(f"[Server] Data caricata: {date} — {len(self.bars_m1)} barre M1")

            # Invia stato aggiornato a tutti i client
            await self.broadcast(_build_replay_status_message(
                self.mode, date, 0, len(self.bars_m1), self.replay_speed
            ))

            # Dati CleanBridge per questa data (esegui in executor per I/O)
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: get_bridge().load())

                # Invia trade_markers, daily_roadmap, agent_signals_batch
                await self.broadcast(_build_trade_markers_message(date))
                await self.broadcast(_build_daily_roadmap_message(date))
                await self.broadcast(_build_agent_signals_batch(date))
                await self.broadcast(_build_memory_stats_message())
            except Exception as e:
                print(f"[Server] Errore caricamento CleanBridge per {date}: {e}")
                # Invia comunque messaggi vuoti per non bloccare il frontend
                await self.broadcast({'type': 'trade_markers', 'data': {'date': date, 'trades': []}})
                await self.broadcast({'type': 'daily_roadmap', 'data': None})
                await self.broadcast({'type': 'agent_signals_batch', 'data': {'date': date, 'signals': []}})
                await self.broadcast({'type': 'memory_stats', 'data': {'stats': []}})
        except Exception as e:
            print(f"[Server] Errore caricamento {date}: {e}")
            await self.broadcast({'type': 'error', 'data': {'message': str(e)}})

    # ── Broadcast ──────────────────────────────────────────────────────────────

    async def broadcast(self, message: dict):
        """Invia un messaggio JSON a tutti i client connessi."""
        if not self.clients:
            return
        data = json.dumps(message, default=str)
        dead = set()
        for client in self.clients:
            try:
                await client.send(data)
            except Exception:
                dead.add(client)
        self.clients -= dead

    async def send_to(self, websocket, message: dict):
        """Invia un messaggio a un singolo client."""
        try:
            await websocket.send(json.dumps(message, default=str))
        except Exception:
            pass

    # ── Handler client ─────────────────────────────────────────────────────────

    async def handler(self, websocket):
        """Gestisce la connessione di ogni client WebSocket."""
        self.clients.add(websocket)
        client_addr = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
        print(f"[Server] Client connesso: {client_addr} (totale: {len(self.clients)})")

        try:
            # Invia stato iniziale
            await self._send_initial_state(websocket)

            # Ascolta comandi dal client
            async for raw_msg in websocket:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_client_message(websocket, msg)
                except json.JSONDecodeError:
                    await self.send_to(websocket, {'type': 'error', 'data': {'message': 'JSON non valido'}})
                except Exception as e:
                    print(f"[Server] Errore gestione comando: {e}")
                    traceback.print_exc()
        except Exception as e:
            print(f"[Server] Client disconnesso ({client_addr}): {e}")
        finally:
            self.clients.discard(websocket)
            print(f"[Server] Client rimosso (totale: {len(self.clients)})")

    async def _send_initial_state(self, websocket):
        """Invia lo stato completo al nuovo client."""
        # Lista date disponibili
        await self.send_to(websocket, _build_available_dates_message(self.available_dates))

        # Stato replay
        await self.send_to(websocket, _build_replay_status_message(
            self.mode, self.replay_date or '',
            self.bar_idx, len(self.bars_m1), self.replay_speed
        ))

        # Session context attuale (se disponibile)
        if self.session_ctx:
            await self.send_to(websocket, _build_session_context_message(self.session_ctx))

        # VP attuale
        if self.current_vp:
            await self.send_to(websocket, _build_vp_message(
                self.current_vp, self.bars_m1[:self.bar_idx]
            ))

        # Memory stats globali (una volta all'avvio)
        try:
            bridge = get_bridge()
            bridge.load()
            await self.send_to(websocket, _build_memory_stats_message())
            # Dati clean per la data corrente
            if self.replay_date:
                await self.send_to(websocket, _build_trade_markers_message(self.replay_date))
                await self.send_to(websocket, _build_daily_roadmap_message(self.replay_date))
                await self.send_to(websocket, _build_agent_signals_batch(self.replay_date))
        except Exception:
            pass

        # Ultime N candele come storia iniziale (batch)
        start = max(0, self.bar_idx - MAX_CANDLES_IN_MEMORY)
        history_bars = self.bars_m1[start:self.bar_idx]
        if history_bars:
            # Ricalcola CVD per la storia
            cvd_running = 0
            history_messages = []
            for bar in history_bars:
                cvd_running += bar.delta
                history_messages.append(_build_candle_message(
                    bar, self.current_vp, self.session_ctx, cvd_running
                ))
            await self.send_to(websocket, {
                'type': 'history_batch',
                'data': {'candles': [m['data'] for m in history_messages]}
            })

    async def _handle_client_message(self, websocket, msg: dict):
        """Gestisce i comandi in arrivo dal client."""
        action = msg.get('action', '')

        if action == 'replay_play':
            self.replay_paused = False
            self.mode = 'replay'
            print(f"[Server] ▶ PLAY — velocità {self.replay_speed}x")
            await self.broadcast({'type': 'replay_status', 'data': {
                'mode': 'replay', 'currentDate': self.replay_date,
                'currentBarIdx': self.bar_idx, 'totalBars': len(self.bars_m1),
                'speedMultiplier': self.replay_speed
            }})

        elif action == 'replay_pause':
            self.replay_paused = True
            self.mode = 'paused'
            print(f"[Server] ⏸ PAUSED")
            await self.broadcast({'type': 'replay_status', 'data': {
                'mode': 'paused', 'currentDate': self.replay_date,
                'currentBarIdx': self.bar_idx, 'totalBars': len(self.bars_m1),
                'speedMultiplier': self.replay_speed
            }})

        elif action == 'replay_step_forward':
            self._step_forward = True
            self._step_event.set()

        elif action == 'replay_step_back':
            self._step_back = True
            self._step_event.set()

        elif action == 'set_speed':
            speed = float(msg.get('multiplier', 1.0))
            self.replay_speed = max(0.1, min(speed, MAX_REPLAY_SPEED))
            print(f"[Server] Velocità: {self.replay_speed}x")
            await self.broadcast({'type': 'replay_status', 'data': {
                'mode': self.mode, 'currentDate': self.replay_date,
                'currentBarIdx': self.bar_idx, 'totalBars': len(self.bars_m1),
                'speedMultiplier': self.replay_speed
            }})

        elif action == 'set_replay_date':
            date = msg.get('date', '')
            if date in self.available_dates:
                was_paused = self.replay_paused
                self.replay_paused = True
                print(f"[Server] Caricamento data {date}...")
                await self._load_date_async(date)
                self.replay_paused = was_paused
            else:
                await self.send_to(websocket, {'type': 'error', 'data': {
                    'message': f"Data {date} non disponibile"
                }})

        elif action == 'seek':
            idx = int(msg.get('bar_idx', 0))
            if 0 <= idx < len(self.bars_m1):
                self.bar_idx = idx
                # Ricalcola CVD e VP fino a questo punto
                self.running_cvd = sum(b.delta for b in self.bars_m1[:idx])
                sub_bars = self.bars_m1[:idx]
                if sub_bars:
                    loop = asyncio.get_event_loop()
                    self.current_vp = await loop.run_in_executor(
                        None, compute_volume_profile, sub_bars
                    )
                await self.broadcast(_build_vp_message(self.current_vp, sub_bars))
                await self.broadcast({'type': 'replay_status', 'data': {
                    'mode': self.mode, 'currentDate': self.replay_date,
                    'currentBarIdx': self.bar_idx, 'totalBars': len(self.bars_m1),
                    'speedMultiplier': self.replay_speed
                }})

        elif action == 'get_daily_profile':
            date = msg.get('date', self.replay_date)
            await self._send_full_daily_profile(websocket, date)

        elif action == 'get_available_dates':
            await self.send_to(websocket, _build_available_dates_message(self.available_dates))

        elif action == 'get_daily_roadmap':
            date = msg.get('date', self.replay_date)
            await self.send_to(websocket, _build_daily_roadmap_message(date))

        elif action == 'get_memory_stats':
            await self.send_to(websocket, _build_memory_stats_message())

        elif action == 'get_agent_signals':
            date = msg.get('date', self.replay_date)
            await self.send_to(websocket, _build_agent_signals_batch(date))

        elif action == 'ping':
            await self.send_to(websocket, {'type': 'pong', 'ts': datetime.now().isoformat()})

        else:
            print(f"[Server] Comando sconosciuto: {action}")

    async def _send_full_daily_profile(self, websocket, date: str):
        """Invia il profilo VP completo del giorno (tutti i bar, non progressivo)."""
        try:
            loop = asyncio.get_event_loop()
            bars_m1, _ = await loop.run_in_executor(None, self.data_service.load_date, date)
            vp = await loop.run_in_executor(None, compute_volume_profile, bars_m1)
            if vp:
                await self.send_to(websocket, _build_vp_message(vp, bars_m1))
        except Exception as e:
            await self.send_to(websocket, {'type': 'error', 'data': {'message': str(e)}})

    # ── Loop replay principale ─────────────────────────────────────────────────

    async def _build_session_ctx_async(self, bars_so_far: list, date: str):
        """Costruisce il session context in modo asincrono."""
        loop = asyncio.get_event_loop()
        try:
            # Filtra barre overnight (prima delle 09:30 ET)
            overnight_bars = await loop.run_in_executor(None, filter_overnight_window, bars_so_far)
            vp = await loop.run_in_executor(None, compute_volume_profile, overnight_bars or bars_so_far)
            ctx = await loop.run_in_executor(None, build_session_context, date, bars_so_far, vp)
            return ctx
        except Exception as e:
            print(f"[Server] Errore costruzione session context: {e}")
            return None

    async def replay_loop(self):
        """Loop principale del replay: emette barre a cadenza controllata."""
        print(f"[Server] Replay loop avviato")

        while True:
            try:
                # Handle step events (anche in pausa)
                if self._step_event.is_set():
                    self._step_event.clear()
                    if self._step_forward and self.bar_idx < len(self.bars_m1):
                        await self._emit_bar(self.bar_idx)
                        self.bar_idx += 1
                        self._step_forward = False
                    elif self._step_back and self.bar_idx > 0:
                        self.bar_idx -= 1
                        self._step_back = False
                        # Re-emit la barra corrente (stato regredito)
                        await self._emit_bar(self.bar_idx)
                    continue

                if self.replay_paused:
                    # Attendi evento o timeout
                    try:
                        await asyncio.wait_for(self._step_event.wait(), timeout=0.2)
                    except asyncio.TimeoutError:
                        pass
                    continue

                if not self.bars_m1:
                    await asyncio.sleep(0.5)
                    continue

                if self.bar_idx >= len(self.bars_m1):
                    # Fine sessione — metti in pausa
                    self.replay_paused = True
                    self.mode = 'paused'
                    await self.broadcast({'type': 'session_end', 'data': {
                        'date': self.replay_date,
                        'totalBars': len(self.bars_m1)
                    }})
                    print(f"[Server] Fine sessione {self.replay_date}")
                    await asyncio.sleep(1)
                    continue

                # Emetti la barra corrente
                await self._emit_bar(self.bar_idx)
                self.bar_idx += 1

                # Sleep inversamente proporzionale alla velocità
                # speed=1 → 60s/bar, speed=60 → 1s/bar, speed=MAX → 0s
                sleep_time = 60.0 / self.replay_speed
                if sleep_time > 0.001:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Server] Errore nel replay loop: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)

    async def _emit_bar(self, idx: int):
        """Emette una singola barra M1 con VP e context aggiornati."""
        if idx >= len(self.bars_m1):
            return

        bar = self.bars_m1[idx]
        sub_bars = self.bars_m1[:idx + 1]

        # Aggiorna CVD
        self.running_cvd += bar.delta

        # Calcola VP progressivo (asincrono per non bloccare)
        if idx % VP_UPDATE_EVERY_N_BARS == 0:
            loop = asyncio.get_event_loop()
            self.current_vp = await loop.run_in_executor(
                None, compute_volume_profile, sub_bars
            )

        # Aggiorna session context (ogni 10 barre o a IB_DURATION_MIN)
        if idx % 10 == 0 or (idx < 35 and idx % 2 == 0):
            self.session_ctx = await self._build_session_ctx_async(sub_bars, self.replay_date)

        # Invia candle_update
        candle_msg = _build_candle_message(bar, self.current_vp, self.session_ctx, self.running_cvd)
        await self.broadcast(candle_msg)

        # Invia VP update (ogni VP_UPDATE_EVERY_N_BARS)
        if idx % VP_UPDATE_EVERY_N_BARS == 0 and self.current_vp:
            await self.broadcast(_build_vp_message(self.current_vp, sub_bars))

        # Invia session context (ogni 10 barre)
        if idx % 10 == 0 and self.session_ctx:
            await self.broadcast(_build_session_context_message(self.session_ctx))

        # Log progress ogni 30 barre
        if idx % 30 == 0:
            bar_time = bar.timestamp.astimezone(ET).strftime('%H:%M ET') if hasattr(bar.timestamp, 'astimezone') else str(bar.timestamp)
            poc_str = f"POC={self.current_vp.poc:.2f}" if self.current_vp else "VP=None"
            print(f"[Server] [{self.replay_date}] Barra {idx}/{len(self.bars_m1)} {bar_time} "
                  f"C={bar.close:.2f} Δ={bar.delta:+d} CVD={self.running_cvd:+d} {poc_str}")

    # ── Entry point ────────────────────────────────────────────────────────────

    async def run(self):
        """Avvia il server WebSocket e il loop replay."""
        print(f"[Server] DeepPrint Pro WebSocket Server")
        print(f"[Server] Listening on ws://{WS_HOST}:{WS_PORT}")
        print(f"[Server] Date disponibili: {len(self.available_dates)} sessioni")
        print(f"[Server] Data corrente: {self.replay_date}")
        print(f"[Server] Velocità default: {DEFAULT_REPLAY_SPEED}x")
        print(f"")
        print(f"[Server] Apri il frontend: cd deepchart-desktop && npm run dev")
        print(f"[Server] Poi vai su: http://localhost:5173")
        print(f"")

        # Avvia replay loop in background
        replay_task = asyncio.create_task(self.replay_loop())

        try:
            # Avvia server WebSocket (websockets v16+ usa websockets.serve)
            async with websockets.serve(
                self.handler,
                WS_HOST,
                WS_PORT,
                ping_interval=20,
                ping_timeout=10,
                max_size=10 * 1024 * 1024,  # 10MB max message
            ):
                print(f"[Server] [OK] Server avviato. Premere Ctrl+C per uscire.\n")
                await asyncio.Future()  # Blocca per sempre
        except KeyboardInterrupt:
            print(f"\n[Server] Interruzione ricevuta, chiusura...")
        finally:
            replay_task.cancel()
            try:
                await replay_task
            except asyncio.CancelledError:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Entry point principale."""
    server = DeepPrintServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[Server] Server fermato.")


if __name__ == '__main__':
    main()
