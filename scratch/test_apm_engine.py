import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timezone, timedelta
from src import Bar, ConsensusSignal, OpenTrade, ClosedTrade
from src.trade_simulator import open_trade, step_trade, close_early

# Setup dummy bars
base_time = datetime.now(timezone.utc)
bars = [
    Bar(timestamp=base_time, open=21700.0, high=21710.0, low=21690.0, close=21705.0, volume=4000, buy_volume=2000, sell_volume=2000, delta=0, delta_pct=0.0, cvd=0, vwap=21700.0),
    Bar(timestamp=base_time + timedelta(minutes=5), open=21705.0, high=21715.0, low=21700.0, close=21710.0, volume=5000, buy_volume=3000, sell_volume=2000, delta=1000, delta_pct=20.0, cvd=1000, vwap=21720.0),
    Bar(timestamp=base_time + timedelta(minutes=10), open=21710.0, high=21720.0, low=21695.0, close=21700.0, volume=6000, buy_volume=2500, sell_volume=3500, delta=-1000, delta_pct=16.6, cvd=0, vwap=21710.0),
]

def test_apm_simulation():
    print("Testing APM Simulator logic...")
    
    # 1. Create a dummy Consensus for an active trade
    class _DummyConsensus:
        direction = 'long'
        entry = 21700.0
        stop = 21680.0
        target = 21750.0
        r_ratio = 2.5
        class _Sub:
            setup_type = 'ivb_breakout'
            reasoning = 'initial breakout long'
        fabio = _Sub()
        andrea = _Sub()
        final_confidence = 75
        
    consensus = _DummyConsensus()
    
    # 2. Open a trade on bar 0
    trade = open_trade(consensus, bars[0], contracts=10)
    print(f"Opened trade: {trade.direction.upper()} at {trade.entry:.2f} | stop={trade.stop:.2f} target={trade.target:.2f}")
    assert trade.contracts == 10
    
    # 3. Simulate step_trade candle-by-candle
    # Intermediate bar 1
    result = step_trade(trade, [bars[1]])
    assert result is None  # Trade still open, no stops/targets hit
    print("Bar 1 stepped: trade remains open mechanically.")
    
    # 4. Simulate a TRAIL stop decision
    new_stop = 21695.0
    print(f"APM trail stop request: new_stop={new_stop}")
    if new_stop > trade.stop:
        trade.stop = new_stop
        print(f" -> Stop trailed to {trade.stop}")
    assert trade.stop == 21695.0
    
    # 5. Simulate an EARLY_EXIT decision on Bar 2
    # In Bar 2, price is 21700.0 (still above stop 21695.0)
    # But Fabio decides to exit early
    reasoning = "Trapped buyers detected, bid wall collapsed."
    closed = close_early(trade, bars[2], reasoning)
    
    print(f"Closed early: exit={closed.exit_price:.2f} reason={closed.exit_reason} pnl={closed.pnl_usd:.1f}$")
    assert closed.exit_reason == "early_Trapped buyers detec" # truncated to 20 chars
    assert closed.exit_price == 21700.0
    
    # Calculate P&L: long, exit 21700.0, entry 21700.0 -> P&L gross 0.
    # Commissions: $2.42 per round turn per contract (default) -> for 10 contracts, commissions = -$24.20
    print(f"Commissions: {closed.pnl_usd:.2f}$ (Expected roughly -24.20$ net due to 10 contracts commissions)")
    assert closed.pnl_usd < 0  # net pnl must be negative due to commissions
    
    print("APM Simulator test completed successfully!")

if __name__ == "__main__":
    test_apm_simulation()
