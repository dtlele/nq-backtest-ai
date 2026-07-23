"""
DAILY MAP — Mappa del giorno calcolata UNA volta alle 9:55 ET (1 sola chiamata LLM).

Cosa fa:
- Prende i dati di inizio giornata (overnight VP, IB parziale, day-type history, GEX)
- Restituisce un oggetto DailyMap con:
  - bias_regime: 'drive_up' / 'drive_down' / 'lean_up' / 'lean_down' / 'rotational'
  - primary_levels: {poc, vah, val, ib_high, ib_low, key_walls: [...]}
  - allowed_setups: ['pullback', 'squeeze', 'ivb_breakout', 'failed_auction']
  - max_trades: int
  - no_trade_zones: [(start_et, end_et), ...]
  - vah_to_poc_quality: 'aligned' / 'split' / 'wide'
  - generated_at_utc: datetime
  - llm_confidence: 0-100

La mappa viene usata per tutto il giorno da src.agents.mechanical_trigger.
La cache key include (date, bias_regime, primary_levels) -> riuso finche' la struttura
non cambia significativamente.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
import hashlib


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class DailyMap:
    date: str  # 'YYYY-MM-DD'
    bias_regime: str  # drive_up / drive_down / lean_up / lean_down / rotational
    bias_score: int  # -100..+100
    primary_levels: Dict[str, float]  # poc, vah, val, ib_high, ib_low
    key_walls: List[Dict]  # [{price, side, size, source}]
    allowed_setups: List[str]
    max_trades: int
    no_trade_zones: List[List[int]]  # [[start_h, start_m, end_h, end_m], ...]
    setup_priority: Dict[str, int]  # {'pullback': 90, 'squeeze': 70, ...}
    generated_at_utc: str
    llm_confidence: int
    reasoning: str

    def cache_key(self) -> str:
        """Key stabile: stessa data + stessa struttura = stessa mappa."""
        payload = json.dumps({
            'date': self.date,
            'bias_regime': self.bias_regime,
            'primary_levels': self.primary_levels,
            'key_walls': self.key_walls,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Prompt per la mappa (1 sola volta/giorno) ───────────────────────────

DAILY_MAP_PROMPT = """You are an NQ orderflow scalper building a DAILY TRADING MAP for today.
You will be given overnight volume profile, partial Initial Balance, day-type history,
and (if available) GEX levels. Based on this, output a structured plan for the day.

TASK:
1. BIAS: determine the institutional bias regime for today:
   - drive_up / drive_down (|score| >= 35): initiative participants control
   - lean_up / lean_down (15..35): trend preferred, counterbias limited
   - rotational (-15..+15): mean-reversion day

2. PRIMARY LEVELS: identify the 3-5 most important structural levels:
   - POC (Point of Control) of overnight OR developing RTH
   - VAH/VAL (Value Area High/Low)
   - IB High/Low (if complete)
   - Any obvious institutional levels from history

3. KEY WALLS: list 2-4 large Big Trade walls (>= 150 contracts) that may act as
   support/resistance today, with their size and side (BUY/SELL).

4. ALLOWED SETUPS: which of these setups make sense today:
   - pullback (against the bias, with absorption)
   - squeeze (consolidation before breakout)
   - ivb_breakout (Initial Value Breakout in drive)
   - failed_auction (rejection at value extreme in rotational)
   DO NOT include 'reversal' (globally disabled).

5. MAX TRADES: typical day 3-5. In strong drive: 4-6. In chop: 2-3.

6. NO TRADE ZONES: when NOT to enter:
   - 9:30-9:45 ET (opening rotation, fake breakouts)
   - 11:45-13:15 ET (lunch chop — OK only if drive_aligned)
   - 15:15-16:00 ET (EOD unwind)

7. SETUP PRIORITY: rank allowed setups 0-100 (higher = more confident).
   In a drive, the pullback to POC/VAH should rank highest.
   In chop, failed_auction at value extremes.

