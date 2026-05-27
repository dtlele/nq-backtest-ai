import pandas as pd
import numpy as np
from src import Trade, Bar, NQ_BIG_TRADE_THRESHOLD

def aggregate_to_bars(trades: list, freq: str = '1min') -> list:
    if not trades:
        return []
    records = [{
        'ts':    pd.Timestamp(t.ts_event).tz_convert('UTC') if t.ts_event.tzinfo else pd.Timestamp(t.ts_event).tz_localize('UTC'),
        'side':  t.side,
        'price': t.price,
        'size':  t.size,
    } for t in trades]

    df = pd.DataFrame(records).set_index('ts').sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')

    df['buy_vol']  = np.where(df['side'] == 'A', df['size'], 0)
    df['sell_vol'] = np.where(df['side'] == 'B', df['size'], 0)
    df['dollar']   = df['price'] * df['size']

    g      = df.resample(freq)
    ohlcv  = g['price'].ohlc()
    vol    = g['size'].sum().rename('volume')
    buy    = g['buy_vol'].sum().rename('buy_volume')
    sell   = g['sell_vol'].sum().rename('sell_volume')
    dollar = g['dollar'].sum().rename('dollar')

    agg = pd.concat([ohlcv, vol, buy, sell, dollar], axis=1).dropna(subset=['open'])
    agg['delta']     = agg['buy_volume'] - agg['sell_volume']
    agg['delta_pct'] = np.where(agg['volume'] > 0,
                                agg['delta'].abs() / agg['volume'] * 100, 0.0)
    agg['vwap']      = np.where(agg['volume'] > 0,
                                agg['dollar'] / agg['volume'], agg['close'])
    agg['cvd']       = agg['delta'].cumsum()
    # Trades with side='N' (unknown aggressor) count toward total volume but not buy/sell
    unknown_vol = agg['volume'] - agg['buy_volume'] - agg['sell_volume']
    if (unknown_vol > 0).any():
        pass # Muted UserWarning to prevent terminal noise during assisted backtest

    # --- MBO FOOTPRINT BUBBLE RECONSTRUCTION ---
    # To mimic DeepCharts/Fabio's "Big Trades", we calculate the 1-minute 
    # footprint (volume per price per side) and filter for clusters >= NQ_BIG_TRADE_THRESHOLD.
    # We use 1min specifically because Fabio's entry triggers are on the M1 footprint.
    df['m1_floor'] = df.index.floor('1min')
    
    # Ignore 'N' (unknown) side for footprint walls
    footprint = df[df['side'] != 'N'].groupby(['m1_floor', 'side', 'price'])['size'].sum().reset_index()
    bubbles = footprint[footprint['size'] >= NQ_BIG_TRADE_THRESHOLD]

    big_map: dict = {}
    for _, row in bubbles.iterrows():
        # The bubble's exact M1 timestamp
        ts_m1 = row['m1_floor']
        
        # We must map the bubble to the parent M5 (or freq) candle it belongs to
        ts_parent = ts_m1.floor(freq)
        
        bubble_trade = Trade(
            ts_event=ts_m1.to_pydatetime(),
            side=row['side'],
            price=float(row['price']),
            size=int(row['size'])
        )
        big_map.setdefault(ts_parent, []).append(bubble_trade)

    bars = []
    for ts, row in agg.iterrows():
        bars.append(Bar(
            timestamp   = ts.to_pydatetime(),
            open        = float(row['open']),
            high        = float(row['high']),
            low         = float(row['low']),
            close       = float(row['close']),
            volume      = int(row['volume']),
            buy_volume  = int(row['buy_volume']),
            sell_volume = int(row['sell_volume']),
            delta       = int(row['delta']),
            delta_pct   = float(row['delta_pct']),
            cvd         = int(row['cvd']),
            vwap        = float(row['vwap']),
            big_trades  = big_map.get(ts, []),
        ))
    return bars
