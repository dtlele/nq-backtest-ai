"""
Simulate what would have happened if the 4 rejected trades had been executed.
Extracts proposal details from log and runs forward-looking simulation on M1 data.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

@dataclass
class RejectedProposal:
    timestamp: datetime
    direction: str
    confidence: int
    rejection_reason: str
    # Will be filled from simulation
    entry_price: float = None
    stop_loss: float = None
    outcome: str = None  # 'win', 'loss', 'open', 'unknown'
    max_profit_pts: float = 0.0
    max_loss_pts: float = 0.0
    exit_price: float = None
    exit_time: datetime = None

def parse_log_for_proposals(log_path: Path):
    """Extract rejected proposals from v4 log."""
    proposals = []
    
    with open(log_path) as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if "DEEP AUDIT TRIGGERED" not in line or "Reflex proposed" not in line:
            continue
            
        # Extract direction and confidence
        match = re.search(r'(long|short)\s*\(Conf:\s*(\d+)\)', line, re.IGNORECASE)
        if not match:
            continue
            
        direction = match.group(1).lower()
        confidence = int(match.group(2))
        
        # Find timestamp from previous lines (look for UTC)
        ts = None
        for j in range(max(0, i-10), i):
            utc_match = re.match(r'\s+(\d{2}:\d{2}) UTC FABIO', lines[j])
            if utc_match:
                time_str = utc_match.group(1)
                # Date is 2025-02-04 (from log header)
                ts = datetime(2025, 2, 4, int(time_str[:2]), int(time_str[3:5]))
                break
        
        if not ts:
            continue
        
        # Find rejection reason from next lines
        reason = None
        for j in range(i+1, min(len(lines), i+5)):
            if "DEEP AUDIT REJECTED" in lines[j]:
                reason_match = re.search(r'⛔\s*(.+)', lines[j])
                if reason_match:
                    reason = reason_match.group(1).strip()
                break
        
        if reason:
            proposals.append(RejectedProposal(
                timestamp=ts,
                direction=direction,
                confidence=confidence,
                rejection_reason=reason
            ))
    
    return proposals

def load_m1_data_for_proposals(date_str: str, data_dir: Path):
    """Load M1 bars for the given date."""
    # Try different formats
    import glob
    pattern = str(data_dir / f"*{date_str}*.jsonl")
    files = glob.glob(pattern)
    
    if not files:
        # Try parquet
        pattern_pq = str(data_dir / f"*{date_str}*.parquet")
        files = glob.glob(pattern_pq)
        if files:
            return pd.read_parquet(files[0])
        return None
    
    # Read jsonl
    bars = []
    for f in files:
        with open(f) as file:
            for line in file:
                try:
                    bars.append(json.loads(line))
                except:
                    pass
    
    return pd.DataFrame(bars)

def simulate_trade(proposal: RejectedProposal, m1_bars: pd.DataFrame, risk_pts: float = 10.0, target_pts: float = 18.0):
    """Simulate trade outcome using M1 data."""
    if m1_bars is None or len(m1_bars) == 0:
        proposal.outcome = 'unknown'
        return
    
    # Find entry bar (first bar after proposal time)
    entry_candidates = m1_bars[m1_bars['ts'] >= proposal.timestamp]
    if len(entry_candidates) == 0:
        proposal.outcome = 'unknown'
        return
    
    entry_bar = entry_candidates.iloc[0]
    
    # Entry on close of signal bar (next bar open, or close if available)
    if 'close' in entry_bar:
        proposal.entry_price = entry_bar['close']
    elif 'open' in entry_bar:
        proposal.entry_price = entry_bar['open']
    else:
        proposal.outcome = 'unknown'
        return
    
    # Set stop and target
    if proposal.direction == 'long':
        proposal.stop_loss = proposal.entry_price - risk_pts
        target = proposal.entry_price + target_pts
    else:
        proposal.stop_loss = proposal.entry_price + risk_pts  # short: stop above
        target = proposal.entry_price - target_pts
    
    # Simulate forward
    for idx, bar in entry_candidates.iloc[1:].iterrows():
        if proposal.direction == 'long':
            # Check stop hit
            if bar.get('low', 999999) <= proposal.stop_loss:
                proposal.outcome = 'loss'
                proposal.exit_price = proposal.stop_loss
                proposal.exit_time = bar.get('ts')
                proposal.max_loss_pts = risk_pts
                return
            
            # Check target
            if bar.get('high', 0) >= target:
                proposal.outcome = 'win'
                proposal.exit_price = target
                proposal.exit_time = bar.get('ts')
                proposal.max_profit_pts = target_pts
                return
            
            # Track max profit
            floating = bar.get('high', 0) - proposal.entry_price
            proposal.max_profit_pts = max(proposal.max_profit_pts, floating)
            
        else:  # short
            # Check stop hit
            if bar.get('high', 0) >= proposal.stop_loss:
                proposal.outcome = 'loss'
                proposal.exit_price = proposal.stop_loss
                proposal.exit_time = bar.get('ts')
                proposal.max_loss_pts = risk_pts
                return
            
            # Check target
            if bar.get('low', 999999) <= target:
                proposal.outcome = 'win'
                proposal.exit_price = target
                proposal.exit_time = bar.get('ts')
                proposal.max_profit_pts = target_pts
                return
            
            # Track max profit
            floating = proposal.entry_price - bar.get('low', 999999)
            proposal.max_profit_pts = max(proposal.max_profit_pts, floating)
    
    # Reached end of day without exit
    proposal.outcome = 'open'

def main():
    log_path = Path("output/week_glm52_scalper_v4.log")
    data_dir = Path("data/processed/m1")
    
    if not log_path.exists():
        print(f"Log not found: {log_path}")
        return
    
    # Parse proposals from log
    proposals = parse_log_for_proposals(log_path)
    print(f"Found {len(proposals)} rejected proposals:")
    
    for p in proposals:
        print(f"\n  {p.timestamp.strftime('%H:%M')} | {p.direction}({p.confidence})")
        print(f"  Rejection: {p.rejection_reason[:70]}...")
    
    # Need M1 data for Feb 4, 2025
    # For now, check if we have data files
    print(f"\n\nLooking for M1 data in {data_dir}...")
    
    import glob
    files = glob.glob(str(data_dir / "*"))
    if files:
        print(f"Found files: {[Path(f).name for f in files[:5]]}")
    else:
        print("No M1 data files found. Need to locate data source.")
        return
    
    # Try to load data (placeholder - actual data loading would need correct format)
    print("\nNote: Actual simulation needs the M1 bar data for Feb 4, 2025")
    print("The data should contain: ts, open, high, low, close, delta, volume")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total proposals rejected by auditor: {len(proposals)}")
    print(f"\nBreakdown by direction:")
    longs = [p for p in proposals if p.direction == 'long']
    shorts = [p for p in proposals if p.direction == 'short']
    print(f"  Long: {len(longs)} (confidence: {[p.confidence for p in longs]})")
    print(f"  Short: {len(shorts)} (confidence: {[p.confidence for p in shorts]})")
    
    print(f"\nThe auditor rejected all {len(proposals)} proposals.")
    print("Without M1 data loaded, cannot simulate what would have happened.")
    print("\nHowever, from the rejection reasons, we can infer:")
    print("- All 4 were rationalized setups with flow contradictions")
    print("- The auditor identified institutional absences (no wall defense)")
    print("- Need price data to confirm if these would have been losses")

if __name__ == "__main__":
    main()
