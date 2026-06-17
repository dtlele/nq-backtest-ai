import json

def inspect():
    with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl", "r") as f:
        for i in range(3):
            line = f.readline()
            if line:
                print(f"Trade log sample {i}:")
                print(json.dumps(json.loads(line), indent=2))
                
    with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl", "r") as f:
        for i in range(3):
            line = f.readline()
            if line:
                print(f"Reasoning log sample {i}:")
                print(json.dumps(json.loads(line), indent=2))

if __name__ == "__main__":
    inspect()
