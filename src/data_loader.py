import glob, os
import pandas as pd
from src import Trade

REQUIRED_COLS = {'ts_event', 'action', 'side', 'price', 'size'}

def load_day(filepath: str) -> list:
    """Parse one DataBento *.trades.csv. Returns action='T' rows only."""
    # Validate columns first for a clear error message
    header = pd.read_csv(filepath, nrows=0)
    missing = REQUIRED_COLS - set(header.columns)
    if missing:
        raise ValueError(f"{filepath}: missing columns {missing}")
    df = pd.read_csv(filepath, usecols=list(REQUIRED_COLS))
    df = df[df['action'] == 'T'].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
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
