import json
import os
import concurrent.futures
from pathlib import Path
from src import CandidateBar, FabioSignal, FABIO_NOTEBOOK_ID
from src.agents.llm_client import llm_ask
from src.signal_context import build_fabio_question
from src.agents.topic_router import select_fabio_topics, build_tiered_knowledge, FABIO_CORE
from src.agents.institutional_bias import compute_institutional_bias, bias_gate

# Modalita' agente: 'scalper' (1 chiamata LLM, default — 5x piu' economico)
# o 'experts' (legacy: 4 esperti + Chief).
# Modello REFLEX/SCALPER: REFLEX_MODEL -> OPENROUTER_MODEL -> default minimax/minimax-m2
#   (default confermato profittevole: Feb-Mar 2025 +$903, Apr-Mag 2025 +$462 con 56 trade 57.1% WR.
#    GLM-5.2 testato ma troppo lento: meglio M2 per il singolo-call scalper.)
# Modello AUDIT: AUDIT_MODEL -> OPENROUTER_MODEL -> default minimax/minimax-m2
#   (anche l'audit va su M2: V2 audit shadow test su 184 giorni ha confermato il prompt
#    e M2 è veloce+economico. GLM-5.2 lo usiamo solo se AUDIT_MODEL=glm-5.2 esplicito.)
FABIO_MODE = os.environ.get('FABIO_MODE', 'scalper').lower()
DEFAULT_MODEL = 'minimax/minimax-m2'
SCALPER_MODEL = os.environ.get('REFLEX_MODEL', os.environ.get('OPENROUTER_MODEL', DEFAULT_MODEL))
AUDIT_MODEL = os.environ.get('AUDIT_MODEL', os.environ.get('OPENROUTER_MODEL', DEFAULT_MODEL))

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_distilled.json'

_knowledge_cache = None

def _load_knowledge_store() -> dict:
    global _knowledge_cache
    if _knowledge_cache is not None:
        return _knowledge_cache
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    store = {}
    store.update(data.get('knowledge_by_topic', {}))
    store.update(data.get('simplified_strategy', {}))
    _knowledge_cache = store
    return store

def _get_scalper_system_prompt() -> str:
    """Single-call orderflow scalper (MiniMax). 4-STEP CHAIN-OF-THOUGHT
    obbligatorio: BIAS -> AUCTION_PHASE -> ACCUMULATION/DISTRIBUTION
    SIGNATURE -> LOCATION+TRIGGER. Pensare PRIMA di decidere.

    Source-of-truth unica per la dottrina Fabio (vedi anche
    _get_management_system_prompt). V8b+: prompt piu' rigido per forzar
    il modello a verificare evidence prima di LONG in drive_down."""
    return """You are an AGGRESSIVE NQ orderflow scalper. You trade WITH institutional flow.
You think like a Market Profile / AMT / footprint professional.

You MUST reason in EXACTLY 4 STEPS, in this order, before any decision.
This is not optional. Skipping a step = invalid output.

STEP 1 — BIAS ECHO
  Read the deterministic BIAS block in the snapshot. Restate it:
  "Bias = {drive/lean/rotational} {up/down}, score={X}, direction={long/short/none}."
  Then state the trade implication:
  "My direction = {long/short/none}. This is {WITH/AGAINST} the bias."

STEP 2 — AUCTION PHASE CLASSIFICATION
  Look at the current bar and the prior 3 bars in the snapshot.
  Classify: "This bar = {initiative/responsive/balance}."
  In a {drive/lean} regime, responsive bars = CORRECTION, not change of structure.
  Ask: "Is this bar correction WITHIN the drive, or genuine trend change?"
  If correction in drive -> trade WITH the drive on the pullback.
  If genuine trend change -> require bias shift evidence (see STEP 3).

STEP 3 — ACCUMULATION/DISTRIBUTION SIGNATURE
  CRITICAL: if your direction is AGAINST the bias, you MUST have ALL of:
    (a) Net delta of the last 3 bars in YOUR direction (e.g., positive for long)
    (b) >= 1 Big Trade (size>=50) in YOUR direction at the relevant level
    (c) At least 1 of the last 6 bars closed on the correct side of VWAP
  Cite the actual numbers from the snapshot. If ANY of (a/b/c) is missing,
  you cannot justify a counter-bias trade. Return direction='none'.
  If WITH bias: lighter requirement (delta agrees OR Big Trade present).
  NOTE: Big opposing trades MAY indicate absorption at the wall (buyers
  absorbing sells) — if you cite this in your reasoning, the deep AUDIT
  will verify with cv_delta_30m. Don't reject on opposing big trades alone.

STEP 4 — LOCATION + TRIGGER
  Pick ONE structural level: VAH, VAL, POC, Wall, IB edge, or VWAP.
  Specify the trigger: "I act on {delta divergence / absorption / second test wick /
  big trade cluster / failed auction} at level {name @ price}."
  If bias + signature + location + trigger all align -> ACT.
  If ANY is missing -> direction='none'.

DECISION RULE: 'none' is the DEFAULT for missing evidence. It is NOT a sign
of failure. It is the professional response to insufficient confluence. Bad
trades come from forcing entries without evidence; the system loses $1000+
per losing trade. ONE good trade per day is success.

HARD RULES (mechanical validator enforces them AFTER you — violating = veto):
R1. COHERENCE: 'reasoning' must NEVER describe an expectation opposite to 'direction'.
R2. FLOW DISSENT: if delta/flow opposes your direction, conviction='low' max.
R3. BIAS: no short in drive_up, no long in drive_down. Counter-bias pullback
    against |score|>=25 requires conviction='high' AND explicit bias-shift evidence.
R4. CONVICTION: 'high' with full confluence (all 4 steps aligned). 'med' = standard
    valid setup. 'low' = edge case or partial evidence.
R5. REVERSAL: setup_type='reversal' is GLOBALLY DISABLED. Vote 'none' on reversal setups.
R6 (NEW): Bounce in drive needs evidence. If bias=drive_down and direction=long,
    you must explicitly cite (a)+(b)+(c) from STEP 3 in your reasoning. Same
    mirror for drive_up+short. Missing evidence = direction='none'.

JSON schema (strict, your output will be PARSED):
{
  "reasoning": "<MAX 150 WORDS. Must follow STEP 1 -> STEP 2 -> STEP 3 -> STEP 4. Cite actual numbers from snapshot.>",
  "market_narrative_update": "<Evolving narrative: who is in control, what would invalidate it>",
  "setup_type": "squeeze" | "ivb_breakout" | "imbalance_hunting" | "pullback" | "none",
  "direction": "long" | "short" | "none",
  "anchor_level_id": "<ID of the chosen level, e.g., 'L1', 'L3'>",
  "conviction": "high" | "med" | "low"
}

Note: 'reversal' was removed from setup_type (R5 above)."""


