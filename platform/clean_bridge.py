"""
CleanBridge: accesso READ-ONLY agli artefatti di nq-backtest-clean.

Legge (senza MAI scrivere) i prodotti del motore di backtest principale:
- agent_memory/reasoning_log.jsonl   -> segnali agenti (Fabio/Andrea) per data
- agent_memory/trades_log.jsonl      -> trade eseguiti (entry/stop/target/exit/pnl)
- output/daily_roadmap_YYYY-MM-DD.json -> roadmap giornaliera (scenari bull/bear)
- agent_memory/quantitative_memory.json -> statistiche per regime|setup|wall

VINCOLO: nq-backtest-clean è gestito da un altro agente.
Questo modulo deve solo LEGGERE. Nessuna scrittura, nessuna modifica.
"""
import json
import os
from pathlib import Path
from datetime import datetime

# Root del progetto clean (READ-ONLY). Override via env NQ_CLEAN_ROOT.
CLEAN_ROOT = Path(os.environ.get(
    'NQ_CLEAN_ROOT',
    Path(__file__).parent.parent.parent / 'nq-backtest-clean'
))

REASONING_LOG = CLEAN_ROOT / 'agent_memory' / 'reasoning_log.jsonl'
TRADES_LOG = CLEAN_ROOT / 'agent_memory' / 'trades_log.jsonl'
QUANT_MEMORY = CLEAN_ROOT / 'agent_memory' / 'quantitative_memory.json'
ROADMAP_DIR = CLEAN_ROOT / 'output'


def _read_jsonl(path: Path) -> list:
    """Legge un file JSONL. Tollerante a righe corrotte."""
    if not path.exists():
        return []
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[CleanBridge] Riga {i+1} corrotta in {path.name}, saltata")
    return rows


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


