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
# o 'experts' (legacy: 4 esperti + Chief). Modello: OPENROUTER_MODEL,
# default MiniMax M2 (forte e molto economico per i backtest).
FABIO_MODE = os.environ.get('FABIO_MODE', 'scalper').lower()
SCALPER_MODEL = os.environ.get('OPENROUTER_MODEL', 'minimax/minimax-m2')

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
    """Single-call orderflow scalper (MiniMax). Ragiona come un vero scalper
    istituzionale: prima la BIAS, poi la location, poi il trigger di flusso.
    Source-of-truth unica per la dottrina Fabio (vedi anche _get_management_system_prompt)."""
    return """You are an elite NQ orderflow scalper trading WITH institutional flow.
You think like a Market Profile / AMT / footprint professional, in this exact order:

PRIORITY (rigida, non negoziabile):
  1. INSTITUTIONAL BIAS — ground truth (deterministic block in the snapshot).
  2. LOCATION — trade only at structural levels.
  3. FLOW TRIGGER — confirm with delta/absorption/initiative signature.
  4. PREDATORY PATIENCE — 'no_trade' is the DEFAULT answer.

1. INSTITUTIONAL BIAS. Treat the deterministic BIAS block as ground truth:
   - drive_up/drive_down: ONLY trade WITH the drive. A reversal against a drive
     is the classic losing trade. REVERSAL IS GLOBALLY DISABLED by the validator.
   - lean_up/lean_down: trade with the bias; counter-bias only at extreme location
     WITH absorption evidence, conviction max 'med'.
   - rotational: mean-revert at value extremes (VAH/VAL, IB edges); breakouts suspect.

2. LOCATION. A trade is valid only at a structural level (VAH/VAL/POC, IB edges,
   defended wall, VWAP). Middle of the range = never traded. If no structural
   anchor in the snapshot's 'BIG TRADES' or 'Wall' sections, your vote is 'none'.

3. FLOW TRIGGER. Confirm with: delta divergence at the level, effort-no-result,
   absorption at the wall, trapped traders, completed stop hunt in your direction.
   If delta opposes your direction at the wall, say so explicitly — never
   rationalize it away.

4. PREDATORY PATIENCE. First drive is never chased. Low participation = noise.
   'no_trade' is the default. You are paid to WAIT for A+ setups, not to trade.

HARD RULES (mechanical validator enforces them AFTER you — violating = veto):
R1. COHERENCE: 'reasoning' must NEVER describe an expectation opposite to 'direction'.
R2. FLOW DISSENT: if delta/flow opposes your direction, conviction='low' max.
R3. BIAS: no short in drive_up, no long in drive_down. Counter-bias pullback
    against |score|>=25 requires conviction='high' AND explicit bias-shift evidence.
R4. CONVICTION: 'high' only with full confluence (bias + location + flow trigger).
R5. REVERSAL: setup_type='reversal' is GLOBALLY DISABLED. Vote 'none' on reversal setups.

ANTI-PATTERNS (do NOT do these — they look like good setups but lose):
  - "Price went too far, mean-reverting" (without bias shift = fade the drive)
  - "Wall is empty but price should hold" (no wall = no defense = scratch)
  - "Delta positive but bar is bearish = absorption long" (often = buyer exhaustion)
  - "It's only a small position, doesn't matter" (every loss compounds)
  - "I'm not sure, but let's try" (no_trade beats a -1R)

JSON schema (strict):
{
  "reasoning": "<MAX 100 WORDS. Start with bias, then location, then flow. Cite real numbers from snapshot.>",
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
    from src.agents.llm_client import _get_provider
    if _get_provider() == "human": return 100
    score = 0
    wms = candidate.wall_max_size
    if wms >= 50: score += 30
    elif wms >= 30: score += 20
    cat = candidate.setup_category
    if cat == 'imbalance_hunting': score += 20
    elif cat == 'momentum': score += 20
    elif cat == 'reversal': score += 15
    if candidate.market_state == 'imbalance': score += 10
    if candidate.auction_type == 'initiative': score += 10
    if candidate.is_second_test: score += 10
    if candidate.poc_migration != 'flat': score += 10
    if cat == 'pullback' and wms < 20: score -= 20
    if candidate.market_state == 'balance' and candidate.auction_type == 'responsive': score -= 20
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
    - 9:30-9:45 ET: opening rotation, rumore puro → no entry.
    - 11:45-13:15 ET: lunch chop → consentito SOLO se allineato a un drive
      (in lunch il drive continua; il chop punisce il mean-reversion).
    - dopo 15:15 ET: nessuna nuova posizione (chiusura/EOD risk).
    """
    h, m = _et_time(candidate)
    t = h * 60 + m
    if t < 9 * 60 + 45:
        return False, f"VETO: opening_rotation (entry alle {h:02d}:{m:02d} ET, prime 15min = rumore)"
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

    return True, "", conviction


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

    # ── VALIDATORE MECCANICO narrativa↔decisione + bias (PRIMA del pricing)
    reasoning_txt = data.get('reasoning', '')
    ok, veto_reason, conviction = validate_narrative_decision(
        direction, data.get('conviction', 'low'), reasoning_txt, candidate, flow_report)
    if not ok:
        return FabioSignal('none', 0, None, None, None, 'none',
                           f"{veto_reason} | reasoning: {reasoning_txt[:120]}", "", raw)

    anchor_id = data.get('anchor_level_id')
    if anchor_id not in levels or levels[anchor_id]['price'] == 0:
        return FabioSignal('none', 0, None, None, None, 'none', f"VETO: Invalid anchor {anchor_id}", "", raw)

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
    """Prompt per la gestione attiva del trade (APM). Il numero di barre M1
    nel contesto verra' inserito come 'You see N bars: ...' nel message, non
    qui, perche' e' dinamico."""
    return """You are the trade-management desk for an NQ orderflow scalper.
You manage an OPEN position. The snapshot below shows the last N M1 bars (N is
in the message header) plus the current M5 candidate bar, recent swing highs/lows,
delta evolution, active walls, and VWAP position.

CURRENT STATE in the message:
  - current_rr: how many R the trade is currently in profit/negative
  - bars_held: how many M1 bars since entry
  - mfe: maximum favorable excursion (peak profit in R)
  - swing_last_long / swing_last_short: last confirmed swing high/low
  - current_price: latest price

MANAGEMENT DOCTRINE (a real desk lets winners breathe):
- 'hold' while structure INTACT: higher lows (long) / lower highs (short), delta
  not flipping against you, price on the right side of VWAP.
- 'trail' ONLY when a NEW confirmed swing forms: new_stop just beyond that swing
  (below swing low for long, above swing high for short). NEVER widen, NEVER
  move stop backwards.
- 'early_exit' ONLY on clear invalidation: delta flip + break of last swing,
  OR failed auction back through entry. A pullback to a higher low is NOT
  invalidation — do not scratch winners.

If new_stop would be the same as old stop (no new swing formed), use 'hold' with
new_stop=null. The trade_simulator will run its Donchian 40-bar trail mechanically
on each bar regardless of your decision — your job is to provide INTEL,
not mechanical trailing.

Respond in JSON:
{
  "decision": "hold|trail|early_exit",
  "new_stop": float|null,
  "reason": "<max 20 words: the decisive fact>"
}"""