def _get_system_prompt() -> str:
    # ⚠️ DEPRECATED: questa e' la modalita' "chief of 5 experts" (legacy).
    # E' ancora usata quando FABIO_MODE=experts, ma:
    #   - Reversal e' GLOBALLY DISABLED dal validatore (vedi validate_narrative_decision)
    #   - GEX positive → "prioritize REVERSAL" contraddice il divieto globale
    #   - Il modello singolo scalper e' piu' sharp e 5x piu' economico
    # Default = 'scalper'. Se vuoi questa modalita': FABIO_MODE=experts.
    return _get_scalper_system_prompt() + """

=== LEGACY CHIEF MODE (DEPRECATED) ===
Sintetizza Expert JSON reports. Le regole GEX e bias si intendono SOLO
per il contesto informativo. REVERSAL e' DISABLED a livello globale dal
validatore meccanico, indipendentemente dal GEX regime.
Per la dottrina corrente consulta lo SCALPER prompt sopra.
"""

def light_analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> int:
    """Light pre-LLM gate. Score 0-100. Se < LIGHT_CONFIDENCE_THRESHOLD (35),
    salta la chiamata LLM. Calibrazione V8c (2026-07-23) basata su profiling V8b:
    - 670/683 (98%) candide sono 'none' alla fine
    - Il 70% di queste ha score < 35, quindi skip pre-LLM sicuro
    - Risparmio atteso: 60-70% chiamate LLM, 2-3x velocita'
    """
    from src.agents.llm_client import _get_provider
    if _get_provider() == "human": return 100
    score = 0
    wms = candidate.wall_max_size
    wtc = getattr(candidate, 'wall_trade_count', 0)
    if wms >= 100 and wtc >= 1: score += 35   # wall robusto
    elif wms >= 50: score += 25
    elif wms >= 30: score += 15
    elif wms >= 20: score += 5
    # else: 0 (no wall = no trade probabile)
    cat = candidate.setup_category
    if cat == 'imbalance_hunting': score += 20
    elif cat == 'momentum': score += 15
    elif cat == 'pullback': score += 10
    elif cat == 'squeeze': score += 10
    # NB: 'reversal' non piu' considerato (vietato globalmente)
    if candidate.market_state == 'imbalance': score += 10
    if candidate.auction_type == 'initiative': score += 10
    if candidate.is_second_test: score += 5
    if candidate.poc_migration != 'flat': score += 5
    if candidate.delta_divergence in ('bullish', 'bearish'): score += 5
    # === PENALTY (candide con segnali deboli) ===
    if wtc == 0: score -= 15   # nessuna conferma strutturale
    if cat == 'pullback' and wms < 30: score -= 15   # pullback senza wall forte
    if candidate.market_state == 'balance' and candidate.auction_type == 'responsive':
        score -= 20   # balance + responsive = setup debole
    # Bias allineamento: se drive contro direzione probabile, penalizza
    try:
        from src.agents.institutional_bias import compute_institutional_bias
        bias = compute_institutional_bias(candidate)
        if bias.regime in ('drive_up', 'drive_down'):
            score += 5  # drive = contesto chiaro, buono per trade
    except Exception:
        pass
    return max(0, min(100, score))

def _build_market_vector(candidate: CandidateBar) -> dict:
    vp = candidate.session_ctx.vp
    levels = {
        "L1": {"name": "VAH", "price": vp.va_high if vp else 0},
        "L2": {"name": "VAL", "price": vp.va_low if vp else 0},
        "L3": {"name": "POC", "price": vp.poc if vp else 0},
        "L4": {"name": "Wall", "price": candidate.wall_level},
        "L5": {"name": "VWAP", "price": candidate.vwap},
        "L6": {"name": "ZeroGamma", "price": candidate.session_ctx.zero_gamma_level},
    }
    return levels