Output ONLY valid JSON:
{
  "bias_regime": "<drive_up|lean_up|rotational|lean_down|drive_down>",
  "bias_score": <int -100..+100>,
  "primary_levels": {"poc": <float>, "vah": <float>, "val": <float>, "ib_high": <float>, "ib_low": <float>},
  "key_walls": [{"price": <float>, "side": "BUY"|"SELL", "size": <int>}],
  "allowed_setups": ["pullback", "squeeze", ...],
  "max_trades": <int>,
  "setup_priority": {"pullback": <0-100>, "squeeze": <0-100>, ...},
  "no_trade_zones": [[9, 30, 9, 45], [11, 45, 13, 15], [15, 15, 16, 0]],
  "reasoning": "<max 80 words: why this bias and which setups are favored>"
}"""


# ── Cache locale per evitare di richiamare LLM se mappa già generata ─────

CACHE_DIR = Path("agent_memory") / "daily_maps"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(date_str: str) -> Path:
    return CACHE_DIR / f"map_{date_str}.json"


def load_cached_map(date_str: str) -> Optional[DailyMap]:
    """Carica mappa cached se esiste."""
    p = _cache_path(date_str)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            data = json.load(f)
        return DailyMap(**data)
    except Exception as e:
        print(f"[DAILY_MAP] Cache load error: {e}")
        return None


def save_map_to_cache(daily_map: DailyMap) -> None:
    """Salva mappa su disco per run futuri."""
    p = _cache_path(daily_map.date)
    with open(p, 'w') as f:
        json.dump(asdict(daily_map), f, indent=2, default=str)


# ── Generazione mappa (con o senza LLM) ─────────────────────────────────

def compute_bias_from_data(ctx, m1_bars_early) -> tuple:
    """Bias deterministico se LLM fallisce o e' disabilitato.
    Ritorna (regime, score, reasoning)."""
    score = 0
    drivers = []
    # IB extension
    if ctx.ib_high > 0 and ctx.ib_range > 0 and m1_bars_early:
        last_close = m1_bars_early[-1].close
        ext_up = last_close - ctx.ib_high
        ext_dn = ctx.ib_low - last_close
        if ext_up > 0.5 * ctx.ib_range:
            score += 30; drivers.append(f"DRIVE: {ext_up:.0f}pt sopra IB_high")
        elif ext_dn > 0.5 * ctx.ib_range:
            score -= 30; drivers.append(f"DRIVE: {ext_dn:.0f}pt sotto IB_low")
    # POC migration
    if hasattr(ctx, 'poc_migration_direction') and ctx.poc_migration_direction == 'up':
        score += 10; drivers.append("POC migrates up")
    elif hasattr(ctx, 'poc_migration_direction') and ctx.poc_migration_direction == 'down':
        score -= 10
    # VWAP position
    vwap = getattr(ctx, 'vwap', 0) or 0
    if vwap > 0 and m1_bars_early:
        last_close = m1_bars_early[-1].close
        if last_close > vwap:
            score += 8; drivers.append("sopra VWAP")
        else:
            score -= 8
    # Day type
    if getattr(ctx, 'day_type', '') == 'trend_up':
        score += 15; drivers.append("day_type=trend_up")
    elif getattr(ctx, 'day_type', '') == 'trend_down':
        score -= 15
    elif getattr(ctx, 'day_type', '') == 'balance':
        score *= 0.3; drivers.append("day_type=balance (reduce confidence)")
    
    if score >= 35: regime = 'drive_up'
    elif score >= 15: regime = 'lean_up'
    elif score <= -35: regime = 'drive_down'
    elif score <= -15: regime = 'lean_down'
    else: regime = 'rotational'
    
    return regime, score, '; '.join(drivers) or 'no drivers'


def generate_daily_map(date_str: str, ctx, m1_bars_early, use_llm: bool = True) -> DailyMap:
    """Genera la mappa del giorno. Usa LLM se use_llm=True, altrimenti deterministico."""
    # Check cache
    cached = load_cached_map(date_str)
    if cached:
        print(f"[DAILY_MAP] Cache hit for {date_str}: regime={cached.bias_regime}")
        return cached
    
    if not use_llm:
        regime, score, reasoning = compute_bias_from_data(ctx, m1_bars_early)
        return _build_default_map(date_str, regime, score, reasoning, llm_conf=50)
    
    # LLM call (1 volta/giorno)
    from src.agents.llm_client import llm_ask
    import os
    
    # Costruisci user_msg con dati overnight
    user_msg_parts = [f"DATE: {date_str}"]
    if ctx.vp:
        user_msg_parts.append(f"Overnight VP: POC={ctx.vp.poc:.2f} VAH={ctx.vp.va_high:.2f} VAL={ctx.vp.va_low:.2f}")
    if ctx.ib_high > 0:
        user_msg_parts.append(f"Partial IB: high={ctx.ib_high:.2f} low={ctx.ib_low:.2f} (range {ctx.ib_range:.1f})")
    if hasattr(ctx, 'day_type') and ctx.day_type:
        user_msg_parts.append(f"Day type (history-based): {ctx.day_type}")
    if hasattr(ctx, 'gex_regime') and ctx.gex_regime != 'unknown':
        user_msg_parts.append(f"GEX regime: {ctx.gex_regime}")
    # Recent big trades
    if m1_bars_early:
        big_trades = []
        for b in m1_bars_early[-30:]:
            for bt in getattr(b, 'big_trades', []) or []:
                if getattr(bt, 'size', 0) >= 150:
                    big_trades.append(f"@{bt.price:.2f} size={bt.size} {'B' if getattr(bt, 'is_buy', None) else 'S'}")
        if big_trades:
            user_msg_parts.append("Recent Big Trades:\n" + '\n'.join(big_trades[:10]))
    
    user_msg = "\n".join(user_msg_parts) + "\n\nGenerate the daily map JSON."
    
    # Usa lo stesso modello del reflex
    model = os.environ.get('OPENROUTER_MODEL', 'minimax/minimax-m2')
    print(f"[DAILY_MAP] Calling {model} for daily map of {date_str}...")
    raw = llm_ask(DAILY_MAP_PROMPT, user_msg, model=model, reasoning_effort='low', max_tokens=2000)
    
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[DAILY_MAP] JSON parse error: {e}. Falling back to deterministic.")
        regime, score, reasoning = compute_bias_from_data(ctx, m1_bars_early)
        return _build_default_map(date_str, regime, score, reasoning, llm_conf=30)
    
    return DailyMap(
        date=date_str,
        bias_regime=data.get('bias_regime', 'rotational'),
        bias_score=data.get('bias_score', 0),
        primary_levels={
            'poc': data.get('primary_levels', {}).get('poc', 0),
            'vah': data.get('primary_levels', {}).get('vah', 0),
            'val': data.get('primary_levels', {}).get('val', 0),
            'ib_high': data.get('primary_levels', {}).get('ib_high', 0),
            'ib_low': data.get('primary_levels', {}).get('ib_low', 0),
        },
        key_walls=data.get('key_walls', []),
        allowed_setups=data.get('allowed_setups', ['pullback', 'squeeze', 'ivb_breakout']),
        max_trades=data.get('max_trades', 3),
        no_trade_zones=data.get('no_trade_zones', [[9, 30, 9, 45], [11, 45, 13, 15], [15, 15, 16, 0]]),
        setup_priority=data.get('setup_priority', {}),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        llm_confidence=data.get('llm_confidence', 75),
        reasoning=data.get('reasoning', ''),
    )


def _build_default_map(date_str: str, regime: str, score: int, reasoning: str, llm_conf: int) -> DailyMap:
    """Mappa deterministica usata come fallback."""
    # Default levels da ctx
    return DailyMap(
        date=date_str,
        bias_regime=regime,
        bias_score=score,
        primary_levels={},  # will be filled by mechanical_trigger
        key_walls=[],
        allowed_setups=['pullback', 'squeeze', 'ivb_breakout', 'failed_auction'],
        max_trades=3,
        no_trade_zones=[[9, 30, 9, 45], [11, 45, 13, 15], [15, 15, 16, 0]],
        setup_priority={'pullback': 70, 'squeeze': 50, 'ivb_breakout': 60, 'failed_auction': 40},
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        llm_confidence=llm_conf,
        reasoning=f'FALLBACK (deterministic): {reasoning}',
    )
