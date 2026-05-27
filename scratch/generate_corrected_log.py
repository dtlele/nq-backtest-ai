# generate_corrected_log.py
import json, pathlib, re

BASE = pathlib.Path(r"c:/Users/Mauro/Documents/nq-backtest")
reasoning_path = BASE / "agent_memory" / "reasoning_log.jsonl"
human_path = BASE / "agent_memory" / "human_decisions.jsonl"
output_path = BASE / "agent_memory" / "reasoning_log_corrected.jsonl"

# Load human decisions with confirmation true
human_records = []
with open(human_path, encoding="utf-8") as f:
    for line in f:
        if not line.strip(): continue
        obj = json.loads(line)
        decision = obj.get("decision", {})
        # Accept both 'confirm' and 'confirmation'
        if decision.get("confirm") or decision.get("confirmation"):
            human_records.append(decision)

# Index human decisions by date and time if available
# Some decisions include 'entry' and 'direction' fields
human_by_dt = {}
for d in human_records:
    # Attempt to infer date/time from entry if present
    entry = d.get("entry")
    direction = d.get("direction") or d.get("direction", "none")
    # human decisions may not contain explicit timestamp, so we'll fallback to matching by direction and confidence
    # For simplicity, store list
    key = (direction, d.get("confidence"))
    human_by_dt.setdefault(key, []).append(d)

# Read original reasoning log and replace entries where Fabio suggested a direction and Andrea confirmed
out_lines = []
with open(reasoning_path, encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            out_lines.append(line)
            continue
        rec = json.loads(line)
        fabio_dir = rec.get("fabio_direction")
        if fabio_dir and fabio_dir != "none":
            # Check if there is a matching human decision
            candidates = human_by_dt.get((fabio_dir, rec.get("fabio_confidence")))
            if candidates:
                # Use first match to build trade entry
                h = candidates.pop(0)
                # Populate trade fields
                rec["decision"] = "trade"
                rec["trade_direction"] = fabio_dir
                rec["trade_entry"] = h.get("entry")
                rec["trade_stop"] = h.get("stop")
                rec["trade_target"] = h.get("target")
                rec["trade_pnl_usd"] = h.get("pnl_usd", 0)
                rec["trade_pnl_ticks"] = h.get("pnl_ticks", 0)
                rec["trade_exit_reason"] = h.get("reasoning", "")
                rec["no_trade_reason"] = None
        out_lines.append(json.dumps(rec) + "\n")

with open(output_path, "w", encoding="utf-8") as f:
    f.writelines(out_lines)
print(f"Corrected log written to {output_path}")