# ── Narrative-Decision Coherence Validator ────────────────────────────────
# Frasi che indicano aspettativa CONTRARIA alla direzione del trade.
# Se il Chief scrive "expect pullback" e poi va LONG, il testo e l'azione
# si contraddicono → veto meccanico (il caso reale del 06/02, long perso).
# Frasi CONTRARIE alla direzione: solo aspettative esplicite e non ambigue.
# (La prima versione includeva 'rejection', 'buyers trapped' ecc. → falsi
# positivi: 'sweep rejection' = rifiuto dei minimi = rialzista!)
_BEARISH_PHRASES = (
    "expect a pullback", "expect pullback", "expecting a pullback",
    "expect a rejection", "expect rejection", "expecting rejection",
    "expect a drop", "expect further downside", "expect lower",
    "likely to fail", "will likely reverse down",
)
_BULLISH_PHRASES = (
    "expect a bounce", "expect bounce", "expecting a bounce",
    "expect a rally", "expect higher", "expect further upside",
    "will likely reverse up",
)
# Clausole che annullano la contraddizione: la frase e' in un contesto
# condizionale/di invalidazione ('if', 'unless', 'invalidat', 'risk', ...)
_CONDITIONAL_MARKERS = ("if ", "if(", "unless", "invalidat", "abort", "risk",
                        "would ", "in case", "failure", "warning", "however")

def _reasoning_contradicts(direction: str, reasoning: str) -> bool:
    """True se la narrativa descrive uno scenario opposto alla direzione decisa.
    Gestisce negazioni semplici ('no rejection', 'not bearish')."""
    text = reasoning.lower()
    against = _BEARISH_PHRASES if direction == 'long' else _BULLISH_PHRASES
    for ph in against:
        idx = text.find(ph)
        while idx != -1:
            before = text[max(0, idx - 30):idx]
            after = text[idx:idx + len(ph) + 30]
            negated = any(neg in before[-12:] for neg in ('no ', 'not ', 'nessun', 'senza', "isn't", 'no-'))
            conditional = any(m in before for m in _CONDITIONAL_MARKERS) or \
                          any(m in after for m in (' would', ' then ', ' invalidat'))
            if not negated and not conditional:
                return True
            idx = text.find(ph, idx + 1)
    return False


def _et_time(candidate) -> tuple:
    """(hour, minute) ET del candidate bar. Bar.timestamp e' UTC."""
    try:
        from zoneinfo import ZoneInfo
        ts = candidate.bar.timestamp
        if ts.tzinfo is None:
            from datetime import timezone
            ts = ts.replace(tzinfo=timezone.utc)
        et = ts.astimezone(ZoneInfo('America/New_York'))
        return et.hour, et.minute
    except Exception:
        return 12, 0  # fail-open a mezzogiorno (nessun gate orario)


def _time_gate(candidate, bias) -> tuple:
    """Gate orario da desk orderflow. Ritorna (ok, veto_reason).
    - 9:30-10:00 ET: opening rotation, rumore puro → no entry.
      (prod2-yellow final: blocked 9:30-10:00 ET = first 30min only.
      10:00-10:30 was too aggressive per feedback utente dopo Jun-Jul test:
      Giugno-Luglio LONG/SHORT su 10:00-10:30 erano -$153, ma c'erano
      pochi trade e alcuni validi persi. Ridotto a 9:30-10:00.)
    - 11:45-13:15 ET: lunch chop → consentito SOLO se allineato a un drive
      (in lunch il drive continua; il chop punisce il mean-reversion).
    - dopo 15:15 ET: nessuna nuova posizione (chiusura/EOD risk).
    """
    h, m = _et_time(candidate)
    t = h * 60 + m
    if t < 10 * 60:
        return False, f"VETO: opening_rotation (entry alle {h:02d}:{m:02d} ET, prime 30min = rumore)"
    if t >= 15 * 60 + 15:
        return False, f"VETO: late_session (entry alle {h:02d}:{m:02d} ET, no nuove posizioni dopo 15:15)"
    if 11 * 60 + 45 <= t < 13 * 60 + 15 and not bias.is_drive:
        return False, (f"VETO: lunch_chop ({h:02d}:{m:02d} ET, regime {bias.regime}: "
                       "solo drive-aligned consentito in lunch)")
    return True, ""


def _participation_gate(candidate) -> tuple:
    """Segnale su volume sotto media recente = rumore, non iniziativa."""
    recent = (getattr(candidate, 'recent_bars', None) or [])[-6:-1]
    vols = [getattr(b, 'volume', 0) for b in recent if getattr(b, 'volume', 0) > 0]
    if len(vols) >= 3:
        avg = sum(vols) / len(vols)
        if candidate.bar.volume < 0.5 * avg:
            return False, (f"VETO: low_participation (vol {candidate.bar.volume} < 50% "
                           f"media recente {avg:.0f}: non e' iniziativa istituzionale)")
    return True, ""


