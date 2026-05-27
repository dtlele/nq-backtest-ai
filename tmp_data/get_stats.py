import json
import pandas as pd
data = []
with open('c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        data.append(json.loads(line))
if len(data) > 0:
    df = pd.DataFrame(data)
    print(f"Total Trades: {len(df)}")
    print(f"Total PnL (USD): {df['pnl_usd'].sum()}")
    print(f"Win Rate: {len(df[df['pnl_usd'] > 0])/len(df):.2%}")
    print(f"Start Date: {df['date'].min()}")
    print(f"End Date: {df['date'].max()}")
else:
    print("No data")
