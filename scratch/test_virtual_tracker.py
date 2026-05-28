import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timezone, timedelta
from src import Bar
from src.virtual_missed_trade_tracker import VirtualTradeTracker

# Setup dummy bars
base_time = datetime.now(timezone.utc)
bars = [
    Bar(timestamp=base_time + timedelta(minutes=0), open=21700.0, high=21710.0, low=21690.0, close=21705.0, volume=4000, buy_volume=2000, sell_volume=2000, delta=0, delta_pct=0.0, cvd=0, vwap=21700.0),
    Bar(timestamp=base_time + timedelta(minutes=5), open=21705.0, high=21740.0, low=21700.0, close=21735.0, volume=5000, buy_volume=3000, sell_volume=2000, delta=1000, delta_pct=20.0, cvd=1000, vwap=21720.0),
    Bar(timestamp=base_time + timedelta(minutes=10), open=21735.0, high=21750.0, low=21680.0, close=21685.0, volume=6000, buy_volume=2500, sell_volume=3500, delta=-1000, delta_pct=16.6, cvd=0, vwap=21710.0),
]

def test_tracker():
    print("Testing VirtualTradeTracker...")
    tracker = VirtualTradeTracker("2026-05-27")
    
    # 1. Add a virtual LONG trade that should hit target in bar 1
    # Entry: 21705.0, Stop: 21690.0, Target: 21730.0
    tracker.add_virtual_trade(
        direction="long",
        entry=21705.0,
        stop=21690.0,
        target=21730.0,
        setup_type="ivb_breakout",
        confidence=60,
        skip_reason="Confidence below required threshold (60 < 75)",
        entry_bar=bars[0]
    )
    
    # 2. Add a virtual SHORT trade that should hit stop in bar 2
    # Entry: 21735.0, Stop: 21745.0, Target: 21700.0
    # In bar 2 (high=21750.0, low=21680.0), both target and stop are hit, stop-out takes precedence (pessimistic check)
    tracker.add_virtual_trade(
        direction="short",
        entry=21735.0,
        stop=21745.0,
        target=21700.0,
        setup_type="reversal",
        confidence=55,
        skip_reason="Andrea vetoed",
        entry_bar=bars[1]
    )
    
    print(f"Active trades before update: {len(tracker.active_trades)}")
    assert len(tracker.active_trades) == 2
    
    # Update through bar 1 (high=21740.0, low=21700.0)
    messages_1 = tracker.update([bars[1]])
    print(f"Messages after bar 1 update:")
    for msg in messages_1:
        print(f"  {msg}")
    
    # Update through bar 2 (high=21750.0, low=21680.0)
    messages_2 = tracker.update([bars[2]])
    print(f"Messages after bar 2 update:")
    for msg in messages_2:
        print(f"  {msg}")
        
    print(f"Active trades remaining: {len(tracker.active_trades)}")
    
    # Test EOD close
    tracker.add_virtual_trade(
        direction="long",
        entry=21685.0,
        stop=21650.0,
        target=21750.0,
        setup_type="squeeze",
        confidence=50,
        skip_reason="Precision abort",
        entry_bar=bars[2]
    )
    eod_messages = tracker.close_remaining_eod(bars[2])
    print(f"EOD Messages:")
    for msg in eod_messages:
        print(f"  {msg}")
        
    print("Test completed successfully!")

if __name__ == "__main__":
    test_tracker()