def validate_narrative_decision(direction: str, conviction: str, reasoning: str,
                                candidate: CandidateBar, flow_report: dict) -> tuple:
    """Validatore meccanico post-LLM. Ritorna (ok, reason, conviction_capped).

    Regole (tutte derive da errori reali osservati nei log):
    1. COERENZA NARRATIVA: il reasoning non puo' descrivere lo scenario opposto
       alla direzione decisa → veto 'narrative_contradiction'.
    2. DISSENSO FLOW PESA (non si razionalizza): se l'esperto Flow dissente con
       forza med/high E il delta della barra conferma il dissenso
       → conviction cappata a 'low' (il gate confidence<70 fara' il resto).
    3. DAY-TYPE GATE anti mean-reversion: vietato operare contro una giornata
       a iniziativa accertata (i 3 short del 03/02 sotto VAL in trend day up):
       - day_type trend_up + short   → veto 'counter_trend_day'
       - day_type trend_down + long  → veto 'counter_trend_day'
       - auction initiative + poc_migration contro + setup reversal/pullback
         → veto 'counter_initiative'.
    """
    # 0) REVERSAL DISABILITATI (evidenza empirica: tutti i loss della run
    #    scalper sono reversal a conviction med; i pullback con-bias pagano 3/3)
    if candidate.setup_category == 'reversal':
        return False, "VETO: reversal_disabled (setup reversal sospesi: loss sistematici a conf med)", conviction

    # 1) coerenza testo↔direzione
    if direction in ('long', 'short') and _reasoning_contradicts(direction, reasoning):
        return False, f"VETO: narrative_contradiction (reasoning descrive scenario opposto a {direction})", conviction

    # 2) dissenso Flow
    if direction in ('long', 'short'):
        flow_bias = str(flow_report.get('bias', 'none'))
        flow_str = str(flow_report.get('strength', 'low'))
        opposed = (direction == 'long' and flow_bias == 'short') or \
                  (direction == 'short' and flow_bias == 'long')
        if opposed and flow_str in ('med', 'high'):
            delta = candidate.bar.delta
            delta_confirms = (direction == 'long' and delta < 0) or \
                             (direction == 'short' and delta > 0)
            if delta_confirms:
                conviction = 'low'   # cap: il dissenso Flow pesa, non si razionalizza

    # 3) day-type gate
    ctx = candidate.session_ctx
    dt = getattr(ctx, 'day_type', 'unknown')
    if direction == 'short' and dt == 'trend_up':
        return False, "VETO: counter_trend_day (short in trend_up day)", conviction
    if direction == 'long' and dt == 'trend_down':
        return False, "VETO: counter_trend_day (long in trend_down day)", conviction
    if candidate.auction_type == 'initiative' and candidate.setup_category in ('reversal', 'pullback'):
        if direction == 'short' and candidate.poc_migration == 'up':
            return False, "VETO: counter_initiative (short contro migrazione POC up in asta initiative)", conviction
        if direction == 'long' and candidate.poc_migration == 'down':
            return False, "VETO: counter_initiative (long contro migrazione POC down in asta initiative)", conviction

    # 4) INSTITUTIONAL BIAS GATE — deterministico, funziona anche nella PRIMA
    #    ORA dove il day-type gate e' cieco (fix dei 2 short killer del 03/02).
    bias = compute_institutional_bias(candidate)

    # 5) GATE ORARIO da desk (opening rotation / lunch chop / late session)
    ok, reason = _time_gate(candidate, bias)
    if not ok:
        return False, reason, conviction

    # 6) PARTECIPAZIONE: segnale su volume sotto media = rumore, non iniziativa
    ok, reason = _participation_gate(candidate)
    if not ok:
        return False, reason, conviction

    # 7) ESAURIMENTO: IB gia' > 80% ATR e pomeriggio → il movimento e' fatto;
    #    with-trend tardi = comprare il top. Cap conviction (non veto: il drive
    #    puo' continuare, ma non a piena convinzione).
    h_et, _ = _et_time(candidate)
    ib_rng = getattr(candidate.session_ctx, 'ib_range', 0) or 0
    atr = getattr(candidate.session_ctx, 'atr_5day', 0) or 0
    if (atr > 0 and ib_rng > 0.8 * atr and h_et >= 13
            and direction == bias.direction and conviction == 'high'):
        conviction = 'med'

    # 8) BIAS GATE vero e proprio (drive / reversal contro bias / lean cap)
    ok, reason, conviction = bias_gate(direction, candidate.setup_category,
                                       conviction, bias)
    if not ok:
        return False, f"{reason} | bias: {bias.summary()}", conviction

    # 9) R6 (NEW): BOUNCE_IN_DRIVE_NEEDS_EVIDENCE. In drive_down + long, o
    #    drive_up + short, il modello deve dimostrare accumulation/distribution
    #    SIGNATURE con dati reali: delta concordi ultimi 3 bar + big trade nella
    #    direzione giusta + close sopra/sotto VWAP. Senza questo, il bounce
    #    in un drive è un trade ad alta probabilità di perdita (03/02: LONG a
    #    10:00 in downtrend day = -50$). VETO secco.
    if direction in ('long', 'short'):
        if bias.regime == 'drive_down' and direction == 'long':
            ok_r6, ev_r6 = _has_accumulation_evidence(candidate, 'long')
            if not ok_r6:
                return False, (f"VETO: bounce_in_drive_no_evidence "
                               f"(LONG in drive_down senza accumulation: {ev_r6})"), 'low'
        if bias.regime == 'drive_up' and direction == 'short':
            ok_r6, ev_r6 = _has_accumulation_evidence(candidate, 'short')
            if not ok_r6:
                return False, (f"VETO: bounce_in_drive_no_evidence "
                               f"(SHORT in drive_up senza distribution: {ev_r6})"), 'low'

    return True, "", conviction


