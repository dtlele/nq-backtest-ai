"""
MECHANICAL TRIGGER — Detector meccanico per setup M5. Zero LLM.

Processa ogni candida del candidate_detector e decide istantaneamente (<1ms):
1. Se il setup e' 'no_trade' per via di no_trade_zone/bias/no_wall: SKIP
2. Se il setup e' A+ (tutti i check passano): apri trade con SL/TP meccanici
3. Se il setup e' B (1 check borderline): chiedi LLM verifier (1 call)
4. Se il setup e' C (2+ check fail): SKIP

Risultato atteso: ~85% delle candide gestite senza LLM, ~10% con LLM verifier,
~5% skip puro.

L'LLM Fabio agent originale viene chiamato SOLO per:
- Generare la mappa del giorno (1 volta)
- Verificare setup borderline (max 5/giorno)
- Exception handling durante gestione trade (max 3/giorno)
"""

import math
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple


_ET_OFFSET = timedelta(hours=-5)


def to_et(ts_utc: datetime) -> datetime:
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    return ts_utc.astimezone(timezone(_ET_OFFSET)).replace(tzinfo=None)


def is_in_no_trade_zone(ts_utc: datetime, no_trade_zones: List[List[int]]) -> Tuple[bool, str]:
    """Controlla se il timestamp cade in una no_trade_zone.
    Ritorna (in_zone, zone_description)."""
    et = to_et(ts_utc)
    h, m = et.hour, et.minute
    cur = h * 60 + m
    for zone in no_trade_zones:
        if len(zone) >= 4:
            start = zone[0] * 60 + zone[1]
            end = zone[2] * 60 + zone[3]
            if start <= cur < end:
                names = {0: 'opening_rotation', 1: 'lunch_chop', 2: 'late_session'}
                kind = names.get(zone[0] % 3, 'no_trade')
                return True, f"NO_TRADE_ZONE ({kind} {zone[0]}:{zone[1]:02d}-{zone[2]}:{zone[3]:02d} ET)"
    return False, ""


@dataclass
class TriggerVerdict:
    """Risultato del trigger meccanico per una candida."""
    decision: str  # 'open', 'verify_with_llm', 'skip'
    confidence: int  # 0-100
    setup_type: str  # 'pullback', 'squeeze', etc.
    direction: Optional[str]  # 'long', 'short', None
    sl: Optional[float]
    tp: Optional[float]
    rr: float
    reasons: List[str]  # pass/fail reasons for each check
    needs_llm_reason: str  # why we need LLM (if verify_with_llm)


def check_pullback_setup(bar, recent_bars, daily_map) -> Tuple[float, str, str, str]:
    """Score per pullback su livello.
    Returns: (score, direction, sl_reason, tp_reason)."""
    direction = 'none'
    score = 0
    sl_reason = ""
    tp_reason = ""
    
    if not daily_map or not daily_map.primary_levels:
        return 0, 'none', '', ''
    
    levels = daily_map.primary_levels
    
    # Check long: bar chiude DENTRO il value area o sotto, ma rimbalza
    if 'pullback' in daily_map.allowed_setups:
        for level_name, level_price in [
            ('val', levels.get('val', 0)),
            ('poc', levels.get('poc', 0)),
            ('ib_low', levels.get('ib_low', 0)),
        ]:
            if level_price <= 0:
                continue
            # Long se: low tocca livello +/- 5pt, close > open, delta > 0
            if (bar.low <= level_price + 5 and 
                bar.close >= level_price - 5 and
                bar.close > bar.open and
                bar.delta > 0):
                if daily_map.bias_regime in ('drive_up', 'lean_up', 'rotational'):
                    score = 75
                    direction = 'long'
                    sl_reason = f"below {level_name}={level_price:.2f} (close > open, delta > 0)"
                    # TP = next structural level above
                    tp_level = max([v for n, v in levels.items() if n in ('poc', 'vah', 'ib_high') and v > bar.close] or [0])
                    if tp_level > 0:
                        tp_reason = f"above {tp_level:.2f}"
                    return score, direction, sl_reason, tp_reason
            
            # Short se: high tocca livello, close < open, delta < 0
            if (bar.high >= level_price - 5 and
                bar.close <= level_price + 5 and
                bar.close < bar.open and
                bar.delta < 0):
                if daily_map.bias_regime in ('drive_down', 'lean_down', 'rotational'):
                    score = 75
                    direction = 'short'
                    sl_reason = f"above {level_name}={level_price:.2f} (close < open, delta < 0)"
                    tp_level = min([v for n, v in levels.items() if n in ('poc', 'val', 'ib_low') and v > 0 and v < bar.close] or [999999])
                    if tp_level < 999999:
                        tp_reason = f"below {tp_level:.2f}"
                    return score, direction, sl_reason, tp_reason
    
    return 0, 'none', '', ''


