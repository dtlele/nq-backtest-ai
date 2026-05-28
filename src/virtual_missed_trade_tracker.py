import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from src import Bar

MEMORY_DIR = Path(__file__).parent.parent / 'agent_memory'
VIRTUAL_TRADES_FILE = MEMORY_DIR / 'virtual_trades_log.jsonl'

@dataclass
class VirtualTrade:
    direction: str             # 'long' | 'short'
    entry: float
    stop: float
    target: float
    setup_type: str
    confidence: int
    skip_reason: str
    entry_bar: Bar
    date: str                  # 'YYYY-MM-DD'
    entry_time: datetime       # UTC datetime of the entry bar

class VirtualTradeTracker:
    def __init__(self, date_str: str):
        self.date_str = date_str  # YYYY-MM-DD
        self.active_trades = []
        
    def add_virtual_trade(self, direction: str, entry: float, stop: float, target: float, 
                          setup_type: str, confidence: int, skip_reason: str, entry_bar: Bar) -> None:
        """Add a virtual trade to the tracker."""
        if not entry or not stop or not target or direction == 'none':
            return
        
        trade = VirtualTrade(
            direction=direction,
            entry=entry,
            stop=stop,
            target=target,
            setup_type=setup_type,
            confidence=confidence,
            skip_reason=skip_reason,
            entry_bar=entry_bar,
            date=self.date_str,
            entry_time=entry_bar.timestamp
        )
        self.active_trades.append(trade)
        
    def update(self, bars: list[Bar]) -> list[str]:
        """
        Advance active virtual trades through the new bars.
        Returns a list of formatted feedback messages for any virtual trades closed.
        """
        closed_messages = []
        for bar in bars:
            still_active = []
            for trade in self.active_trades:
                closed_trade = self._check_exit(trade, bar)
                if closed_trade:
                    # Save to virtual trades log
                    self._log_virtual_trade(closed_trade)
                    # Create feedback message
                    closed_messages.append(self._format_feedback(closed_trade))
                else:
                    still_active.append(trade)
            self.active_trades = still_active
        return closed_messages

    def close_remaining_eod(self, last_bar: Bar) -> list[str]:
        """Close any remaining open virtual trades at End of Day close price."""
        closed_messages = []
        for trade in self.active_trades:
            closed_trade = self._close_trade(trade, last_bar.close, 'eod', last_bar)
            self._log_virtual_trade(closed_trade)
            closed_messages.append(self._format_feedback(closed_trade))
        self.active_trades = []
        return closed_messages

    def _check_exit(self, trade: VirtualTrade, bar: Bar) -> Optional[dict]:
        """Check if the bar triggered the target or stop for the virtual trade."""
        if trade.direction == 'long':
            # Check Stop first (conservative/pessimistic)
            if bar.low <= trade.stop:
                return self._close_trade(trade, trade.stop, 'stop', bar)
            elif bar.high >= trade.target:
                return self._close_trade(trade, trade.target, 'target', bar)
        else:  # short
            if bar.high >= trade.stop:
                return self._close_trade(trade, trade.stop, 'stop', bar)
            elif bar.low <= trade.target:
                return self._close_trade(trade, trade.target, 'target', bar)
        return None

    def _close_trade(self, trade: VirtualTrade, exit_price: float, exit_reason: str, exit_bar: Bar) -> dict:
        """Compute virtual trade results and return a dictionary."""
        sign = 1 if trade.direction == 'long' else -1
        pnl_ticks = sign * (exit_price - trade.entry) / 0.25
        pnl_usd = pnl_ticks * 0.50 # MNQ standard 0.50 per tick per contract
        
        # Calculate Risk and Reward to R Ratio
        risk = abs(trade.entry - trade.stop)
        reward = abs(trade.target - trade.entry)
        r_ratio = round(reward / risk, 2) if risk > 0 else 0.0

        return {
            'date': trade.date,
            'entry_time': trade.entry_time.isoformat(),
            'exit_time': exit_bar.timestamp.isoformat(),
            'direction': trade.direction,
            'entry': trade.entry,
            'stop': trade.stop,
            'target': trade.target,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_ticks': pnl_ticks,
            'pnl_usd': pnl_usd,
            'r_ratio': r_ratio,
            'setup_type': trade.setup_type,
            'confidence': trade.confidence,
            'skip_reason': trade.skip_reason,
            'logged_at': datetime.now(timezone.utc).isoformat()
        }

    def _log_virtual_trade(self, closed_trade: dict) -> None:
        """Append one closed virtual trade to the virtual_trades JSONL log."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            with open(VIRTUAL_TRADES_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(closed_trade, ensure_ascii=False) + '\n')
        except Exception as e:
            # Silence logging failures to avoid disrupting the run
            pass

    def _format_feedback(self, closed_trade: dict) -> str:
        """Format the virtual trade outcome into a highly descriptive session buffer comment."""
        emoji = "✅" if closed_trade['pnl_usd'] > 0 else "❌"
        exit_time_utc = datetime.fromisoformat(closed_trade['exit_time']).strftime('%H:%M UTC')
        pnl = f"+{closed_trade['pnl_usd']:.1f}$" if closed_trade['pnl_usd'] > 0 else f"{closed_trade['pnl_usd']:.1f}$"
        
        # Human-friendly result
        if closed_trade['exit_reason'] == 'target':
            result_str = f"HIT TARGET ({closed_trade['target']:.2f})"
        elif closed_trade['exit_reason'] == 'stop':
            result_str = f"HIT STOP ({closed_trade['stop']:.2f})"
        else:
            result_str = f"CLOSED EOD ({closed_trade['exit_price']:.2f})"
            
        return (
            f"{emoji} [VIRTUAL {closed_trade['exit_reason'].upper()}] {exit_time_utc} "
            f"{closed_trade['direction'].upper()} entry={closed_trade['entry']:.2f} {result_str} pnl={pnl} "
            f"(Skipped: {closed_trade['skip_reason']})"
        )