def _has_accumulation_evidence(candidate, direction: str) -> tuple:
    """Verifica accumulation (per long) o distribution (per short) signature
    in contesto drive. Richiesto TUTTO:
      (a) >= 3 degli ultimi 6 bar hanno delta nella direzione giusta
      (b) >= 1 Big Trade (size>=50) nella direzione giusta, sul livello rilevante
      (c) >= 1 degli ultimi 6 bar ha chiuso dalla parte giusta del VWAP
    Returns (ok: bool, evidence_str: str).
    """
    recent = (getattr(candidate, 'recent_bars', None) or [])[-6:]
    if len(recent) < 3:
        return False, "insufficient recent bars"

    if direction == 'long':
        pos_delta = sum(1 for b in recent if getattr(b, 'delta', 0) > 0)
        buy_big = 0
        for b in recent:
            for bt in (getattr(b, 'big_trades', []) or []):
                if getattr(bt, 'side', '') == 'A':  # 'A' = buy aggressor
                    buy_big += 1
        vwap_hold = sum(1 for b in recent
                        if getattr(b, 'vwap', 0) > 0 and b.close > b.vwap)
        ok = pos_delta >= 3 and buy_big >= 1 and vwap_hold >= 1
        return ok, f"pos_delta={pos_delta}/6 buy_big={buy_big} vwap_hold={vwap_hold}"
    else:  # short / distribution
        neg_delta = sum(1 for b in recent if getattr(b, 'delta', 0) < 0)
        sell_big = 0
        for b in recent:
            for bt in (getattr(b, 'big_trades', []) or []):
                if getattr(bt, 'side', '') == 'B':  # 'B' = sell aggressor
                    sell_big += 1
        vwap_reject = sum(1 for b in recent
                          if getattr(b, 'vwap', 0) > 0 and b.close < b.vwap)
        ok = neg_delta >= 3 and sell_big >= 1 and vwap_reject >= 1
        return ok, f"neg_delta={neg_delta}/6 sell_big={sell_big} vwap_reject={vwap_reject}"


def _fmt_bars_recent(candidate: CandidateBar, max_bars: int = 6) -> str:
    """Ultime N barre in formato compatto: ts O H L C V delta."""
    bars = (candidate.recent_bars or [])[-max_bars:]
    if not bars:
        return "(no recent bars)"
    lines = []
    for b in bars:
        ts = getattr(b, 'timestamp', None)
        hhmm = ts.strftime('%H:%M') if ts else '??'
        lines.append(f"{hhmm} O={b.open:.2f} H={b.high:.2f} L={b.low:.2f} C={b.close:.2f} "
                     f"V={b.volume} D={b.delta:+d}")
    return "\n".join(lines)


def _fmt_big_trades_recent(candidate: CandidateBar, direction: str = None, lookback: int = 6) -> str:
    """Big Trades dalle ultime N barre, opzionalmente filtrati per lato.
    Usa sia recent_bars che eventuali raw_bars sul candidate.
    Ritorna lista compatta: ts price size is_buy"""
    bars = (candidate.recent_bars or [])[-lookback:]
    big_trades = []
    for b in bars:
        for bt in getattr(b, 'big_trades', []) or []:
            # bt: oggetto con .price .size .is_buy (ordinefootprint)
            ts = getattr(b, 'timestamp', None)
            hhmm = ts.strftime('%H:%M') if ts else '??'
            big_trades.append(f"{hhmm} @ {bt.price:.2f} size={bt.size} {'BUY' if getattr(bt, 'is_buy', None) else 'SELL'}")
    if not big_trades:
        return "(no significant Big Trades in recent bars)"
    return "\n".join(big_trades[-15:])  # max 15 per non esplodere il prompt


def _build_snapshot(candidate: CandidateBar, market_narrative: str,
                    session_context: list = None) -> str:
    """Snapshot strutturato COMPLETO per gli esperti LLM.
    Prima ricevevano ~10 righe (livelli + price + delta + GEX): gli 'esperti'
    non avevano dati su cui essere esperti. Ora ricevono tutto il contesto
    gia' calcolato dal motore (wall, flow, asta, day-type, barre recenti,
    narrativa, memoria di sessione)."""
    levels = _build_market_vector(candidate)
    levels_str = "\n".join([f"{k}: {v['name']} @ {v['price']}" for k, v in levels.items() if v['price'] > 0])
    ctx = candidate.session_ctx
    bar = candidate.bar

    mem_lines = ""
    if session_context:
        mem_lines = "\n".join(f"- {m}" for m in session_context[-6:])
    elif getattr(ctx, 'session_memory', None):
        mem_lines = "\n".join(f"- {m.get('text', m)}" for m in ctx.session_memory[-6:])

    bias = compute_institutional_bias(candidate)
    bias_txt = bias.summary()

    return f"""## STRUCTURAL LEVELS (MARKET VECTOR)
{levels_str}
IB: high={ctx.ib_high} low={ctx.ib_low} complete={ctx.ib_complete}
Prev day: POC={getattr(ctx.prev_day_vp, 'poc', None)} VAH={getattr(ctx.prev_day_vp, 'va_high', None)} VAL={getattr(ctx.prev_day_vp, 'va_low', None)}

## CANDIDATE BAR
Price: {bar.close} | O={bar.open} H={bar.high} L={bar.low} | Vol={bar.volume} | Delta={bar.delta:+d}
Wicks: top={candidate.top_wick_ratio:.0%} bottom={candidate.bottom_wick_ratio:.0%} | close_pct={candidate.close_percentile:.0%}
Wall: {candidate.wall_side} @ {candidate.wall_level} | n_trades={candidate.wall_trade_count} max_size={candidate.wall_max_size}
Proximity: {candidate.proximity_to} @ {candidate.proximity_level} | second_test={candidate.is_second_test}

## FLOW & AUCTION
Delta divergence: {candidate.delta_divergence} | Effort-no-result: {candidate.effort_no_result}
Market state: {candidate.market_state} | Auction: {candidate.auction_type} | POC migration: {candidate.poc_migration}
Setup category: {candidate.setup_category} | Session bias: {candidate.session_bias}
Stop hunt: active={candidate.active_stop_hunt} dir={candidate.stop_hunt_direction}
VWAP: {candidate.vwap:.2f} | NAV alert (vol spike): {candidate.nav_alert}

## DAY CONTEXT
Day type: {ctx.day_type} (history: {getattr(ctx, 'day_type_history', [])[-4:]})
Profile shape: {ctx.profile_shape} | Market structure: {ctx.market_structure_state}
IB breakouts: {ctx.ib_breakouts_count} (first dir: {ctx.ib_first_breakout_dir})
GEX: {ctx.gex_regime} zero_gamma={ctx.zero_gamma_level} call_wall={ctx.call_wall} put_wall={ctx.put_wall}
ATR5: {ctx.atr_5day} | News: {candidate.upcoming_news}

## INSTITUTIONAL BIAS (deterministic — computed from data, treat as ground truth)
{bias_txt}

## RECENT BARS (M5, ultimi {6})
{_fmt_bars_recent(candidate)}

## BIG TRADES (ultimi 6 bar M5, lato corretto del trade proposto)
{_fmt_big_trades_recent(candidate, direction=None)}

## EVOLVING NARRATIVE
{market_narrative or '(none)'}

## SESSION MEMORY (ultimi eventi)
{mem_lines or '(none)'}"""

