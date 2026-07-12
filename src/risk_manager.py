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
    Calculates number of contracts based on account equity and exact stop distance
    to maintain a constant risk percentage per trade.
    """
    if entry == stop:
        return min_contracts

    # Determine tick value
    tick_val = 5.00 if instrument.upper() == 'NQ' else 0.50
    
    # Calculate risk amount in USD
    risk_usd = equity * risk_pct
    if max_risk_usd is not None:
        risk_usd = min(risk_usd, max_risk_usd)
        
    # Calculate distance in ticks
    dist_ticks = abs(entry - stop) / 0.25
    if dist_ticks <= 0:
        return min_contracts
        
    # Contracts = Risk_USD / (Dist_Ticks * Tick_Value)
    contracts = risk_usd / (dist_ticks * tick_val)
    
    # CFD/Fractional contracts: return the exact float value rounded to 4 decimals
    return round(contracts, 4)

def calculate_commissions(contracts: int, instrument: str = 'NQ') -> float:
    """
    Standard round-turn commissions.
    NQ: ~$5.00 per RT ($2.50 per side).
    MNQ: ~$1.20 per RT ($0.60 per side).
    """
    per_side = 2.50 if instrument.upper() == 'NQ' else 0.60
    return contracts * per_side * 2