def check_squeeze_setup(bar, recent_bars, daily_map) -> Tuple[float, str, str, str]:
    """Score per squeeze (range stretto prima di breakout).
    Returns: (score, direction, sl_reason, tp_reason)."""
    if not daily_map or 'squeeze' not in daily_map.allowed_setups:
        return 0, 'none', '', ''
    if not recent_bars or len(recent_bars) < 4:
        return 0, 'none', '', ''
    
    # Range ultimi 4 bar stretto (< 30pt = 120 ticks NQ)
    last_4 = recent_bars[-4:]
    range_pts = max(b.high for b in last_4) - min(b.low for b in last_4)
    if range_pts > 35:
        return 0, 'none', '', ''
    
    # Breakout long: close > high degli ultimi 4 bar, delta > 0
    range_high = max(b.high for b in last_4)
    range_low = min(b.low for b in last_4)
    if bar.close > range_high and bar.delta > 0:
        if daily_map.bias_regime in ('drive_up', 'lean_up', 'rotational'):
            return 70, 'long', f"below range_low={range_low:.2f}", f"above POC/VaH"
    # Breakout short: close < low degli ultimi 4 bar, delta < 0
    if bar.close < range_low and bar.delta < 0:
        if daily_map.bias_regime in ('drive_down', 'lean_down', 'rotational'):
            return 70, 'short', f"above range_high={range_high:.2f}", f"below POC/VAL"
    
    return 0, 'none', '', ''


def check_ivb_setup(bar, recent_bars, daily_map) -> Tuple[float, str, str, str]:
    """IVB = Initial Value Breakout. Price breaks IB_high (long) or IB_low (short).
    Returns: (score, direction, sl_reason, tp_reason)."""
    if not daily_map or 'ivb_breakout' not in daily_map.allowed_setups:
        return 0, 'none', '', ''
    if daily_map.bias_regime not in ('drive_up', 'drive_down', 'lean_up', 'lean_down'):
        return 0, 'none', '', ''
    
    ib_high = daily_map.primary_levels.get('ib_high', 0)
    ib_low = daily_map.primary_levels.get('ib_low', 0)
    if ib_high <= 0 or ib_low <= 0:
        return 0, 'none', '', ''
    
    # Long IVB: close > ib_high, delta > 0
    if (bar.close > ib_high and bar.delta > 0 and
        daily_map.bias_regime in ('drive_up', 'lean_up')):
        # Stop below IB midpoint
        ib_mid = (ib_high + ib_low) / 2
        return 80, 'long', f"below IB_mid={ib_mid:.2f}", f"above VAH={daily_map.primary_levels.get('vah', 0):.2f}"
    
    # Short IVB: close < ib_low, delta < 0
    if (bar.close < ib_low and bar.delta < 0 and
        daily_map.bias_regime in ('drive_down', 'lean_down')):
        ib_mid = (ib_high + ib_low) / 2
        return 80, 'short', f"above IB_mid={ib_mid:.2f}", f"below VAL={daily_map.primary_levels.get('val', 0):.2f}"
    
    return 0, 'none', '', ''


def check_failed_auction_setup(bar, recent_bars, daily_map) -> Tuple[float, str, str, str]:
    """Failed auction = rejection a value extreme. Bar probes level and closes back inside.
    Returns: (score, direction, sl_reason, tp_reason)."""
    if not daily_map or 'failed_auction' not in daily_map.allowed_setups:
        return 0, 'none', '', ''
    if daily_map.bias_regime != 'rotational':
        return 0, 'none', '', ''
    
    levels = daily_map.primary_levels
    # Long failed auction: bar probes VAL/IB_low, closes back inside
    val = levels.get('val', 0)
    ib_low = levels.get('ib_low', 0)
    
    for level_name, level_price in [('val', val), ('ib_low', ib_low)]:
        if level_price <= 0:
            continue
        if (bar.low < level_price and 
            bar.close > level_price and
            bar.delta > 0):  # buyers defended
            return 70, 'long', f"below {level_name}={level_price:.2f}", f"above POC={levels.get('poc', 0):.2f}"
    
    # Short failed auction: probes VAH/IB_high, closes back inside
    vah = levels.get('vah', 0)
    ib_high = levels.get('ib_high', 0)
    for level_name, level_price in [('vah', vah), ('ib_high', ib_high)]:
        if level_price <= 0:
            continue
        if (bar.high > level_price and 
            bar.close < level_price and
            bar.delta < 0):  # sellers defended
            return 70, 'short', f"above {level_name}={level_price:.2f}", f"below POC={levels.get('poc', 0):.2f}"
    
    return 0, 'none', '', ''


