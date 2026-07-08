import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BigTradeEvent:
    time: datetime
    price: float
    size: int
    side: str

@dataclass
class BigTradeNode:
    current_time: datetime
    current_price: float
    current_trades: List[BigTradeEvent]
    
    # Context from previous node
    previous_time: Optional[datetime] = None
    previous_price: Optional[float] = None
    previous_trades: List[BigTradeEvent] = None
    
    # In-between metrics
    elapsed_mins: int = 0
    price_change: float = 0.0
    cumulative_delta: int = 0
    max_excursion: float = 0.0
    min_excursion: float = 0.0
    
    def to_prompt_string(self) -> str:
        s = f"=== CURRENT BIG TRADE NODE at {self.current_time.strftime('%H:%M ET')} ===\n"
        s += f"Price: {self.current_price:.2f}\n"
        for t in self.current_trades:
            s += f"  -> {t.side.upper()} TRADE: {t.size} contracts at {t.price:.2f}\n"
            
        if self.previous_time:
            s += f"\n--- SINCE LAST NODE ({self.previous_time.strftime('%H:%M ET')}) ---\n"
            s += f"Elapsed Time: {self.elapsed_mins} minutes\n"
            s += f"Price Change: {self.price_change:+.2f} points\n"
            s += f"Cumulative Delta: {self.cumulative_delta:+d}\n"
            s += f"Max Upward Excursion: {self.max_excursion:.2f}\n"
            s += f"Max Downward Excursion: {self.min_excursion:.2f}\n"
        else:
            s += "\n--- (First Node of the Session) ---\n"
            
        return s

def extract_big_trade_nodes(m1_bars: List[any]) -> List[BigTradeNode]:
    """
    Scans M1 bars, jumping from Big Trade to Big Trade.
    Calculates intermediate price action (Delta, Excursion).
    """
    nodes = []
    
    last_bt_bar = None
    last_bt_events = []
    
    bars_in_between = []
    
    for bar in m1_bars:
        # Check if current bar has Big Trades
        if hasattr(bar, 'big_trades') and bar.big_trades:
            # We found a node!
            current_events = []
            for bt in bar.big_trades:
                current_events.append(BigTradeEvent(
                    time=getattr(bt, 'timestamp', getattr(bt, 'time', bar.timestamp)),
                    price=getattr(bt, 'price', bar.close),
                    size=getattr(bt, 'size', 0),
                    side=getattr(bt, 'side', 'unknown')
                ))
            
            node = BigTradeNode(
                current_time=bar.timestamp,
                current_price=bar.close,
                current_trades=current_events
            )
            
            if last_bt_bar:
                # Calculate metrics in between
                node.previous_time = last_bt_bar.timestamp
                node.previous_price = last_bt_bar.close
                node.previous_trades = last_bt_events
                
                # elapsed_mins includes the bars in between
                delta_t = bar.timestamp - last_bt_bar.timestamp
                node.elapsed_mins = int(delta_t.total_seconds() / 60)
                node.price_change = bar.close - last_bt_bar.close
                
                # Calculate metrics in between (including the current node's bar)
                excursion_bars = bars_in_between + [bar]
                node.cumulative_delta = sum(getattr(b, 'delta', 0) for b in excursion_bars)
                node.max_excursion = max(getattr(b, 'high', b.close) for b in excursion_bars)
                node.min_excursion = min(getattr(b, 'low', b.close) for b in excursion_bars)
            
            nodes.append(node)
            
            # Reset for next jump
            last_bt_bar = bar
            last_bt_events = current_events
            bars_in_between = []
        else:
            if last_bt_bar:
                bars_in_between.append(bar)
                
    return nodes
