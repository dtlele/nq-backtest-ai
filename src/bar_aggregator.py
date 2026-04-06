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

    # Map big trades to bar floor timestamp
    big_map: dict = {}
    for trade, rec in zip(trades, records):
        if trade.size >= NQ_BIG_TRADE_THRESHOLD:
            floor = rec['ts'].floor(freq)
            big_map.setdefault(floor, []).append(trade)

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
