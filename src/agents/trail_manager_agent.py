"""
TRAIL MANAGER — LLM trailing stop per R:R ≥ 1.0
Prompt ultra-corto, decisioni veloci. Zero contesto inutile.
"""

import json, os
from src.agents.llm_client import llm_ask

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'agent_memory', 'trail_manager_log.jsonl')

SYSTEM = """You are the TRAIL MANAGER. A trade is in profit (≥1.0R). Protect profits, maximize runners.

Decide: hold, trail (new_stop), or early_exit.
Rules:
- LONG: new_stop must be > old_stop. Trail behind nearest wall below price.
- SHORT: new_stop must be < old_stop. Trail behind nearest wall above price.
- R:R≥2.0 → MUST trail aggressively behind nearest structural wall.
- early_exit only if clear reversal signals (delta divergence, volume collapse, key level break).

Respond ONLY valid JSON: {"decision":"hold|trail|early_exit", "new_stop": float|null, "reasoning":"short_reason"}"""


def evaluate(trade, bar, m1_bars, ctx) -> dict:
    risk = abs(trade.entry - trade.stop)
    rr = ((bar.close - trade.entry) if trade.direction == 'long' else (trade.entry - bar.close)) / risk if risk > 0 else 0.0

    # Trova il muro più vicino
    walls_bid, walls_ask = [], []
    for b in m1_bars[-15:]:
        for bt in getattr(b, 'big_trades', []):
            if bt.get('size', 0) >= 80:
                (walls_bid if bt.get('side') == 'bid' else walls_ask).append(bt.get('price', 0))

    near_bid = min([abs(bar.close - p) for p in walls_bid]) if walls_bid else None
    near_ask = min([abs(bar.close - p) for p in walls_ask]) if walls_ask else None

    context = (
        f"{trade.direction.upper()} entry={trade.entry} stop={trade.stop} "
        f"price={bar.close} rr={rr:.1f} bars={len(m1_bars)}\n"
        f"day={getattr(ctx,'day_type','?')} ib={getattr(ctx,'ib_high',0):.0f}/{getattr(ctx,'ib_low',0):.0f}\n"
        f"last_bar: O={bar.open} H={bar.high} L={bar.low} C={bar.close} V={bar.volume} D={bar.delta}\n"
        f"walls: bid_near={near_bid} ask_near={near_ask}"
    )

    raw = llm_ask(SYSTEM, context, use_cache=False)
    if '```' in raw:
        raw = raw.split('```')[1].strip().lstrip('json')

    try:
        return json.loads(raw)
    except Exception:
        return {"decision": "hold", "new_stop": None, "reasoning": "parse_fail"}


def log(dec: dict, trade, bar, ts):
    risk = abs(trade.entry - trade.stop)
    rr = ((bar.close - trade.entry) if trade.direction == 'long' else (trade.entry - bar.close)) / risk if risk > 0 else 0.0
    entry = {
        'ts': ts.isoformat(), 'event': f'TRAIL_{dec.get("decision","hold").upper()}',
        'dir': trade.direction, 'entry': trade.entry, 'price': bar.close,
        'old_stop': trade.stop, 'new_stop': dec.get('new_stop'), 'rr': round(rr, 2),
        'decision': dec.get('decision'), 'reasoning': dec.get('reasoning', '')
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    print(f"  [TRAIL MANAGER] {dec.get('decision','hold').upper()} | {dec.get('reasoning','')[:100]}")