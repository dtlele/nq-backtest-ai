import glob, os
import pandas as pd
from datetime import timezone
from src import Trade

def load_day(filepath: str) -> list:
    """Parse one DataBento *.trades.csv. Returns action='T' rows only."""
    df = pd.read_csv(filepath,
                     usecols=['ts_event', 'action', 'side', 'price', 'size'])
    df = df[df['action'] == 'T'].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
    return [
        Trade(
            ts_event=row.ts_event.to_pydatetime().replace(tzinfo=timezone.utc),
            side=row.side,
            price=float(row.price),
            size=int(row.size),
        )
        for row in df.itertuples(index=False)
    ]

def list_data_files(directory: str) -> list:
    """Return sorted list of *.trades.csv paths."""
    return sorted(glob.glob(os.path.join(directory, '*.trades.csv')))
