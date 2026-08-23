"""
Configurazione centralizzata DeepPrint Pro.
Tutti i path e parametri sono qui — non hardcodati altrove.
"""
from pathlib import Path
import os

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
CACHE_OHLC_DIR = Path(os.environ.get('NQ_CACHE_OHLC_DIR', PROJECT_ROOT / 'cache_ohlc'))
AGENT_MEMORY_DIR = PROJECT_ROOT / "agent_memory"
DATA_DIR       = PROJECT_ROOT / "data"
OUTPUT_DIR     = PROJECT_ROOT / "output"

# ── WebSocket ─────────────────────────────────────────────────────────────────
WS_HOST = "localhost"
WS_PORT = 8765

# ── Replay defaults ───────────────────────────────────────────────────────────
# speed multiplier: 1.0 = tempo reale (1 M1 bar = 60s), 60.0 = 1 bar/s, 600 = 10 bars/s
DEFAULT_REPLAY_SPEED  = 60.0    # avvia a 60x (1 barra M1 ogni 1 secondo)
MAX_REPLAY_SPEED      = 99999.0 # MAX = nessun sleep
MAX_CANDLES_IN_MEMORY = 300     # M1 candles mantenute in memoria per client
MAX_M5_CANDLES        = 100

# ── Volume Profile ────────────────────────────────────────────────────────────
VP_UPDATE_EVERY_N_BARS = 1   # aggiorna VP ad ogni barra M1

# ── Agent trigger ─────────────────────────────────────────────────────────────
AGENT_EVAL_ENABLED     = False  # True per attivare agenti in replay
AGENT_EVAL_EVERY_N_BARS = 5
MIN_CONFIDENCE_ALERT   = 78

# ── NQ Constants (sincronizzati con src/__init__.py) ──────────────────────────
NQ_TICK_SIZE           = 0.25
NQ_TICK_VALUE          = 5.0
NQ_BIG_TRADE_THRESHOLD = 30
VA_PERCENTAGE          = 0.70
IB_DURATION_MIN        = 30

# Session NY window (ET)
NY_OPEN_H   = 9
NY_OPEN_M   = 30
NY_CLOSE_H  = 16
NY_CLOSE_M  = 0
FABIO_START_H = 9
FABIO_START_M = 35
FABIO_END_H   = 12
FABIO_END_M   = 30
