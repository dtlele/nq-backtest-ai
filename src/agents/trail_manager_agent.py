"""
⚠️ DEPRECATED — NON USARE ⚠️

TRAIL MANAGER — LLM trailing stop per R:R >= 1.0
Sostituito da: src/trade_simulator.py: _donchian_trail_stop (40-bar Donchian +
swing trail, O(1) per barra, zero LLM, piu' veloce e piu' preciso).

Motivi della rimozione:
  1. "R:R>=2.0 -> MUST trail aggressively" causava il pattern "stop a BE a 1R
     poi scratch immediato" che e' stato il killer dei nostri winner.
  2. "trail behind nearest wall" non distingueva wall robusti (>=150 contratti)
     da singole print retail.
  3. Latenza ~50s per decisione di trailing su un'operazione che avviene su
     ogni barra M1: ingestibile.

Se devi attivare un trail manager basato su LLM, fallo in trade_simulator
con il pattern attuale (Donchian + swing confermato).
"""

# Mantenuto solo per retrocompatibilita' con vecchi import. Non esegue alcuna
# logica: ogni chiamata a evaluate() ritorna 'hold' + warning di deprecazione.

import os
import json as _json

LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'agent_memory', 'trail_manager_log.jsonl'
)

SYSTEM = "[DEPRECATED] Use src/trade_simulator._donchian_trail_stop instead."

_DEPRECATION_WARNING_EMITTED = False


def evaluate(trade, bar, m1_bars, ctx) -> dict:
    """DEPRECATED. Restituisce sempre hold + warning. Usare _donchian_trail_stop()."""
    global _DEPRECATION_WARNING_EMITTED
    if not _DEPRECATION_WARNING_EMITTED:
        print("[DEPRECATION] trail_manager_agent.evaluate() is DEPRECATED. "
              "Use src/trade_simulator._donchian_trail_stop instead.")
        _DEPRECATION_WARNING_EMITTED = True
    return {"decision": "hold", "new_stop": None, "reasoning": "deprecated_module"}


def log(dec, trade, bar, ts):
    """DEPRECATED. Non scrive log utili."""
    return  # no-op
