import json, os
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from src import CandidateBar, FabioSignal, AndreaSignal, ANDREA_NOTEBOOK_ID
from src.agents.nlm_client import nlm_ask
from src.signal_context import build_andrea_question

load_dotenv()

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'andrea_knowledge.json'
RELEVANT_TOPICS = [
    'ibob_overview', 'ibob_candle_close',
    'ibob_bubble_body_vs_wick', 'ibob_diagonal_imbalances',
    'ibob_stop_target', 'ibob_invalidation',
    'simplified_entry_mechanical',
]

def _load_knowledge() -> str:
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    # Topics may be in either section — combine both
    combined = {}
    combined.update(data.get('topics', {}))
    combined.update(data.get('simplified_strategy', {}))
    return '\n'.join(
        f"### {t}\n{combined[t]}\n"
        for t in RELEVANT_TOPICS if t in combined
    )

SYSTEM_PROMPT = """You are Andrea Cimi's methodology agent providing confirmation analysis for NQ futures.
You check IBOB (Initial Balance Outside Bar) conditions: candle close outside IB, big bubble in candle body (not wick), 2-3 diagonal imbalances in footprint.
You confirm or veto Fabio Valentini's primary signal.

Respond ONLY with valid JSON:
{
  "confirmation": true | false,
  "confidence": <int 0-100>,
  "setup_type": "ibob" | "failed_auction" | "none",
  "reasoning": "<2 sentence explanation>"
}
"""

def confirm(candidate: CandidateBar, fabio_signal: FabioSignal) -> AndreaSignal:
    knowledge = _load_knowledge()
    nlm_question = build_andrea_question(candidate, fabio_signal)
    nlm_answer = nlm_ask(nlm_question, ANDREA_NOTEBOOK_ID)

    user_msg = f"""## Andrea's Knowledge (IBOB Simplified)
{knowledge}

## NotebookLM Context
{nlm_answer}

## Bar Context + Fabio's Signal
{nlm_question}

Does this bar confirm Fabio's signal? Respond with JSON only."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_msg}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AndreaSignal(
            confirmation=False, confidence=0,
            setup_type='none',
            reasoning=f'JSON parse error: {raw[:100]}',
            nlm_answer=nlm_answer,
        )
    return AndreaSignal(
        confirmation = bool(data.get('confirmation', False)),
        confidence   = int(data.get('confidence', 0)),
        setup_type   = data.get('setup_type', 'none'),
        reasoning    = data.get('reasoning', ''),
        nlm_answer   = nlm_answer,
    )
