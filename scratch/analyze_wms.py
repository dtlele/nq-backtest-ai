import json

count = 0
low_wms_trades = 0

with open("agent_memory/reasoning_log.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip(): continue
        data = json.loads(line)
        if data.get("decision") == "trade":
            count += 1
            wms = data.get("wall_max_size", 0)
            conf = data.get("fabio_confidence", 0)
            if wms < 30:
                low_wms_trades += 1
                print(f"Date: {data.get('date')} {data.get('bar_time_utc')} | WMS={wms} | FabioConf={conf} | Setup={data.get('fabio_setup')}")

print(f"Total trades taken: {count}")
print(f"Trades with WMS < 30: {low_wms_trades}")
