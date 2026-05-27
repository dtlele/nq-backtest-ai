import glob, os, warnings
import pandas as pd
from src import Trade

REQUIRED_COLS = {'ts_event', 'action', 'side', 'price', 'size'}

def load_day(filepath: str) -> list:
    """Parse one DataBento *.trades.csv. Returns action='T' rows for front-month NQ only.

    DataBento files may contain multiple symbols: front-month futures (e.g. NQM5),
    back-month futures (NQU5, NQZ5), and calendar spreads (NQM5-NQU5).
    Spread prices (~183 pts) would corrupt bar OHLC — filter to outright futures only,
    then pick the highest-volume symbol (front month).
    """
    # Validate columns first for a clear error message
    header = pd.read_csv(filepath, nrows=0)
    all_cols = set(header.columns)
    missing = REQUIRED_COLS - all_cols
    if missing:
        raise ValueError(f"{filepath}: missing columns {missing}")

    read_cols = list(REQUIRED_COLS | ({'symbol'} if 'symbol' in all_cols else set()))
    df = pd.read_csv(filepath, usecols=read_cols)
    df = df[df['action'] == 'T'].copy()

    # Filter to outright futures (exclude calendar spreads whose symbol contains '-')
    if 'symbol' in df.columns:
        outright = df[~df['symbol'].str.contains('-', na=False)]
        if not outright.empty:
            # Pick the symbol with the highest trade count (front month)
            front_month = outright['symbol'].value_counts().idxmax()
            df = outright[outright['symbol'] == front_month].copy()

    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
    with warnings.catch_warnings():
        # DataBento timestamps have nanosecond precision; Python datetime truncates to microseconds
        warnings.filterwarnings('ignore', message='Discarding nonzero nanoseconds')
        return [
            Trade(
                ts_event=row.ts_event.to_pydatetime(),
                side=row.side,
                price=float(row.price),
                size=int(row.size),
            )
            for row in df.itertuples(index=False)
        ]

def list_data_files(directory: str) -> list:
    """Return sorted list of *.trades.csv paths."""
    return sorted(glob.glob(os.path.join(directory, '*.trades.csv')))
