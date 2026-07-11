import dspy
from src.agents.dspy_llm_wrapper import CustomOpenRouterLM

class FabioSignature(dspy.Signature):
    """
    Evaluate the current market context (trend, VWAP, Big Trades).
    Identify structural imbalances and determine if a valid trading setup exists.
    If valid, calculate precise mechanical execution: entry, structurally-placed stop loss (behind a Big Trade wall), and target.
    If no setup exists, set setup_valid to False.
    """
    market_data = dspy.InputField(desc="Recent M1 bars, volume profile, VWAP context, and active rules.")
    
    setup_valid = dspy.OutputField(desc="Boolean indicating if a valid setup exists.", prefix="setup_valid:")
    direction = dspy.OutputField(desc="Execution direction: long, short, or none.")
    confidence = dspy.OutputField(desc="Confidence score 0-100.")
    entry = dspy.OutputField(desc="Entry price.")
    stop = dspy.OutputField(desc="Stop loss price (structurally protected).")
    target = dspy.OutputField(desc="Profit target price.")
    reasoning = dspy.OutputField(desc="MAX 150 WORDS: cite the specific Big Trade wall protecting the stop, exact stop placement logic, and target rationale. If no setup, explain why.")

class FabioAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step = dspy.ChainOfThought(FabioSignature)
        
    def forward(self, market_data):
        # Single Step: Evaluation & Execution
        result = self.step(market_data=market_data)
        
        # Parse the setup_valid boolean properly
        is_valid = str(result.setup_valid).lower() in ['true', 'yes', '1']
        
        return dspy.Prediction(
            setup_valid=is_valid,
            direction=result.direction if is_valid else "none",
            confidence=result.confidence if is_valid else 0,
            entry=result.entry if is_valid else 0.0,
            stop=result.stop if is_valid else 0.0,
            target=result.target if is_valid else 0.0,
            reasoning=result.reasoning
        )

# Ensure DSPy uses our custom wrapper
lm = CustomOpenRouterLM(model="deepseek/deepseek-chat")
dspy.settings.configure(lm=lm)
