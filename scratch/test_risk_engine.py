import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))

from src.risk_manager import calculate_contracts, calculate_commissions
from src.trade_simulator import open_trade, _close
from src import Bar, ConsensusSignal, FabioSignal, AndreaSignal
from datetime import datetime

def test_risk_logic():
    print("Testing Risk Logic...")
    
    # Setup
    equity = 100000.0
    entry = 20000.0
    stop = 19950.0  # 50 points = 200 ticks
    target = 20100.0
    
    # 1. Calculate Contracts (0.5% risk = $500)
    # Expected: $500 / (200 * 0.5) = 5 contracts
    contracts = calculate_contracts(entry, stop, equity, risk_pct=0.005, instrument='MNQ')
    print(f"Contracts: {contracts} (Expected: 5)")
    
    # 2. Open Trade
    fabio = FabioSignal(direction='long', confidence=80, entry=entry, stop=stop, target=target, setup_type='squeeze', reasoning='test', nlm_answer='test')
    andrea = AndreaSignal(confirmation=True, confidence=80, setup_type='ibob', reasoning='test', nlm_answer='test')
    consensus = ConsensusSignal(direction='long', entry=entry, stop=stop, target=target, r_ratio=2.0, final_confidence=80, fabio=fabio, andrea=andrea, decision='trade', no_trade_reason='')
    
    bar = Bar(timestamp=datetime.now(), open=entry, high=entry+10, low=entry-10, close=entry, volume=1000, buy_volume=500, sell_volume=500, delta=0, delta_pct=0, cvd=0, vwap=entry)
    
    trade = open_trade(consensus, bar, contracts=contracts)
    print(f"Opened Trade with {trade.contracts} contracts.")
    
    # 3. Close at Target
    # Expected: 200 ticks * 0.5 * 5 = $500 Gross. Commissions = 5 * 0.6 * 2 = $6.0. Net = $494.
    closed = _close(trade, target, 'target', bar)
    print(f"PnL USD: {closed.pnl_usd} (Expected: 494.0)")
    
    # 4. Close at Stop
    # Expected: -200 ticks * 0.5 * 5 = -$500 Gross. Commissions = $6. Net = -$506.
    closed = _close(trade, stop, 'stop', bar)
    print(f"PnL USD: {closed.pnl_usd} (Expected: -506.0)")

if __name__ == "__main__":
    test_risk_logic()
