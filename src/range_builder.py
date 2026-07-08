import numpy as np
from collections import defaultdict
from datetime import datetime
from src import Trade, Bar

def build_range_bars(trades: list[Trade], range_points: float = 10.0, big_trade_threshold: int = 10) -> list[Bar]:
    """
    Build Range bars from a list of Trade objects.
    A bar closes as soon as high - low >= range_points.
    Each bar is populated with volume, buy/sell volume, delta, vwap, footprint, and big trades.
    """
    if not trades:
        return []

    bars = []
    current_candle = None
    cvd = 0

    for t in trades:
        price = t.price
        qty = t.size
        side = t.side
        ts = t.ts_event

        if current_candle is None:
            current_candle = {
                'timestamp': ts,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': 0,
                'buy_volume': 0,
                'sell_volume': 0,
                'dollar_sum': 0.0,
                'footprint': defaultdict(lambda: {'bid': 0, 'ask': 0}),
                'big_trades': []
            }

        # Update metrics
        current_candle['volume'] += qty
        current_candle['dollar_sum'] += price * qty

        if side == 'A':
            current_candle['buy_volume'] += qty
            current_candle['footprint'][price]['ask'] += qty
        elif side == 'B':
            current_candle['sell_volume'] += qty
            current_candle['footprint'][price]['bid'] += qty

        # Big trade detection
        if qty >= big_trade_threshold and side in ('A', 'B'):
            current_candle['big_trades'].append(t)

        # Update extremes
        if price > current_candle['high']:
            current_candle['high'] = price
        if price < current_candle['low']:
            current_candle['low'] = price
        current_candle['close'] = price

        # Check range breach
        if (current_candle['high'] - current_candle['low']) >= range_points:
            # Finalize bar
            vol = current_candle['volume']
            buy_vol = current_candle['buy_volume']
            sell_vol = current_candle['sell_volume']
            delta = buy_vol - sell_vol
            cvd += delta
            
            vwap = current_candle['dollar_sum'] / vol if vol > 0 else current_candle['close']
            delta_pct = (abs(delta) / vol * 100.0) if vol > 0 else 0.0

            bars.append(Bar(
                timestamp=current_candle['timestamp'],
                open=current_candle['open'],
                high=current_candle['high'],
                low=current_candle['low'],
                close=current_candle['close'],
                volume=vol,
                buy_volume=buy_vol,
                sell_volume=sell_vol,
                delta=delta,
                delta_pct=delta_pct,
                cvd=cvd,
                vwap=vwap,
                big_trades=current_candle['big_trades'],
                footprint=dict(current_candle['footprint'])
            ))
            current_candle = None

    # Handle the last incomplete bar if any
    if current_candle is not None:
        vol = current_candle['volume']
        if vol > 0:
            buy_vol = current_candle['buy_volume']
            sell_vol = current_candle['sell_volume']
            delta = buy_vol - sell_vol
            cvd += delta
            vwap = current_candle['dollar_sum'] / vol
            delta_pct = (abs(delta) / vol * 100.0)
            bars.append(Bar(
                timestamp=current_candle['timestamp'],
                open=current_candle['open'],
                high=current_candle['high'],
                low=current_candle['low'],
                close=current_candle['close'],
                volume=vol,
                buy_volume=buy_vol,
                sell_volume=sell_vol,
                delta=delta,
                delta_pct=delta_pct,
                cvd=cvd,
                vwap=vwap,
                big_trades=current_candle['big_trades'],
                footprint=dict(current_candle['footprint'])
            ))

    return bars