def _finalize_decision(data: dict, flow_report: dict, candidate: CandidateBar,
                       levels: dict, raw: str) -> FabioSignal:
    """Validatore meccanico + execution compiler + risk validator.
    Condiviso tra modalita' scalper (1 call) ed experts (5 call)."""
    direction = data.get('direction', 'none')
    if direction == 'none':
        return FabioSignal('none', 0, None, None, None, 'none', "Chief opted for no trade.", "", raw)

    # FLEXIBLE PARSING: modelli diversi (GLM, M2.7) usano schemi diversi.
    # Estrai conviction da vari possibili campi.
    _raw_conf = data.get('conviction', '')
    if not _raw_conf:
        # M2.7 potrebbe usare 'confidence' numerica
        _num_conf = data.get('confidence', 0)
        if isinstance(_num_conf, (int, float)):
            if _num_conf >= 80:
                _raw_conf = 'high'
            elif _num_conf >= 60:
                _raw_conf = 'med'
            else:
                _raw_conf = 'low'
        # oppure da setup_type
        if not _raw_conf:
            _setup = data.get('setup_type', data.get('setup', ''))
            if _setup in ('pullback', 'ivb_breakout', 'squeeze'):
                _raw_conf = 'med'
            elif _setup in ('imbalance_hunting', 'reversal'):
                _raw_conf = 'low'
            else:
                _raw_conf = 'med'  # default sensato

    # ── VALIDATORE MECCANICO narrativa↔decisione + bias (PRIMA del pricing)
    reasoning_txt = data.get('reasoning', '')
    ok, veto_reason, conviction = validate_narrative_decision(
        direction, _raw_conf, reasoning_txt, candidate, flow_report)
    if not ok:
        return FabioSignal('none', 0, None, None, None, 'none',
                           f"{veto_reason} | reasoning: {reasoning_txt[:120]}", "", raw)

    # FLEXIBLE ANCHOR: se LLM non ha specificato anchor_level_id, scegli il migliore.
    anchor_id = data.get('anchor_level_id')
    if anchor_id not in levels or levels[anchor_id]['price'] == 0:
        # Scegli l'anchor piu' logico basato sulla direzione
        valid_levels = [(k, v) for k, v in levels.items() if v['price'] > 0]
        if not valid_levels:
            return FabioSignal('none', 0, None, None, None, 'none', f"VETO: No valid levels available", "", raw)
        # Per long: anchor piu' vicino SOTTO il prezzo. Per short: sopra.
        price = candidate.bar.close
        if direction == 'long':
            valid_levels.sort(key=lambda x: price - x[1]['price'] if x[1]['price'] < price else 1e9)
        else:
            valid_levels.sort(key=lambda x: x[1]['price'] - price if x[1]['price'] > price else 1e9)
        anchor_id = valid_levels[0][0]

    # EXECUTION COMPILER (Code-based Pricing)
    anchor_price = levels[anchor_id]['price']
    entry_price = candidate.bar.close

    # Volatility Buffer (approximate from 5day ATR, min 8 points)
    atr = candidate.session_ctx.atr_5day
    buffer = max(8.0, atr * 0.05)

    if direction == 'long':
        stop = anchor_price - buffer
    else:
        stop = anchor_price + buffer

    risk_points_pre = abs(entry_price - stop)

    # TARGET STRUTTURALE (non un multiplo R nel vuoto): il desk esce al livello
    # opposto — POC/VAH/VAL/IB edges/VWAP/prev-day VP — il primo a distanza >= 1R
    # nella direzione del trade. Fallback 1.5R solo se non c'e' struttura utile.
    def _structural_target(direction, entry, risk):
        cands = []
        ctx = candidate.session_ctx
        for v in levels.values():
            if v['price'] > 0:
                cands.append((v['name'], v['price']))
        if ctx.ib_high > 0:
            cands += [('IB_high', ctx.ib_high), ('IB_low', ctx.ib_low)]
        pvp = getattr(ctx, 'prev_day_vp', None)
        if pvp is not None:
            for nm, pr in [('prevVAH', getattr(pvp, 'va_high', 0)), ('prevPOC', getattr(pvp, 'poc', 0)),
                           ('prevVAL', getattr(pvp, 'va_low', 0))]:
                if pr:
                    cands.append((nm, pr))
        if direction == 'long':
            valid = sorted(p for _, p in cands if p >= entry + risk)
            return valid[0] if valid else entry + risk * 1.5
        valid = sorted((p for _, p in cands if p <= entry - risk), reverse=True)
        return valid[0] if valid else entry - risk * 1.5

    target = _structural_target(direction, entry_price, risk_points_pre)

    # RISK VALIDATOR
    risk_points = abs(entry_price - stop)
    if risk_points < 2.0:  # Too tight, noise will kill it
        return FabioSignal('none', 0, None, None, None, 'none', f"VETO: Stop too tight ({risk_points:.2f} pts).", "", raw)

    # If stop is completely on the wrong side of price (e.g., long but stop is above entry)
    if (direction == 'long' and stop >= entry_price) or (direction == 'short' and stop <= entry_price):
        return FabioSignal('none', 0, None, None, None, 'none', f"VETO: Structurally invalid stop placement.", "", raw)

    conf_map = {"high": 90, "med": 75, "low": 50}
    confidence = conf_map.get(conviction, 50)   # usa conviction CAPPATA dal validatore

    return FabioSignal(
        direction=direction,
        confidence=confidence,
        entry=entry_price,
        stop=stop,
        target=target,
        setup_type=data.get('setup_type', 'none'),
        reasoning=f"Anchor: {levels[anchor_id]['name']} @ {anchor_price}. " + data.get('reasoning', ''),
        market_narrative_update=data.get('market_narrative_update', ''),
        nlm_answer=raw
    )


