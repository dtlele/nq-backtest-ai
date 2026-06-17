import json

def get_all_keys():
    keys = set()
    with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl", "r") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                keys.update(data.keys())
            except Exception as e:
                pass
    print("Keys in reasoning_log.jsonl:")
    print(sorted(list(keys)))

    trade_keys = set()
    with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl", "r") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                trade_keys.update(data.keys())
            except Exception as e:
                pass
    print("\nKeys in trades_log.jsonl:")
    print(sorted(list(trade_keys)))

if __name__ == "__main__":
    get_all_keys()
