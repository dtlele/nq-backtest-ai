"""V2.0 — Prompt Fabio.

REGOLE:
1. System prompt = SOLO estratti dei file VERIFIED (lista esplicita sotto).
   Niente master manual, niente statistiche in-sample, niente GEX, niente
   temporal audit, niente formule ATR. (Bug 1.6 eliminato alla radice.)
2. Single-task: il modello VOTA. Non produce entry/stop/target (quelli sono
   meccanici, dai detector). Output: vote, confidence, key_evidence, veto_reason.
3. Contesto = solo stato causale fino alla barra di segnale.
"""
from __future__ import annotations
from pathlib import Path

from .models import SignalEvent, Side
from .state import SessionState
from .config import Config

# Tier VERIFIED: solo trascrizioni. I file con [Inquiry 2026]/[Methodology Refinement 2026]
# o riferimenti a log specifici sono esclusi dal core e trattati come ipotesi.
VERIFIED_RULE_FILES = {
    "core": [
        "rule_fabio_trend_vs_mean_reversion_model.md",
        "rule_fabio_second_drive.md",
        "rule_fabio_acceptance_definition_exact.md",
        "rule_fabio_stop_placement.md",
        "rule_fabio_big_trades_filter.md",
        "rule_fabio_participation_baseline.md",
        "rule_fabio_avoid_times.md",
    ],
    "failed_auction": [
        "rule_fabio_failed_auction_is_the_setup.md",
        "rule_fabio_squeeze_vs_failed_auction.md",
        "rule_fabio_trapped_buyers.md",
        "rule_fabio_trapped_sellers.md",
        "rule_fabio_effort_vs_result.md",
        "rule_fabio_punches_to_wall.md",
        "rule_fabio_balance_day_exceptions.md",
        "rule_fabio_target_selection_hierarchy.md",
    ],
    "ib_second_drive": [
        "rule_fabio_ib_breakout_rules.md",
        "rule_fabio_ib_bias.md",
        "rule_fabio_second_drive.md",
        "rule_fabio_ib_extension_targets.md",
        "rule_fabio_ivb_protection_level.md",
        "rule_fabio_cvd_as_leading_indicator.md",
    ],
    "squeeze_wall": [
        "rule_fabio_squeeze_definition.md",
        "rule_fabio_squeeze_entry_trigger.md",
        "rule_fabio_pre_explosion_pattern.md",
        "rule_fabio_trapped_buyers.md",
        "rule_fabio_trapped_sellers.md",
        "rule_fabio_punches_to_wall.md",
        "rule_fabio_coherence_of_information.md",
    ],
    "sweep_reclaim": [
        "rule_fabio_entry_mechanics.md",
        "rule_fabio_failed_auction_is_the_setup.md",
        "rule_fabio_pre_market_levels_usage.md",
    ],
}

MAX_RULE_CHARS = 6_000


def _v2_bias_line(state) -> str:
    """Bias istituzionale compatta per il V2 (SessionState, non CandidateBar).
    Stessa logica dell'engine: IB extension drive > CVD > posizione vs VWAP."""
    score, drivers = 0.0, []
    if state.ib_high > 0 and state.ib_range > 0 and state.last_bar is not None:
        close = state.last_bar.close
        ext_up, ext_dn = close - state.ib_high, state.ib_low - close
        if ext_up > 0.5 * state.ib_range:
            score += 30; drivers.append(f"DRIVE: {ext_up:.0f}pt sopra IB_high (>0.5x range)")
        elif ext_up > 0:
            score += 12; drivers.append(f"{ext_up:.0f}pt sopra IB_high")
        elif ext_dn > 0.5 * state.ib_range:
            score -= 30; drivers.append(f"DRIVE: {ext_dn:.0f}pt sotto IB_low (>0.5x range)")
        elif ext_dn > 0:
            score -= 12; drivers.append(f"{ext_dn:.0f}pt sotto IB_low")
        if state.ib_breakouts:
            first = state.ib_breakouts[0][1]
            if first == 'long':
                score += 10; drivers.append(f"primo IB breakout long ({len(state.ib_breakouts)} totali)")
            elif first == 'short':
                score -= 10; drivers.append(f"primo IB breakout short ({len(state.ib_breakouts)} totali)")
    cvd = state.cvd_slope()
    if abs(cvd) >= 150:
        score += max(-12, min(12, cvd / 50)); drivers.append(f"CVD slope {cvd:+.0f}")
    if state.vwap > 0 and state.last_bar is not None:
        if state.last_bar.close > state.vwap:
            score += 8; drivers.append("sopra VWAP")
        else:
            score -= 8; drivers.append("sotto VWAP")
    gap = state.gap_points()
    if gap is not None and abs(gap) >= 30:
        score += 8 if gap > 0 else -8; drivers.append(f"gap {gap:+.0f}pt")
    if score >= 35: regime = 'drive_up'
    elif score >= 15: regime = 'lean_up'
    elif score <= -35: regime = 'drive_down'
    elif score <= -15: regime = 'lean_down'
    else: regime = 'rotational'
    return f"score={score:+.0f} regime={regime} | " + ("; ".join(drivers) or "no drivers")