def _analyze_scalper(candidate: CandidateBar, session_context: list = None,
                     m1_bars: list = None, market_narrative: str = "",
                     bars_since_last: list = None) -> FabioSignal:
    """Modalita' SCALPER: 1 sola chiamata LLM (MiniMax) invece di 5.
    La bias istituzionale e' calcolata deterministicamente e data come ground
    truth; il modello ragiona da orderflow scalper: bias → location → trigger."""
    levels = _build_market_vector(candidate)
    snapshot = _build_snapshot(candidate, market_narrative, session_context)

    raw = llm_ask(_get_scalper_system_prompt(), snapshot, model=SCALPER_MODEL)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return FabioSignal('none', 0, None, None, None, 'none', f"JSON parse error: {e}", "", raw)

    # flow_report sintetico dal delta della barra (per il gate dissenso-flow):
    # in modalita' single-call il 'flow expert' e' il dato stesso.
    bar_delta = candidate.bar.delta
    flow_report = {
        'bias': 'long' if bar_delta > 0 else ('short' if bar_delta < 0 else 'none'),
        'strength': 'high' if abs(bar_delta) >= 500 else ('med' if abs(bar_delta) >= 150 else 'low'),
    }
    return _finalize_decision(data, flow_report, candidate, levels, raw)


def analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> FabioSignal:
    if FABIO_MODE == 'scalper':
        return _analyze_scalper(candidate, session_context, m1_bars, market_narrative, bars_since_last)
    levels = _build_market_vector(candidate)
    snapshot = _build_snapshot(candidate, market_narrative, session_context)
    base_user_msg = snapshot + "\n\n"

    # Expert Prompts (JSON Output Required) — ogni esperto riceve lo STESSO
    # snapshot completo (bias inclusa) + focus di ruolo
    json_req = "Respond ONLY with valid JSON: {\"bias\": \"long|short|none\", \"strength\": \"low|med|high\", \"key_level_ids\": [\"L1\", ...], \"note\": \"<max 20 words>\"}"

    amt_prompt = ("You are the AMT/Volume Profile Analyst. Judge from DAY TYPE, profile shape, "
                  "POC migration, VA position, auction type (responsive vs initiative). "
                  "Respect the INSTITUTIONAL BIAS block: NEVER suggest fading a drive regime. "
                  "In rotational regime, mean-reversion at value extremes is the business.\n" + json_req)
    flow_prompt = ("You are the Order Flow Analyst. Judge from delta, delta divergence, "
                   "effort-no-result, wall size/side, stop hunts, recent bar deltas. "
                   "If delta opposes price direction at a wall, say so explicitly. "
                   "Absorption at a wall against the bias = reversal risk, flag it.\n" + json_req)
    tech_prompt = ("You are the Technical Analyst. Judge from VWAP position, market structure, "
                   "recent bars, IB state, wicks/close percentile. "
                   "Price extended >0.5x IB range = drive: pullbacks-with-trend only.\n" + json_req)
    macro_prompt = ("You are the Macro & GEX Analyst. Judge from GEX regime, zero-gamma distance, "
                    "news risk. POSITIVE gex = mean-reversion; NEGATIVE = volatility/breakouts.\n" + json_req)

    def fetch_expert(prompt, user_msg):
        raw = llm_ask(prompt, user_msg)
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        try:
            return json.loads(raw)
        except:
            return {"bias": "none", "strength": "low", "key_level_ids": [], "error": "parse_failed"}

    # Run Experts in Parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_macro = executor.submit(fetch_expert, macro_prompt, base_user_msg)
        f_amt   = executor.submit(fetch_expert, amt_prompt, base_user_msg)
        f_flow  = executor.submit(fetch_expert, flow_prompt, base_user_msg)
        f_tech  = executor.submit(fetch_expert, tech_prompt, base_user_msg)
        
        macro_report = f_macro.result()
        amt_report   = f_amt.result()
        flow_report  = f_flow.result()
        tech_report  = f_tech.result()

    # Chief Decision
    chief_prompt = _get_system_prompt()
    chief_msg = base_user_msg + f"## EXPERT REPORTS (JSON)\nMacro: {json.dumps(macro_report)}\nAMT: {json.dumps(amt_report)}\nFlow: {json.dumps(flow_report)}\nTech: {json.dumps(tech_report)}\n"
    
    raw = llm_ask(chief_prompt, chief_msg)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return FabioSignal('none', 0, None, None, None, 'none', f"JSON parse error: {e}", "", raw)

    return _finalize_decision(data, flow_report, candidate, levels, raw)