def _fmt_m1_window(m1_bars: list, max_bars: int = 40) -> str:
    bars = (m1_bars or [])[-max_bars:]
    if not bars:
        return "(no M1 context)"
    lines = []
    for b in bars:
        ts = getattr(b, 'timestamp', None)
        hhmm = ts.strftime('%H:%M') if ts else '??'
        lines.append(f"{hhmm} O={b.open:.2f} H={b.high:.2f} L={b.low:.2f} C={b.close:.2f} V={b.volume} D={b.delta:+d}")
    return "\n".join(lines)

def manage_active_trade(trade, candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> dict:
    risk = abs(trade.entry - trade.stop)
    cur = candidate.bar.close
    pnl = (cur - trade.entry) if trade.direction == 'long' else (trade.entry - cur)
    rr = pnl / risk if risk > 0 else 0
    bars_held = len(m1_bars or [])
    mfe = getattr(trade, 'max_profit_pts', 0.0) / risk if risk > 0 else 0
    trade_context = (f"OPEN TRADE: dir={trade.direction} entry={trade.entry} stop={trade.stop} "
                     f"target={getattr(trade, 'target', None)} price={cur} | open PnL={pnl:+.1f}pt ({rr:+.2f}R)\n"
                     f"current_rr={rr:+.2f}R | bars_held={bars_held} | mfe={mfe:+.2f}R")
    msg = (f"You see {bars_held} M1 bars below.\n\n{trade_context}\n\n"
           f"## {bars_held}-BAR M1 WINDOW (oldest->newest)\n{_fmt_m1_window(m1_bars, max_bars=bars_held)}"
           f"\n\n## NARRATIVE\n{market_narrative or '(none)'}\n\nDecide: hold / trail / early_exit.")
    raw = llm_ask(_get_management_system_prompt(), msg, model=SCALPER_MODEL)
    if raw.startswith('```'): raw = raw.split('```')[1].lstrip('json').strip()
    try:
        data = json.loads(raw)
        decision = data.get("decision", "hold")
        new_stop = data.get("new_stop")
        # Safety: mai allargare lo stop
        if decision == 'trail' and new_stop is not None:
            if trade.direction == 'long' and new_stop <= trade.stop:
                new_stop = None; decision = 'hold'
            elif trade.direction == 'short' and new_stop >= trade.stop:
                new_stop = None; decision = 'hold'
        return {"decision": decision, "new_stop": new_stop, "new_target": None,
                "reasoning": data.get("reason", "")}
    except Exception:
        return {"decision": "hold", "new_stop": None, "new_target": None, "reasoning": "parse error"}
