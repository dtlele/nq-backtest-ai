"""
Meccanici desk-grade gates — zero LLM, eseguiti PRIMA del reflex.
Risparmiano chiamate LLM e bloccano i setup noti-perdenti prima dell'analisi.

Gates implementati:
  1. TIME GATE: veto opening rotation (9:30-9:45 ET), lunch chop non allineato,
     late session (15:15+ ET). Restituisce anche orari ET per audit/replay.
  2. PARTICIPATION FILTER: vol < 50% media recente = rumore, veto.
  3. STRUCTURAL ANCHOR CHECK: se il setup propone entry ma wall + big trades
     entrambi vuoti = setup "in the middle of nowhere", veto.

Usage:
  from src.agents.desk_gates import check_desk_gates
  veto = check_desk_gates(candidate, direction, bias_regime)
  if veto: print(f"  [GATE VETO] {veto}")
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# ET offset (handles EST/EDT via fixed -5h/-4h; NQ RTH = EST-5 in winter, EDT-4 in summer)
# Per il backtest usiamo -5h (ET standard, NQ futures usa sempre ET)
_ET_OFFSET = timedelta(hours=-5)


def to_et(ts_utc: datetime) -> datetime:
    """Converte UTC -> ET per time gate."""
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    return ts_utc.astimezone(timezone(_ET_OFFSET)).replace(tzinfo=None)


def check_time_gate(ts: datetime, direction: str, bias_regime: str = 'rotational') -> Optional[str]:
    """
    Veto per orari pericolosi.
    - 9:30-9:45 ET: opening rotation = nessun trade (rumore, gap fake)
    - 11:45-13:15 ET: lunch chop = veto salvo drive_aligned
    - 15:15-16:00 ET: late session = nessun trade (EOD unwind, istituzionali chiudono)
    Ritorna stringa con motivo del veto, o None se passa.
    """
    et = to_et(ts)
    hhmm = et.hour * 60 + et.minute

    # Opening rotation 9:30-9:45
    if 9*60+30 <= hhmm < 9*60+45:
        return f"OPENING_ROTATION (9:30-9:45 ET) — fake breakouts/spikes frequenti"

    # Lunch chop 11:45-13:15
    if 11*60+45 <= hhmm < 13*60+15:
        # In drive regime, pranzare al drive e' ok (continuazione del trend)
        if 'drive' in bias_regime:
            return None
        return f"LUNCH_CHOP (11:45-13:15 ET) — bias={bias_regime}, no drive alignment"

    # Late session 15:15-16:00
    if 15*60+15 <= hhmm < 16*60:
        return f"LATE_SESSION (15:15-16:00 ET) — EOD unwind, istituzionali chiudono"

    return None


def check_participation(bar, recent_bars: list, min_ratio: float = 0.5) -> Optional[str]:
    """
    Veto se volume < 50% della media delle ultime 6 barre.
    Volume basso = nessuna iniziativa istituzionale = rumore retail.
    """
    if not recent_bars or len(recent_bars) < 3:
        return None
    vols = [b.volume for b in recent_bars if b.volume > 0]
    if len(vols) < 3:
        return None
    avg = sum(vols) / len(vols)
    if avg == 0:
        return None
    ratio = bar.volume / avg
    if ratio < min_ratio:
        return f"LOW_PARTICIPATION (vol={bar.volume} = {ratio:.0%} di avg {avg:.0f})"
    return None


def has_structural_anchor(candidate, direction: str) -> tuple:
    """
    Verifica se esiste un livello strutturale valido per l'entry.
    Controlla in ordine:
      1. candidate.wall_level con wall_trade_count > 0
      2. Big Trade >= 150 contracts sul lato corretto nelle ultime 6 barre
      3. Prossimita' a livello VP (POC/VAH/VAL) gia' nel candidate
    Ritorna (has_anchor, source_string).
    """
    if direction not in ('long', 'short'):
        return (True, "no_direction_check")

    # 1. Wall dal candidate
    if candidate.wall_level > 0 and candidate.wall_trade_count > 0:
        if direction == 'long' and candidate.wall_level < candidate.bar.close:
            return (True, f"candidate.wall @ {candidate.wall_level} (n={candidate.wall_trade_count})")
        if direction == 'short' and candidate.wall_level > candidate.bar.close:
            return (True, f"candidate.wall @ {candidate.wall_level} (n={candidate.wall_trade_count})")

    # 2. Big Trade >= 150 contracts sul lato corretto
    bars = (candidate.recent_bars or [])[-6:]
    for b in bars:
        for bt in getattr(b, 'big_trades', []) or []:
            if getattr(bt, 'size', 0) < 150:
                continue
            if direction == 'long' and bt.price < candidate.bar.close:
                return (True, f"BigTrade @ {bt.price} size={bt.size} (recent_bar)")
            if direction == 'short' and bt.price > candidate.bar.close:
                return (True, f"BigTrade @ {bt.price} size={bt.size} (recent_bar)")

    # 3. Prossimita' a livello VP gia' nota
    if candidate.proximity_to and candidate.proximity_to not in ('none', 'm1_feed'):
        return (True, f"VP proximity: {candidate.proximity_to} @ {candidate.proximity_level}")

    return (False, "no_wall_no_bigtrade_no_vp_proximity")


def check_desk_gates(candidate, direction: str, bias_regime: str = 'rotational') -> Optional[str]:
    """
    Gate aggregator: esegue tutti i check meccanici in sequenza.
    Ritorna il PRIMO veto trovato, o None se tutti passano.
    """
    if direction not in ('long', 'short'):
        return None

    bar = candidate.bar
    recent = candidate.recent_bars or []

    # 1. Time gate
    v = check_time_gate(bar.timestamp, direction, bias_regime)
    if v: return v

    # 2. Participation
    v = check_participation(bar, recent)
    if v: return v

    # 3. Structural anchor
    has_anchor, src = has_structural_anchor(candidate, direction)
    if not has_anchor:
        return f"NO_STRUCTURAL_ANCHOR ({src}) — entry without wall/bigtrade/VP proximity"

    return None
