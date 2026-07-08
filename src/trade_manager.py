from dataclasses import dataclass
from datetime import datetime
from src import Bar, Trade
from src.footprint_engine import get_bar_poc

@dataclass
class ActiveTrade:
    direction: str         # 'long' | 'short'
    entry_price: float
    entry_ts: datetime
    initial_sl: float
    sl: float
    risk_pts: float
    max_profit_pts: float = 0.0
    is_breakeven: bool = False
    status: str = 'active' # 'active', 'stopped', 'closed_eod'
    setup_reason: str = ""

def evaluate_trade_tick(trade: ActiveTrade, current_price: float, current_ts: datetime) -> bool:
    """
    Evaluate trade against current tick price.
    Returns True if trade has been stopped out, updating its status.
    """
    if trade.status != 'active':
        return True

    # Track maximum profit (MFE)
    if trade.direction == 'long':
        profit = current_price - trade.entry_price
        if profit > trade.max_profit_pts:
            trade.max_profit_pts = profit
        
        # Stop loss check
        if current_price <= trade.sl:
            trade.status = 'stopped'
            return True
            
    elif trade.direction == 'short':
        profit = trade.entry_price - current_price
        if profit > trade.max_profit_pts:
            trade.max_profit_pts = profit
            
        # Stop loss check
        if current_price >= trade.sl:
            trade.status = 'stopped'
            return True
            
    return False

def update_trailing_stop(
    trade: ActiveTrade, 
    new_bar: Bar, 
    poc_volume_threshold: int = 179,
    breakeven_R: float = 1.0
) -> float:
    """
    Update the trailing stop based on:
    1. Breakeven rule: if MFE >= 1.0R, move SL to entry.
    2. Structural rule: if a new bar has an institutional POC, move SL behind it.
    """
    if trade.status != 'active':
        return trade.sl

    # 1. Check Breakeven
    if not trade.is_breakeven and trade.risk_pts > 0:
        if trade.max_profit_pts >= (trade.risk_pts * breakeven_R):
            trade.sl = trade.entry_price
            trade.is_breakeven = True

    # 2. Check Structural POC trailing
    poc_price, poc_vol = get_bar_poc(new_bar)
    if poc_vol >= poc_volume_threshold:
        if trade.direction == 'long':
            # Move stop to 1.0 point below the low of this new POC bar
            # ONLY move it UP (never down)
            new_sl = new_bar.low - 1.0
            if new_sl > trade.sl:
                trade.sl = new_sl
        elif trade.direction == 'short':
            # Move stop to 1.0 point above the high of this new POC bar
            # ONLY move it DOWN (never up)
            new_sl = new_bar.high + 1.0
            if new_sl < trade.sl:
                trade.sl = new_sl

    return trade.sl