def _get_management_system_prompt() -> str:
    """Prompt minimale per trailing LLM. Solo dati necessari:
    entry/stop/current, ultimi 10 M1 bars, swing high/low recenti.
    Decision: hold o trail (con new_stop). Mai allargare lo stop."""
    return """You manage an OPEN NQ position. Decide: hold or trail.

RULES:
- 'trail' ONLY if there's a new confirmed swing (higher low for long, lower high
  for short). Move stop just BEYOND the new swing (below swing low for long,
  above swing high for short). NEVER widen, NEVER move stop backwards.
- 'hold' if no new swing or structure intact.
- new_stop must be STRICTLY better than current stop (higher for long,
  lower for short). If no improvement possible, return hold.

Respond JSON only:
{"decision": "hold"|"trail", "new_stop": float|null, "reason": "<10 words>"}"""

def _fmt_m1_window(m1_bars: list, max_bars: int = 10) -> str:
    """Last N M1 bars, COMPACT: only H L C D (no O, no V). Default 10 (was 40)."""
    bars = (m1_bars or [])[-max_bars:]
    if not bars:
        return "(no M1 context)"
    lines = []
    for b in bars:
        ts = getattr(b, 'timestamp', None)
        hhmm = ts.strftime('%H:%M') if ts else '??'
        lines.append(f"{hhmm} H={b.high:.2f} L={b.low:.2f} C={b.close:.2f} D={b.delta:+d}")
    return "\n".join(lines)

def manage_active_trade(trade, candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> dict:
    """MINIMAL trailing LLM. Window ridotta a 10 M1 bars, niente narrative,
    prompt minimal. Decision semplice: hold o trail (no early_exit/reverse).

    prod2-yellow: trigger rr=0.8 (was 0.3). Lets winners run more.
    Lock-in: 50% at rr=1.5 (NEW safety net), 75% at rr=2.5.
    Cap new_stop at target-4pt (long) / target+4pt (short) so trailing
    can never move stop beyond the original target.
    """
    import os
    risk = abs(trade.entry - trade.stop)
    cur = candidate.bar.close
    pnl = (cur - trade.entry) if trade.direction == 'long' else (trade.entry - cur)
    rr = pnl / risk if risk > 0 else 0
    trail_trigger_rr = float(os.environ.get('TRAIL_TRIGGER_RR', '0.8'))
    if rr <= trail_trigger_rr:
        # In loss o micro-profit, niente trailing: hold silente
        return {"decision": "hold", "new_stop": None, "new_target": None, "reasoning": f"rr={rr:+.2f}, no trail zone (trigger={trail_trigger_rr})"}
    # SAFETY NET: lock-in at higher RR (50% at 1.5R, 75% at 2.5R)
    # Applied as a MIN on the LLM's new_stop, not a max — LLM can be more aggressive
    lock_50_rr = float(os.environ.get('TRAIL_LOCK_50_RR', '1.5'))
    lock_75_rr = float(os.environ.get('TRAIL_LOCK_75_RR', '2.5'))
    if rr >= lock_50_rr:
        if trade.direction == 'long':
            min_lock = trade.entry + risk * 0.5  # lock 50%
        else:
            min_lock = trade.entry - risk * 0.5
    else:
        min_lock = trade.stop
    if rr >= lock_75_rr:
        if trade.direction == 'long':
            min_lock = trade.entry + risk * 0.75  # lock 75%
        else:
            min_lock = trade.entry - risk * 0.75
    # Solo ultime 10 M1 (ridotto da 40)
    target = getattr(trade, 'target', None)
    m1_compact = _fmt_m1_window(m1_bars, max_bars=10)
    msg = (f"dir={trade.direction} entry={trade.entry} stop={trade.stop} "
           f"target={target} price={cur} rr={rr:+.2f}\n"
           f"MIN_LOCK (don't move below): {min_lock:.2f}\n\n"
           f"LAST 10 M1 (H L C D):\n{m1_compact}\n\n"
           f"Move stop? trail/hold. If trail: new_stop >= {min_lock:.2f} "
           f"and {'< target-4' if target and trade.direction=='long' else '> target+4' if target and trade.direction=='short' else '<= entry+20'}")
    raw = llm_ask(_get_management_system_prompt(), msg, model=SCALPER_MODEL)
    if raw.startswith('```'): raw = raw.split('```')[1].lstrip('json').strip()
    try:
        data = json.loads(raw)
        decision = data.get("decision", "hold")
        new_stop = data.get("new_stop")
        if decision == 'trail' and new_stop is not None:
            # Safety 1: mai allargare lo stop
            if trade.direction == 'long' and new_stop <= trade.stop:
                new_stop = None; decision = 'hold'
            elif trade.direction == 'short' and new_stop >= trade.stop:
                new_stop = None; decision = 'hold'
            # Safety 2: enforce min_lock floor
            elif trade.direction == 'long' and new_stop < min_lock:
                new_stop = min_lock
            elif trade.direction == 'short' and new_stop > min_lock:
                new_stop = min_lock
            # Safety 3: cap at target-4pt so trailing can never overshoot target
            if target is not None:
                if trade.direction == 'long' and new_stop is not None and new_stop > target - 4:
                    new_stop = target - 4
                elif trade.direction == 'short' and new_stop is not None and new_stop < target + 4:
                    new_stop = target + 4
        return {"decision": decision, "new_stop": new_stop, "new_target": None,
                "reasoning": data.get("reason", "")}
    except Exception:
        return {"decision": "hold", "new_stop": None, "new_target": None, "reasoning": "parse error"}
