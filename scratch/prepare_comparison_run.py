import os
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))

from src.backtest_runner import run_backtest, DATA_DIR
from src.agent_memory import reset_session, save_session, load_session, TRADES_FILE

def prepare_risk_run():
    print("Preparing Risk-Adjusted Comparison Backtest (July-August 2025)...")
    
    # 1. Define a separate log file for the risk-adjusted run
    # This avoids mixing results with the original human-validated backtest
    new_trades_log = Path('agent_memory/trades_log_risk_adjusted.jsonl')
    new_reasoning_log = Path('agent_memory/reasoning_log_risk_adjusted.jsonl')
    
    # We'll temporarily override the TRADES_FILE path in the module
    # (Note: In a more robust system, this would be a parameter, but for this comparison script we override)
    import src.agent_memory
    src.agent_memory.TRADES_FILE = new_trades_log
    src.agent_memory.LOG_FILE = new_reasoning_log
    
    print(f"New Trades Log: {new_trades_log}")
    
    # 2. Reset Session with $100,000 Equity
    # We use July 1st as the logical start
    state = reset_session("2025-07-01")
    state['equity'] = 100000.0
    save_session(state)
    
    print(f"Session Reset. Starting Equity: ${state['equity']}")
    
    # 3. Setup CLI instructions
    print("\nREADY TO RUN.")
    print("To start the comparison backtest, run:")
    print("python run_backtest.py --start-date 20250701")
    print("\nNOTE: The runner will now use 0.5% risk per trade with MNQ contracts.")

if __name__ == "__main__":
    prepare_risk_run()
