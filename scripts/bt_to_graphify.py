"""
bt_to_graphify.py  v2
=====================
Legge sequences_narrative.jsonl (output di bt_narrative_bulk.py) e genera
file Markdown per Graphify. Ogni .md contiene la narrative testuale + metadati
strutturati, in modo che Graphify possa costruire edges semantici tra sequenze
che condividono concetti istituzionali (absorption, trapped sellers, ecc.).
"""
import json
from pathlib import Path

BASE        = Path(__file__).parent.parent
NARR_FILE   = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "sequences_narrative.jsonl"
FALLBACK    = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "bt_sequences_2026.json"
MD_OUT_DIR  = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "md_narrative"

PATTERN_LABELS = {
    "accumulation_breakup":    "Accumulation + Breakout Long",
    "distribution_breakdown":  "Distribution + Breakdown Short",
    "trending_up":             "Trend Continuation Long",
    "trending_down":           "Trend Continuation Short",
    "reversal_buy":            "Reversal to Long",
    "reversal_sell":           "Reversal to Short",
    "failed_reversal":         "Failed Reversal / Trap",
    "chop":                    "Chop / No Clear Direction",
    "unknown":                 "Unknown Pattern",
}

def side_label(s: str) -> str:
    return "Buyers (Bids)" if s == "B" else "Sellers (Asks)"

def outcome_str(rec: dict) -> str:
    d = rec["target_price_delta"]
    t = rec.get("target_time_delta_mins", 0)
    if rec["is_profitable_long"]:
        return f"PROFITABLE LONG: +{d:.1f} points in {t:.0f} minutes"
    if rec["is_profitable_short"]:
        return f"PROFITABLE SHORT: {d:.1f} points in {t:.0f} minutes"
    return f"NEUTRAL / CHOP: {d:.1f} points"

def make_markdown(rec: dict) -> str:
    seq_id  = rec["sequence_id"]
    pattern = PATTERN_LABELS.get(rec.get("seq_pattern", "unknown"), "Unknown Pattern")
    sides   = rec.get("seq_sides", "?")
    out     = outcome_str(rec)
    narr    = rec.get("narrative", "")
    contrary_max = rec.get("contrary_max_size", 0)
    contrary_cnt = rec.get("contrary_count", 0)

    md  = f"# Institutional Pattern: {seq_id}\n\n"
    md += f"**Pattern Type**: {pattern}\n"
    md += f"**Node Sequence Sides**: {sides}\n"
    md += f"**Date / Time**: {rec['date']} starting {rec.get('start_time','')}\n"
    md += f"**Contrary Flow**: Max Size={contrary_max}ct, Count={contrary_cnt}\n"
    md += f"**Outcome**: {out}\n\n"
    md += "## Institutional Narrative\n\n"
    md += f"{narr}\n\n"
    md += "## Pattern Classification Tags\n\n"

    # Tags for Graphify to pick up as concept nodes
    if rec["is_profitable_long"]:
        md += "- Tag: profitable_long\n"
    if rec["is_profitable_short"]:
        md += "- Tag: profitable_short\n"
    if "breakup" in rec.get("seq_pattern","") or "trending_up" in rec.get("seq_pattern",""):
        md += "- Tag: bullish_institutional_flow\n"
    if "breakdown" in rec.get("seq_pattern","") or "trending_down" in rec.get("seq_pattern",""):
        md += "- Tag: bearish_institutional_flow\n"
    if "reversal" in rec.get("seq_pattern",""):
        md += "- Tag: reversal_pattern\n"
    if "accumulation" in rec.get("seq_pattern",""):
        md += "- Tag: accumulation\n"
    if "distribution" in rec.get("seq_pattern",""):
        md += "- Tag: distribution\n"
    if "->".join(["B","B","B"]) in sides:
        md += "- Tag: triple_buy_sequence\n"
    if "->".join(["A","A","A"]) in sides:
        md += "- Tag: triple_sell_sequence\n"
        
    # Contrary big trade concept tags
    if contrary_cnt > 0:
        md += "- Tag: contrary_big_trade_detected\n"
    if rec.get("has_contrary_100", contrary_max >= 100):
        md += "- Tag: contrary_big_trade_100\n"
    if rec.get("has_contrary_150", contrary_max >= 150):
        md += "- Tag: contrary_big_trade_150\n"
    if rec.get("has_contrary_250", contrary_max >= 250):
        md += "- Tag: contrary_big_trade_250\n"

    return md

def from_narrative_jsonl():
    """Primary path: read narrative JSONL."""
    records = []
    with open(NARR_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return records

def from_raw_json():
    """Fallback: read bt_sequences.json and generate basic .md without LLM narrative."""
    with open(FALLBACK, encoding="utf-8") as f:
        seqs = json.load(f)
    records = []
    for s in seqs:
        steps = s.get("steps", [])
        sides = "->".join(step.get("dominant_side","?") for step in steps)
        fallback_narr = (
            f"Sequence of {len(steps)} institutional nodes. "
            f"Pattern: {s.get('seq_pattern','unknown')}. "
            f"Node sides: {sides}. "
            f"Volume trend: {s.get('seq_vol_trend','?')}. "
            f"Gap trend between nodes: {s.get('seq_gap_trend','?')}. "
        )
        records.append({
            "sequence_id":         s["sequence_id"],
            "date":                s["date"],
            "start_time":          s.get("start_time",""),
            "seq_pattern":         s.get("seq_pattern","unknown"),
            "seq_sides":           sides,
            "is_profitable_long":  s["is_profitable_long"],
            "is_profitable_short": s["is_profitable_short"],
            "target_price_delta":  s["target_price_delta"],
            "target_time_delta_mins": s.get("target_time_delta_mins"),
            "contrary_max_size":   s.get("contrary_max_size", 0),
            "contrary_count":      s.get("contrary_count", 0),
            "has_contrary_100":    s.get("has_contrary_100", False),
            "has_contrary_150":    s.get("has_contrary_150", False),
            "has_contrary_250":    s.get("has_contrary_250", False),
            "narrative": fallback_narr,
        })
    return records

def main():
    MD_OUT_DIR.mkdir(parents=True, exist_ok=True)

    if NARR_FILE.exists():
        print(f"Reading LLM narratives from {NARR_FILE}")
        records = from_narrative_jsonl()
    else:
        print(f"[WARN] {NARR_FILE} not found. Using raw JSON fallback.")
        records = from_raw_json()

    print(f"Generating {len(records)} Markdown files...")
    for rec in records:
        md  = make_markdown(rec)
        out = MD_OUT_DIR / f"seq_{rec['sequence_id']}.md"
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)

    print(f"Written to {MD_OUT_DIR}")
    print(f"Next step: python -m graphify extract {MD_OUT_DIR} --backend openai --model z-ai/glm-5.2")

if __name__ == "__main__":
    main()
