import json, os
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from src import CandidateBar, FabioSignal, FABIO_NOTEBOOK_ID
from src.agents.nlm_client import nlm_ask
from src.signal_context import build_fabio_question

load_dotenv()

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_knowledge.json'

# Topics from simplified_strategy most relevant per candidate type
RELEVANT_TOPICS = [
    'simplified_model_overview',
    'simplified_wall_definition',
    'simplified_second_drive_exact',
    'simplified_entry_trigger',
    'simplified_stop_exact',
    'simplified_target_exact',
    'simplified_ivb_formation',
    'simplified_no_trade_top3',
    'myisto_pattern',
]

def _load_knowledge() -> str:
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    simplified = data.get('simplified_strategy', {})
    parts = []
    for topic in RELEVANT_TOPICS:
        if topic in simplified:
            parts.append(f"### {topic}\n{simplified[topic]}\n")
    return '\n'.join(parts)

SYSTEM_PROMPT = """You are Fabio Valentini's trading methodology agent analyzing NQ futures.
You follow the simplified Chart Fanatics approach: Big Trades (>=30 contracts) clustering at LVN/POC + IVB breakout direction + second drive = high probability squeeze.
NO CVD analysis. NO multi-timeframe. Keep it simple and mechanical.

Respond ONLY with valid JSON matching this schema:
{
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "ivb_breakout" | "none",
  "reasoning": "<2-3 sentence explanation>"
}
"""

def analyze(candidate: CandidateBar) -> FabioSignal:
    knowledge = _load_knowledge()
    nlm_question = build_fabio_question(candidate)
    nlm_answer = nlm_ask(nlm_question, FABIO_NOTEBOOK_ID)

    user_msg = f"""## Fabio's Knowledge (Simplified Strategy)
{knowledge}

## NotebookLM Context
{nlm_answer}

## Current Bar Data
{build_fabio_question(candidate)}

Analyze this setup and respond with JSON only."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_msg}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()

    data = json.loads(raw)
    return FabioSignal(
        direction   = data.get('direction', 'none'),
        confidence  = int(data.get('confidence', 0)),
        entry       = data.get('entry'),
        stop        = data.get('stop'),
        target      = data.get('target'),
        setup_type  = data.get('setup_type', 'none'),
        reasoning   = data.get('reasoning', ''),
        nlm_answer  = nlm_answer,
    )
