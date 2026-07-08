import json
import logging
from src.agents.llm_client import llm_ask
from src.bt_narrative_engine import BigTradeNode

logger = logging.getLogger(__name__)

BT_NARRATIVE_PROMPT = """You are a highly specialized Order Flow analyst.
Your only job is to analyze the market by jumping from one Institutional Big Trade Node to the next.
You do not care about what happens on a minute-by-minute basis, unless it helps you understand the context between two nodes.

Your task is to:
1. Identify the nature of the CURRENT Big Trade (Accumulation, Defense, Exhaustion/Trap, Jump the Creek, etc.).
2. Explain how the "in-between" price action (Delta, Excursions, Time elapsed) confirms or denies the institutional intent.
3. Decide if this is a high-probability entry point.

Output your response EXACTLY as a JSON object with the following fields:
- "narrative": A clear, fluid, and continuous story of what the institutions are doing. (Max 150 words).
- "classification": A 2-4 word label for the current Big Trade (e.g. "Trapped Sellers", "Aggressive Buying", "Passive Defense").
- "entry_decision": "long", "short", or "none".
- "confidence": 0 to 100. (Only > 80 is a valid entry).
- "stop_loss": Price level for stop loss (if entering, else null).
"""

def analyze_bt_node(node: BigTradeNode) -> dict:
    """
    Sends the Node context to the LLM and parses the response.
    """
    context_str = node.to_prompt_string()
    user_msg = f"Here is the context of the current Big Trade Node, the previous Big Trade Node, and the price action that occurred between them:\n\n{context_str}"
    
    try:
        raw_resp = llm_ask(BT_NARRATIVE_PROMPT, user_msg)
        
        # Parse JSON
        resp_clean = raw_resp.strip()
        if resp_clean.startswith('```json'):
            resp_clean = resp_clean.split('```json')[1]
        if resp_clean.endswith('```'):
            resp_clean = resp_clean.rsplit('```', 1)[0]
            
        return json.loads(resp_clean.strip())
        
    except Exception as e:
        logger.error(f"Error calling LLM for BT Node: {e}")
        return {
            "narrative": f"Error: {str(e)}",
            "classification": "Error",
            "entry_decision": "none",
            "confidence": 0,
            "stop_loss": None
        }