class CleanBridge:
    """
    Indicizza gli artefatti di nq-backtest-clean per data.
    Singleton: caricamento lazy + cache in memoria.
    """

    def __init__(self, clean_root: Path = None):
        self.root = clean_root or CLEAN_ROOT
        self._reasoning_by_date: dict = {}   # date -> [record, ...]
        self._trades_by_date: dict = {}      # date -> [trade, ...]
        self._quant_memory: dict = {}
        self._loaded = False

    # ── Caricamento ──────────────────────────────────────────────────────────

    def load(self, force: bool = False):
        """Carica e indicizza tutti gli artefatti. Chiamata lazy al primo uso."""
        if self._loaded and not force:
            return
        t0 = datetime.now()

        self._reasoning_by_date = {}
        for rec in _read_jsonl(REASONING_LOG):
            d = rec.get('date')
            if d:
                self._reasoning_by_date.setdefault(d, []).append(rec)

        self._trades_by_date = {}
        for rec in _read_jsonl(TRADES_LOG):
            d = rec.get('date')
            if d:
                self._trades_by_date.setdefault(d, []).append(rec)

        if QUANT_MEMORY.exists():
            try:
                self._quant_memory = json.loads(QUANT_MEMORY.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"[CleanBridge] Errore lettura quantitative_memory: {e}")
                self._quant_memory = {}

        self._loaded = True
        dt = (datetime.now() - t0).total_seconds()
        n_cand = sum(len(v) for v in self._reasoning_by_date.values())
        n_tr = sum(len(v) for v in self._trades_by_date.values())
        print(f"[CleanBridge] Caricato in {dt:.2f}s — "
              f"{n_cand} candidati su {len(self._reasoning_by_date)} date, "
              f"{n_tr} trade su {len(self._trades_by_date)} date, "
              f"{len(self._quant_memory)} chiavi quantitative memory")

    def available_dates(self) -> list:
        """Date per cui esistono dati agenti (unione reasoning + trades)."""
        self.load()
        return sorted(set(self._reasoning_by_date) | set(self._trades_by_date))

    # ── Serializzatori verso il frontend ─────────────────────────────────────

    def get_agent_signals(self, date: str) -> list:
        """
        Converte i candidati del reasoning_log in messaggi 'agent_signal'
        compatibili col tipo già gestito da useWebSocket.ts.
        """
        self.load()
        out = []
        for rec in self._reasoning_by_date.get(date, []):
            decision = rec.get('decision', 'no_trade')
            out.append({
                'barTimeEt':      rec.get('bar_time_et', ''),
                'barTimeUtc':     rec.get('bar_time_utc', ''),
                'direction':      rec.get('fabio_direction') or rec.get('trade_direction') or '',
                'confidence':     _safe_int(rec.get('final_confidence')),
                'setupType':      rec.get('fabio_setup', ''),
                'finalDecision':  'trade' if decision == 'trade' else 'no_trade',
                'noTradeReason':  rec.get('no_trade_reason', ''),
                'reasoning':      rec.get('fabio_reasoning', ''),
                # Dettaglio esteso (nuovo pannello candidati)
                'detail': {
                    'fabio': {
                        'direction':   rec.get('fabio_direction', ''),
                        'confidence':  _safe_int(rec.get('fabio_confidence')),
                        'setup':       rec.get('fabio_setup', ''),
                        'entry':       _safe_float(rec.get('fabio_entry')),
                        'stop':        _safe_float(rec.get('fabio_stop')),
                        'target':      _safe_float(rec.get('fabio_target')),
                        'reasoning':   rec.get('fabio_reasoning', ''),
                        'imbalancePhase': rec.get('fabio_imbalance_phase', ''),
                    },
                    'andrea': {
                        'confirmation': rec.get('andrea_confirmation', ''),
                        'confidence':   _safe_int(rec.get('andrea_confidence')),
                        'setup':        rec.get('andrea_setup', ''),
                        'reasoning':    rec.get('andrea_reasoning', ''),
                    },
                    'context': {
                        'dayType':     rec.get('day_type', ''),
                        'marketState': rec.get('market_state', ''),
                        'macroRegime': rec.get('macro_regime', ''),
                        'poc':         _safe_float(rec.get('poc')),
                        'vaHigh':      _safe_float(rec.get('va_high')),
                        'vaLow':       _safe_float(rec.get('va_low')),
                        'ibHigh':      _safe_float(rec.get('ib_high')),
                        'ibLow':       _safe_float(rec.get('ib_low')),
                        'zeroGamma':   _safe_float(rec.get('zero_gamma')),
                        'callWall':    _safe_float(rec.get('call_wall')),
                        'putWall':     _safe_float(rec.get('put_wall')),
                        'wallLevel':   _safe_float(rec.get('wall_level')),
                        'wallSide':    rec.get('wall_side', ''),
                        'wallMaxSize': _safe_int(rec.get('wall_max_size')),
                        'proximityTo': rec.get('proximity_to', ''),
                        'proximityLevel': _safe_float(rec.get('proximity_level')),
                        'ignitionLabel': rec.get('ignition_label', ''),
                        'newsFlag':    rec.get('news_flag', ''),
                    },
                    'result': {
                        'pnlUsd':     _safe_float(rec.get('trade_pnl_usd')),
                        'pnlTicks':   _safe_float(rec.get('trade_pnl_ticks')),
                        'exitReason': rec.get('trade_exit_reason', ''),
                    },
                },
            })
        return out

    def get_trade_markers(self, date: str) -> list:
        """Trade del giorno come marker entry/exit/stop/target per il chart."""
        self.load()
        out = []
        for t in self._trades_by_date.get(date, []):
            out.append({
                'entryTime':  t.get('entry_time', ''),
                'exitTime':   t.get('exit_time', ''),
                'direction':  t.get('direction', ''),
                'entry':      _safe_float(t.get('entry')),
                'stop':       _safe_float(t.get('stop')),
                'target':     _safe_float(t.get('target')),
                'exitPrice':  _safe_float(t.get('exit_price')),
                'exitReason': t.get('exit_reason', ''),
                'pnlUsd':     _safe_float(t.get('pnl_usd')),
                'pnlTicks':   _safe_float(t.get('pnl_ticks')),
                'setupType':  t.get('setup_type', ''),
                'confidence': _safe_int(t.get('final_confidence')),
                'contracts':  _safe_int(t.get('contracts'), 1),
                'fabioReasoning':  t.get('fabio_reasoning', ''),
                'andreaReasoning': t.get('andrea_reasoning', ''),
            })
        return out

    def get_daily_roadmap(self, date: str) -> dict:
        """Roadmap giornaliera da output/daily_roadmap_YYYY-MM-DD.json."""
        path = ROADMAP_DIR / f'daily_roadmap_{date}.json'
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[CleanBridge] Errore lettura roadmap {date}: {e}")
            return None
        return {
            'date':            date,
            'contextAnalysis': data.get('context_analysis', ''),
            'bullish':         data.get('bullish_scenario', {}),
            'bearish':         data.get('bearish_scenario', {}),
            # campi opzionali presenti in alcune roadmap
            'keyLevels':       data.get('key_levels', []),
            'raw':             data,
        }

    def get_memory_stats(self) -> list:
        """Quantitative memory come lista ordinata per win rate."""
        self.load()
        out = []
        for key, s in self._quant_memory.items():
            parts = key.split('|')
            out.append({
                'key':       key,
                'regime':    parts[0] if len(parts) > 0 else '',
                'setup':     parts[1] if len(parts) > 1 else '',
                'wall':      parts[2] if len(parts) > 2 else '',
                'seen':      _safe_int(s.get('seen')),
                'wins':      _safe_int(s.get('wins')),
                'losses':    _safe_int(s.get('losses')),
                'winRate':   _safe_float(s.get('win_rate')),
                'totalPnlUsd': _safe_float(s.get('total_pnl_usd')),
            })
        out.sort(key=lambda x: -x['seen'])
        return out


# Singleton condiviso
_bridge = None

def get_bridge() -> CleanBridge:
    global _bridge
    if _bridge is None:
        _bridge = CleanBridge()
    return _bridge
