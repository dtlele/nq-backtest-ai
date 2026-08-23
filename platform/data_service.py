"""
DataService: accesso ai dati Databento storici in cache_ohlc/.
Carica CSV giornalieri, aggrega in barre M1/M5, restituisce dati strutturati.
"""
import os
import re
import sys
import warnings
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Aggiungi project root a sys.path se necessario
_THIS_DIR = Path(__file__).parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src import Trade, Bar

# Costanti (copiate da config.py per evitare import circolari con built-in platform)
NQ_BIG_TRADE_THRESHOLD = 30
NQ_TICK_SIZE = 0.25
CACHE_OHLC_DIR = Path(os.environ.get('NQ_CACHE_OHLC_DIR', _PROJECT_ROOT / 'cache_ohlc'))


REQUIRED_COLS = {'ts_event', 'action', 'side', 'price', 'size'}


def _load_csv_raw(filepath: str) -> list:
    """
    Legge un CSV Databento (formato cache_ohlc: YYYYMMDD.csv).
    Restituisce lista di Trade objects.
    Compatibile sia con file nominati YYYYMMDD.csv che YYYYMMDD.trades.csv.
    """
    try:
        header = pd.read_csv(filepath, nrows=0)
    except Exception as e:
        raise ValueError(f"Impossibile leggere {filepath}: {e}")

    all_cols = set(header.columns)
    missing = REQUIRED_COLS - all_cols
    if missing:
        raise ValueError(f"{filepath}: colonne mancanti {missing}")

    read_cols = list(REQUIRED_COLS | ({'symbol'} if 'symbol' in all_cols else set()))

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        df = pd.read_csv(filepath, usecols=read_cols)

    df = df[df['action'] == 'T'].copy()

    # Filtro front-month (esclude spread con '-' nel simbolo)
    if 'symbol' in df.columns:
        outright = df[~df['symbol'].str.contains('-', na=False)]
        if not outright.empty:
            front_month = outright['symbol'].value_counts().idxmax()
            df = outright[outright['symbol'] == front_month].copy()

    if df.empty:
        return []

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Discarding nonzero nanoseconds')
        df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)

    trades = []
    for row in df.itertuples(index=False):
        trades.append(Trade(
            ts_event=row.ts_event.to_pydatetime(),
            side=row.side,
            price=float(row.price),
            size=int(row.size),
        ))
    return trades


def _aggregate_trades_to_bars(trades: list, freq: str = '1min') -> list:
    """
    Aggregazione trade→barre con footprint MBO bubble reconstruction.
    Replica fedelmente src/bar_aggregator.py con supporto livelli bid/ask per prezzo.
    """
    if not trades:
        return []

    records = []
    for t in trades:
        ts = t.ts_event
        if ts.tzinfo is None:
            ts = pd.Timestamp(ts).tz_localize('UTC')
        else:
            ts = pd.Timestamp(ts).tz_convert('UTC')
        records.append({
            'ts': ts,
            'side': t.side,
            'price': t.price,
            'size': t.size,
        })

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

    # --- MBO FOOTPRINT BUBBLE RECONSTRUCTION ---
    df['m1_floor'] = df.index.floor('1min')
    footprint_df = df[df['side'] != 'N'].groupby(['m1_floor', 'side', 'price'])['size'].sum().reset_index()
    bubbles = footprint_df[footprint_df['size'] >= NQ_BIG_TRADE_THRESHOLD]

    big_map: dict = {}
    for _, row in bubbles.iterrows():
        ts_m1    = row['m1_floor']
        ts_parent = ts_m1.floor(freq)
        bubble_trade = Trade(
            ts_event=ts_m1.to_pydatetime(),
            side=row['side'],
            price=float(row['price']),
            size=int(row['size']),
        )
        big_map.setdefault(ts_parent, []).append(bubble_trade)

    # --- FULL FOOTPRINT: bid×ask per price per bar ---
    # Costruisce il footprint completo per ogni barra (tutti i livelli, non solo bolle)
    fp_all = df[df['side'] != 'N'].copy()
    fp_all['bar_floor'] = fp_all.index.floor(freq)

    footprint_full = (
        fp_all.groupby(['bar_floor', 'price', 'side'])['size']
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    # Assicura colonne A (ask/buy) e B (bid/sell) esistano
    for col in ['A', 'B']:
        if col not in footprint_full.columns:
            footprint_full[col] = 0

    # Raggruppa per bar_floor → dizionario {ts_bar: [(price, bid_vol, ask_vol), ...]}
    fp_map: dict = {}
    for ts_bar, group in footprint_full.groupby('bar_floor'):
        levels_list = []
        for _, lvl_row in group.iterrows():
            bid_vol = int(lvl_row.get('B', 0))
            ask_vol = int(lvl_row.get('A', 0))
            levels_list.append({
                'price': float(lvl_row['price']),
                'bid_vol': bid_vol,
                'ask_vol': ask_vol,
            })
        # Ordina per prezzo decrescente (come nel frontend)
        levels_list.sort(key=lambda x: -x['price'])
        fp_map[ts_bar] = levels_list

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
        # Attacca footprint completo come attributo extra
        bars[-1]._fp_levels = fp_map.get(ts, [])
    return bars


class DataService:
    """
    Servizio singleton per accesso ai dati storici Databento.

    Carica e indicizza tutti i CSV disponibili in cache_ohlc/.
    Ogni file è nominato YYYYMMDD.csv.
    """

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_OHLC_DIR
        self._date_index: dict[str, Path] = {}
        self._build_index()

    def _build_index(self):
        """Scansiona cache_ohlc/ e costruisce indice date→path."""
        self._date_index = {}
        for f in sorted(self.cache_dir.glob('*.csv')):
            stem = f.stem  # es. "20250102"
            if re.match(r'^\d{8}$', stem):
                date_str = f"{stem[:4]}-{stem[4:6]}-{stem[6:8]}"
                self._date_index[date_str] = f
        print(f"[DataService] Indicizzate {len(self._date_index)} date da {self.cache_dir}")

    def list_available_dates(self) -> list:
        """Restituisce lista ordinata di date disponibili (YYYY-MM-DD)."""
        return sorted(self._date_index.keys())

    def load_date(self, date: str) -> tuple:
        """
        Carica il CSV per la data e restituisce (bars_m1, bars_m5).
        date: stringa 'YYYY-MM-DD'
        """
        if date not in self._date_index:
            raise FileNotFoundError(f"Nessun dato per la data {date}. "
                                    f"Date disponibili: {list(self._date_index.keys())[:5]}...")

        filepath = str(self._date_index[date])
        print(f"[DataService] Caricamento {filepath}...")

        trades = _load_csv_raw(filepath)
        if not trades:
            raise ValueError(f"Nessun trade trovato in {filepath}")

        print(f"[DataService] {len(trades)} trade caricati per {date}")

        bars_m1 = _aggregate_trades_to_bars(trades, freq='1min')
        bars_m5 = _aggregate_trades_to_bars(trades, freq='5min')

        print(f"[DataService] Aggregate: {len(bars_m1)} barre M1, {len(bars_m5)} barre M5")
        return bars_m1, bars_m5

    def get_prev_date(self, date: str) -> str | None:
        """Restituisce la data precedente disponibile."""
        dates = self.list_available_dates()
        idx = dates.index(date) if date in dates else -1
        return dates[idx - 1] if idx > 0 else None