def compute_sl_tp_mechanical(candidate, daily_map, direction: str) -> Tuple[Optional[float], Optional[float], float]:
    """Calcola SL e TP meccanicamente.
    Returns: (sl, tp, rr) o (None, None, 0) se impossibile."""
    if not daily_map:
        return None, None, 0.0
    
    levels = daily_map.primary_levels
    bar = candidate.bar
    entry = bar.close
    
    # SL: preferibilmente dietro wall, fallback dietro livello strutturale
    sl = None
    
    # 1. Wall defense (se size > 0)
    if candidate.wall_level > 0 and candidate.wall_trade_count > 0:
        if direction == 'long' and candidate.wall_level < entry:
            sl = candidate.wall_level - 0.5
        elif direction == 'short' and candidate.wall_level > entry:
            sl = candidate.wall_level + 0.5
    
    # 2. Fallback dietro livello strutturale
    if sl is None and levels:
        if direction == 'long':
            for level_name in ['val', 'ib_low', 'poc']:
                lv = levels.get(level_name, 0)
                if lv > 0 and lv < entry:
                    sl = lv - 2.0  # buffer
                    break
        else:
            for level_name in ['vah', 'ib_high', 'poc']:
                lv = levels.get(level_name, 0)
                if lv > 0 and lv > entry:
                    sl = lv + 2.0
                    break
    
    if sl is None:
        return None, None, 0.0
    
    risk = abs(entry - sl)
    if risk < 2.0:
        return None, None, 0.0
    
    # TP: livello opposto strutturale, R:R >= 1.5
    tp = None
    if levels:
        if direction == 'long':
            for level_name in ['poc', 'vah', 'ib_high']:
                lv = levels.get(level_name, 0)
                if lv > 0 and lv >= entry + 1.5 * risk:
                    tp = lv
                    break
        else:
            for level_name in ['poc', 'val', 'ib_low']:
                lv = levels.get(level_name, 0)
                if lv > 0 and lv <= entry - 1.5 * risk:
                    tp = lv
                    break
    
    # Measured move fallback in drive
    if tp is None and daily_map.bias_regime in ('drive_up', 'drive_down'):
        ib_range = abs(levels.get('ib_high', 0) - levels.get('ib_low', 0))
        if ib_range > 0:
            if direction == 'long':
                tp = entry + ib_range
            else:
                tp = entry - ib_range
    
    if tp is None:
        return sl, None, 0.0
    
    rr = abs(tp - entry) / risk
    if rr < 1.5:
        return sl, None, 0.0
    
    return sl, tp, rr