SYSTEM_TEMPLATE = """You are the trading-mind of Fabio Valentini, NQ futures scalper.
The ONLY methodology you may use is the following, extracted verbatim from your
verified transcripts. Do not invent additional rules. Do not use indicators that
are not mentioned here.

=== VERIFIED METHODOLOGY ===
{rules}
=== END ===

TASK — SINGLE DECISION:
A deterministic detector has already identified a candidate setup and computed
entry/stop/target mechanically. You must ONLY vote whether you would take this
trade, based on the methodology above and the market context below.

- Vote "long"/"short" ONLY if the setup matches the methodology with full confluence
  (location + institutional presence + absorption/initiative signature).
- INSTITUTIONAL BIAS (computed block below): in a DRIVE regime (price beyond
  0.5x IB range, CVD confirming) NEVER vote against the drive — a reversal against
  initiative flow is the classic losing trade. In a ROTATIONAL regime, mean-reversion
  at value extremes is the correct business.
- REVERSAL DISCIPLINE: a reversal is valid only if the bias regime is rotational/aligned,
  or there is explicit bias-shift evidence (failed auction + POC/CVD flip).
  "Price went too far" is NOT a reason.
- Vote "no_trade" if ANY required element is missing. Predatory patience: the first
  drive is never taken, the middle of the range is never traded, low participation
  is noise.
- Confidence: 0-100. A+ (all confluences) = 80+. B (one element weak) = 55-70.
  C (counter-trend/off-hours) = 40-55. Below 40 = why are we talking.

Respond ONLY with valid JSON:
{{
  "vote": "long" | "short" | "no_trade",
  "confidence": <int 0-100>,
  "key_evidence": "<max 30 words: the single most decisive fact>",
  "veto_reason": "<max 20 words, or empty if vote is not no_trade>"
}}"""


class FabioPromptBuilder:
    def __init__(self, cfg: Config, knowledge_dir: str = "knowledge/trader_lessons_graph"):
        self.cfg = cfg
        self.kdir = Path(knowledge_dir)
        self._cache: dict = {}

    def _load_rule(self, fname: str) -> str:
        if fname not in self._cache:
            p = self.kdir / fname
            self._cache[fname] = p.read_text(encoding="utf-8") if p.exists() else ""
        return self._cache[fname]

    def _rules_for(self, setup: str) -> str:
        files = list(dict.fromkeys(
            VERIFIED_RULE_FILES["core"] + VERIFIED_RULE_FILES.get(setup, [])))
        out, total = [], 0
        for f in files:
            txt = self._load_rule(f)
            if not txt:
                continue
            # strip markdown header noise, keep substance
            body = "\n".join(l for l in txt.splitlines()
                             if not l.startswith("# ") and not l.startswith("**Trader**")
                             and not l.startswith("**Knowledge Node**"))
            if total + len(body) > MAX_RULE_CHARS:
                break
            out.append(body.strip())
            total += len(body)
        return "\n\n---\n\n".join(out)

    def build(self, sig: SignalEvent, state: SessionState) -> tuple:
        """Ritorna (system_prompt, user_msg)."""
        system = SYSTEM_TEMPLATE.format(rules=self._rules_for(sig.setup))

        bar = state.last_bar
        lines = [
            f"DATE: {state.day.date} | TIME: {state.et_time(sig.ts_signal).strftime('%H:%M')} ET",
            f"SETUP DETECTED: {sig.setup} | DIRECTION PROPOSED: {sig.direction.value}",
            f"LEVEL TESTED: {sig.level_name} @ {sig.wall_price:.2f} | WALL SIZE: {sig.wall_size} contracts"
            + (" (A+ benchmark >=300)" if sig.wall_size >= 300 else ""),
            "",
            "MARKET STATE (causal, up to signal bar):",
            f"- IB (30min): {'complete' if state.ib_complete else 'forming'} "
            f"{state.ib_low:.2f}-{state.ib_high:.2f} (range {state.ib_range:.1f})"
            if state.ib_high > 0 else "- IB: forming",
            f"- IB breakouts so far: {len(state.ib_breakouts)}"
            + (f" (first: {state.ib_breakouts[0][1]})" if state.ib_breakouts else ""),
            f"- Developing RTH POC: {state.rth.poc:.2f} | VA: {state.rth.va_low:.2f}-{state.rth.va_high:.2f}"
            if state.rth.poc else "- RTH profile: forming",
            f"- VWAP: {state.vwap:.2f} | Price: {bar.close:.2f}",
            f"- CVD slope (15 bars): {state.cvd_slope():+.0f}",
            f"- Gap vs prev close: {state.gap_points():+.1f} pts" if state.gap_points() is not None else "",
            "",
            "INSTITUTIONAL BIAS (deterministic):",
            f"- {_v2_bias_line(state)}",
            "",
            "SIGNAL DETAILS (computed):",
            *[f"- {r}" for r in sig.reasons],
            f"- Stop (mechanical, behind wall): {sig.stop:.2f} ({sig.risk_points:.1f} pts)",
            f"- Target1 (structural): {sig.target1:.2f} (R:R {sig.rr1:.2f})",
            "",
            "LAST 8 M1 BARS (oldest→newest):",
        ]
        for b in list(state.bars)[-8:]:
            big = ""
            if b.big_trades:
                buy = sum(t.size for t in b.big_trades if t.side == "A")
                sell = sum(t.size for t in b.big_trades if t.side == "B")
                big = f" | BIG buy={buy} sell={sell}"
            lines.append(
                f"  {state.et_time(b.ts).strftime('%H:%M')} O={b.open:.2f} H={b.high:.2f} "
                f"L={b.low:.2f} C={b.close:.2f} V={b.volume} delta={b.delta:+d}{big}")

        walls = state.active_walls()[:6]
        if walls:
            lines.append("")
            lines.append("ACTIVE WALLS (formed so far today):")
            for w in walls:
                lines.append(f"- {w.side} wall @ {w.price:.2f} size={w.size} punches={w.n_punches} [{w.status}]")

        return system, "\n".join(lines)
