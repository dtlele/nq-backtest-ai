"""
Module for Risk Management and Position Sizing.
Calculates the number of contracts based on account equity and structural stop distance.
"""
import math

# Tick Parameters (NQ = E-mini, MNQ = Micro)
NQ_TICK_VALUE  = 5.00
MNQ_TICK_VALUE = 0.50

def calculate_contracts(
    entry: float, 
    stop: float, 
    equity: float, 
    risk_pct: float = 0.005, 
    instrument: str = 'MNQ',
    setup_category: str = 'momentum',
    min_contracts: int = 1,
    max_risk_usd: float = None
) -> int:
    """
    Calculates number of contracts. Scales risk down for Reversal setups.
    
    Args:
        entry: Entry price.
        stop: Stop loss price.
        equity: Current account equity.
        risk_pct: Baseline risk % (0.005 = 0.5%).
        instrument: 'NQ' or 'MNQ'.
        setup_category: 'momentum' (A-setup) or 'reversal' (C-setup).
        min_contracts: Min contracts to open.
        max_risk_usd: Optional $ cap on loss.
    """
    if entry == stop:
        return min_contracts

    # 1. Scaling for Reversal (C Setup)
    # Fabio targets lower winrate for reversals, so we reduce exposure
    effective_risk_pct = risk_pct
    if setup_category == 'reversal':
        effective_risk_pct = risk_pct * 0.5
        
    # 2. Determine tick value
    tick_val = 5.00 if instrument.upper() == 'NQ' else 0.50
    
    # 3. Calculate risk amount in USD
    risk_usd = equity * effective_risk_pct
    if max_risk_usd is not None:
        risk_usd = min(risk_usd, max_risk_usd)
        
    # 4. Calculate distance in ticks
    dist_ticks = abs(entry - stop) / 0.25

    # Enforce a safety stop floor of 60 ticks (15 points) for sizing calculations to prevent ultra-tight leverage spikes
    effective_dist_ticks = max(60.0, dist_ticks)

    # Apply tighter risk reduction for very narrow stops (<10 ticks originally, now using effective)
    if dist_ticks < 10:
        effective_risk_pct *= 0.5
    
    if dist_ticks <= 0:
        return min_contracts
        
    # 5. Contracts = Risk_USD / (Effective_Dist_Ticks * Tick_Value)
    contracts = risk_usd / (effective_dist_ticks * tick_val)
    
    # 6. Safety Floor
    final_contracts = max(min_contracts, math.floor(contracts))
    
    return final_contracts

def calculate_commissions(contracts: int, instrument: str = 'NQ') -> float:
    """
    Standard round-turn commissions.
    NQ: ~$5.00 per RT ($2.50 per side).
    MNQ: ~$1.20 per RT ($0.60 per side).
    """
    per_side = 2.50 if instrument.upper() == 'NQ' else 0.60
    return contracts * per_side * 2
