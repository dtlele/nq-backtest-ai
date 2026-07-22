"""
Institutional Bias Engine — deterministico, zero costo LLM.

Calcola la direzione istituzionale della giornata dai dati GIÀ disponibili
nel motore (IB, POC migration, VWAP, value area, delta recente, day-type).
Nasce per colmare il buco strutturale trovato nell'audit del 03/02:
il day-type gate non può proteggere la PRIMA ORA (la classificazione usa
le close di sessione), quindi i 2 short killer delle 10:07/12:41 passarono
in una trend-up day. L'estensione oltre l'IB invece è osservabile in tempo
reale alle 10:00.

Output:
  score   -100..+100  (positivo = bias long istituzionale)
  regime  'drive_up' | 'lean_up' | 'rotational' | 'lean_down' | 'drive_down'
  drivers lista leggibile dei contributi (per prompt e log)

Soglie:
  |score| >= 35  → drive   (MAI operare contro; reversal vietato)
  15..35         → lean    (contro-bias solo con conviction alta + flow a favore)
  < 15           → rotational (mean-reversion ai bordi del valore consentita)
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class InstitutionalBias:
    score: float
    regime: str
    drivers: list = field(default_factory=list)

    @property
    def direction(self) -> str:
        if self.score >= 15:
            return 'long'
        if self.score <= -15:
            return 'short'
        return 'none'

    @property
    def is_drive(self) -> bool:
        return self.regime in ('drive_up', 'drive_down')

    def opposes(self, direction: str) -> bool:
        return (direction == 'short' and self.score > 0) or \
               (direction == 'long' and self.score < 0)

    def summary(self) -> str:
        d = "; ".join(self.drivers) if self.drivers else "no drivers"
        return (f"score={self.score:+.0f} regime={self.regime} "
                f"direction={self.direction} | {d}")


def _regime(score: float) -> str:
    if score >= 35:
        return 'drive_up'
    if score >= 15:
        return 'lean_up'
    if score <= -35:
        return 'drive_down'
    if score <= -15:
        return 'lean_down'
    return 'rotational'


def compute_institutional_bias(candidate) -> InstitutionalBias:
    """candidate: src.CandidateBar (o qualsiasi oggetto con gli stessi attributi)."""
    ctx = candidate.session_ctx
    bar = candidate.bar
    score = 0.0
    drivers = []

    # ── 1. IB EXTENSION DRIVE (il segnale di prima ora che mancava) ──────────
    # Prezzo oltre IB_high + 0.5×range = initiative buying accertato, osservabile
    # anche alle 10:00 quando day_type e' ancora 'balance'.
    ib_high = getattr(ctx, 'ib_high', 0) or 0
    ib_low = getattr(ctx, 'ib_low', 0) or 0
    ib_range = getattr(ctx, 'ib_range', 0) or (ib_high - ib_low if ib_high > ib_low else 0)
    if ib_high > 0 and ib_range > 0:
        ext_up = bar.close - ib_high
        ext_dn = ib_low - bar.close
        if ext_up > 0.5 * ib_range:
            score += 30
            drivers.append(f"DRIVE: close {ext_up:.0f}pt sopra IB_high (>0.5x range IB) = initiative buying")
        elif ext_up > 0:
            score += 12
            drivers.append(f"close sopra IB_high di {ext_up:.0f}pt")
        elif ext_dn > 0.5 * ib_range:
            score -= 30
            drivers.append(f"DRIVE: close {ext_dn:.0f}pt sotto IB_low (>0.5x range IB) = initiative selling")
        elif ext_dn > 0:
            score -= 12
            drivers.append(f"close sotto IB_low di {ext_dn:.0f}pt")

        # Primo breakout IB: il mercato ha votato per primo
        first_dir = getattr(ctx, 'ib_first_breakout_dir', 'none')
        n_bo = getattr(ctx, 'ib_breakouts_count', 0)
        if first_dir == 'long':
            score += 10 + min(6, 2 * max(0, n_bo - 1))
            drivers.append(f"primo breakout IB long ({n_bo} totali)")
        elif first_dir == 'short':
            score -= 10 + min(6, 2 * max(0, n_bo - 1))
            drivers.append(f"primo breakout IB short ({n_bo} totali)")

    # ── 2. POC MIGRATION (dove sta migrando il valore) ───────────────────────
    mig = getattr(candidate, 'poc_migration', 'flat')
    if mig == 'up':
        score += 15
        drivers.append("POC migration UP (valore accettato più in alto)")
    elif mig == 'down':
        score -= 15
        drivers.append("POC migration DOWN (valore accettato più in basso)")

    # ── 3. POSIZIONE VS VWAP ─────────────────────────────────────────────────
    vwap = getattr(candidate, 'vwap', 0) or 0
    if vwap > 0:
        if bar.close > vwap:
            score += 8
            drivers.append(f"sopra VWAP (+{bar.close - vwap:.0f}pt)")
        else:
            score -= 8
            drivers.append(f"sotto VWAP ({bar.close - vwap:.0f}pt)")

    # ── 4. ACCETTAZIONE VS VALUE AREA DEL GIORNO PRIMA ──────────────────────
    pvp = getattr(ctx, 'prev_day_vp', None)
    if pvp is not None:
        vah = getattr(pvp, 'va_high', 0) or 0
        val = getattr(pvp, 'va_low', 0) or 0
        if vah and bar.close > vah:
            score += 10
            drivers.append(f"accettazione SOPRA prev VAH {vah:.0f}")
        elif val and bar.close < val:
            score -= 10
            drivers.append(f"accettazione SOTTO prev VAL {val:.0f}")

    # ── 5. DAY TYPE (quando già accertato — pesa meno dell'IB drive) ────────
    dt = getattr(ctx, 'day_type', 'unknown')
    if dt == 'trend_up':
        score += 20
        drivers.append("day_type=trend_up")
    elif dt == 'trend_down':
        score -= 20
        drivers.append("day_type=trend_down")

    # ── 6. DELTA RECENTE (chi sta aggressendo nelle ultime barre) ───────────
    recent = (getattr(candidate, 'recent_bars', None) or [])[-6:]
    if recent:
        dsum = sum(getattr(b, 'delta', 0) for b in recent)
        if abs(dsum) >= 300:
            contrib = max(-12, min(12, dsum / 100))
            score += contrib
            drivers.append(f"delta cumulato ultime {len(recent)} barre: {dsum:+d}")

    # ── 7. SESSION BIAS DEL MOTORE + MARKET STRUCTURE ───────────────────────
    sb = getattr(candidate, 'session_bias', 'none')
    if sb == 'long':
        score += 8
        drivers.append("session_bias engine=long")
    elif sb == 'short':
        score -= 8
        drivers.append("session_bias engine=short")

    ms = str(getattr(ctx, 'market_structure_state', '') or '').lower()
    if 'hyperextended_up' in ms or 'trending_up' in ms:
        score += 5
        drivers.append(f"market_structure={ms}")
    elif 'hyperextended_down' in ms or 'trending_down' in ms:
        score -= 5
        drivers.append(f"market_structure={ms}")

    score = max(-100.0, min(100.0, score))
    return InstitutionalBias(score=score, regime=_regime(score), drivers=drivers)


# ── GATES per il validatore ──────────────────────────────────────────────────

def bias_gate(direction: str, setup_category: str, conviction: str,
              bias: InstitutionalBias) -> tuple:
    """Ritorna (ok, veto_reason, conviction_capped).

    Regole (derivate dagli errori reali del 03/02):
    1. DRIVE: mai contro un drive istituzionale → veto secco.
       (Copre la prima ora, dove il day-type gate era cieco.)
    2. REVERSAL/PULLBACK contro bias significativa (|score|>=25): il reversal
       e' compromesso se la bias non e' stata identificata → veto, a meno che
       conviction='high' (tutti gli elementi allineati contro-trend = possibile
       bias shift, lo lasciamo al Chief ma cappato a med).
    3. LEAN contro-bias: conviction cappata a 'med'.
    """
    if direction not in ('long', 'short'):
        return True, "", conviction

    # 1) drive gate — sostituisce il day-type gate nella prima ora
    if bias.regime == 'drive_up' and direction == 'short':
        return False, ("VETO: counter_institutional_drive (short contro drive_up, "
                       f"score {bias.score:+.0f})"), conviction
    if bias.regime == 'drive_down' and direction == 'long':
        return False, ("VETO: counter_institutional_drive (long contro drive_down, "
                       f"score {bias.score:+.0f})"), conviction

    # 2) reversal/pullback contro bias
    if setup_category in ('reversal', 'pullback') and bias.opposes(direction) \
            and abs(bias.score) >= 25:
        if conviction == 'high':
            # possibile bias shift: permesso ma mai a piena convinzione
            return True, "", 'med'
        return False, (f"VETO: reversal_against_bias ({setup_category} {direction} contro "
                       f"bias {bias.direction}, score {bias.score:+.0f})"), conviction

    # 3) lean contro-bias: pesa, non blocca
    if bias.opposes(direction) and abs(bias.score) >= 15 and conviction == 'high':
        conviction = 'med'

    return True, "", conviction