def evaluate_candidate(candidate, recent_bars, daily_map, ctx) -> TriggerVerdict:
    """Valuta una candida con il trigger meccanico.
    Returns TriggerVerdict con decisione, confidence, e motivo."""
    bar = candidate.bar
    reasons = []
    
    # CHECK 1: No trade zone
    in_zone, zone_desc = is_in_no_trade_zone(bar.timestamp, daily_map.no_trade_zones)
    if in_zone:
        return TriggerVerdict(
            decision='skip', confidence=0, setup_type='none', direction=None,
            sl=None, tp=None, rr=0, reasons=[f"NO_TRADE_ZONE: {zone_desc}"],
            needs_llm_reason=''
        )
    
    # CHECK 2: Wall valido
    if candidate.wall_level <= 0 or candidate.wall_trade_count == 0:
        # No wall = no A+ setup. Verifica se c'è un Big Trade >= 150
        big_trade_found = False
        for b in (recent_bars or [])[-6:]:
            for bt in getattr(b, 'big_trades', []) or []:
                if getattr(bt, 'size', 0) >= 150:
                    if direction_match(bt, direction='any') and near_entry(bt, bar.close):
                        big_trade_found = True
                        break
            if big_trade_found:
                break
        if not big_trade_found:
            return TriggerVerdict(
                decision='skip', confidence=0, setup_type='none', direction=None,
                sl=None, tp=None, rr=0, reasons=['NO_WALL: no structural defense'],
                needs_llm_reason=''
            )
        reasons.append('wall_from_bigtrade (no candidate.wall but recent Big Trade)')
    
    # CHECK 3: Volume
    if recent_bars and len(recent_bars) >= 3:
        recent_vol = sum(b.volume for b in recent_bars[-3:])
        avg_vol = sum(b.volume for b in recent_bars) / max(len(recent_bars), 1)
        vol_ratio = recent_vol / (3 * avg_vol) if avg_vol > 0 else 0
        if vol_ratio < 0.5:
            return TriggerVerdict(
                decision='skip', confidence=0, setup_type='none', direction=None,
                sl=None, tp=None, rr=0, 
                reasons=[f'LOW_VOLUME: ratio={vol_ratio:.0%} < 50%'],
                needs_llm_reason=''
            )
    
    # CHECK 4: Bias alignment (skip se drive diretto opposto)
    bias = daily_map.bias_regime
    # Prova ciascun setup pattern
    best = (0, 'none', '', '')
    
    s, d, slr, tpr = check_pullback_setup(bar, recent_bars, daily_map)
    if s > best[0]: best = (s, d, slr, tpr)
    
    s, d, slr, tpr = check_squeeze_setup(bar, recent_bars, daily_map)
    if s > best[0]: best = (s, d, slr, tpr)
    
    s, d, slr, tpr = check_ivb_setup(bar, recent_bars, daily_map)
    if s > best[0]: best = (s, d, slr, tpr)
    
    s, d, slr, tpr = check_failed_auction_setup(bar, recent_bars, daily_map)
    if s > best[0]: best = (s, d, slr, tpr)
    
    score, direction, sl_reason, tp_reason = best
    
    if direction == 'none' or score < 60:
        return TriggerVerdict(
            decision='skip', confidence=score, setup_type='none', direction=None,
            sl=None, tp=None, rr=0, reasons=['NO_PATTERN_MATCH'],
            needs_llm_reason=''
        )
    
    # CHECK 5: SL/TP computation
    # We need a synthetic candidate to call compute_sl_tp_mechanical
    class _FakeCand:
        def __init__(self, c, d):
            self.wall_level = c.wall_level
            self.wall_trade_count = c.wall_trade_count
            self.bar = c.bar
    
    fake = _FakeCand(candidate, direction)
    sl, tp, rr = compute_sl_tp_mechanical(fake, daily_map, direction)
    if sl is None or tp is None:
        return TriggerVerdict(
            decision='skip', confidence=score, setup_type='none', direction=direction,
            sl=None, tp=None, rr=0, reasons=['NO_VALID_SL_OR_TP'],
            needs_llm_reason=''
        )
    
    # CHECK 6: confidence score
    if score >= 75:
        return TriggerVerdict(
            decision='open', confidence=score, setup_type='auto_detected',
            direction=direction, sl=sl, tp=tp, rr=rr,
            reasons=reasons + [f'score={score} >= 75 (A+ setup, no LLM needed)'],
            needs_llm_reason=''
        )
    elif score >= 60:
        return TriggerVerdict(
            decision='verify_with_llm', confidence=score, setup_type='auto_detected',
            direction=direction, sl=sl, tp=tp, rr=rr,
            reasons=reasons + [f'score={score} in [60, 75) (B setup, needs LLM)'],
            needs_llm_reason=f'Pattern matched but score is borderline ({score}). Need LLM to confirm confluence of bias + level + flow.'
        )
    else:
        return TriggerVerdict(
            decision='skip', confidence=score, setup_type='none', direction=direction,
            sl=sl, tp=tp, rr=rr, reasons=reasons + [f'score={score} < 60 (C setup, skip)'],
            needs_llm_reason=''
        )


def direction_match(big_trade, direction: str) -> bool:
    """True if the big_trade supports the direction."""
    if direction == 'any':
        return True
    is_buy = getattr(big_trade, 'is_buy', None)
    if is_buy is None:
        return True  # can't determine, accept
    if direction == 'long' and is_buy:
        return True
    if direction == 'short' and not is_buy:
        return True
    return False


def near_entry(big_trade, entry: float, tolerance_pts: float = 10.0) -> bool:
    """True if big_trade is within tolerance of entry."""
    return abs(getattr(big_trade, 'price', 0) - entry) <= tolerance_pts
