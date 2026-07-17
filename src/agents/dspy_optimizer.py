import json
from pathlib import Path
import dspy
from dspy.teleprompt import BootstrapFewShot

from src.agents.fabio_dspy import FabioAgent
from src.agents.dspy_llm_wrapper import CustomOpenRouterLM

ROOT = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean")
DATASET_PATH = ROOT / "agent_memory" / "dspy_dataset.json"

def load_dataset():
    with open(DATASET_PATH, "r") as f:
        raw_data = json.load(f)
        
    examples = []
    for d in raw_data:
        ex = dspy.Example(
            market_data=d["market_data"],
            setup_valid=d["setup_valid"],
            direction=d["direction"],
            confidence=d["confidence"],
            entry=d["entry"],
            stop=d["stop"],
            target=d["target"],
            reasoning=d["reasoning"]
        ).with_inputs("market_data")
        examples.append(ex)
    return examples

def validate_trade_logic(example, pred, trace=None):
    """
    Our Metric: We want the agent to correctly identify the direction,
    and place the stop loss logically behind the entry.
    """
    try:
        # If the model didn't output a valid trade when it was supposed to
        if str(pred.setup_valid).lower() not in ['true', 'yes', '1']:
            return False
            
        # Direction must match our golden trades
        if str(pred.direction).lower() != str(example.direction).lower():
            return False
            
        # Stop loss validation
        entry = float(pred.entry)
        stop = float(pred.stop)
        
        if str(pred.direction).lower() == "long":
            if stop >= entry: return False
        elif str(pred.direction).lower() == "short":
            if stop <= entry: return False
            
        return True
    except Exception as e:
        return False

def optimize_agent():
    print("Loading dataset...")
    trainset = load_dataset()
    print(f"Loaded {len(trainset)} examples.")
    
    # We will use just a small subset for quick training (e.g., 20 examples)
    trainset = trainset[:20]

    lm = CustomOpenRouterLM(model="z-ai/glm-5.2")
    dspy.settings.configure(lm=lm)
    
    agent = FabioAgent()
    
    print("Initializing Teleprompter (BootstrapFewShot)...")
    teleprompter = BootstrapFewShot(
        metric=validate_trade_logic,
        max_bootstrapped_demos=4,
        max_labeled_demos=16
    )
    
    print("Compiling DSPy Agent...")
    compiled_agent = teleprompter.compile(agent, trainset=trainset)
    
    # Save the compiled prompt state
    compiled_path = ROOT / "agent_memory" / "fabio_dspy_compiled_v2.json"
    compiled_agent.save(str(compiled_path))
    print(f"Compilation successful! Optimized agent saved to {compiled_path}")

if __name__ == "__main__":
    optimize_agent()

