import pandas as pd
from pathlib import Path
import pytz

csv_path = Path("c:/Users/Mauro/Documents/nq-backtest/archive_data/glbx-mdp3-20250501.trades.csv")
print("Reading file...")
df = pd.read_csv(csv_path, usecols=['ts_event'], nrows=100)
first_ts = pd.to_datetime(df['ts_event'].iloc[0], utc=True)
print("First timestamp:", first_ts.astimezone(pytz.timezone('America/New_York')))

# Get last row
df_last = pd.read_csv(csv_path, usecols=['ts_event']).tail(1)
last_ts = pd.to_datetime(df_last['ts_event'].iloc[0], utc=True)
print("Last timestamp:", last_ts.astimezone(pytz.timezone('America/New_York')))
