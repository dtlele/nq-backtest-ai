"""
bt_narrative_bulk.py
====================
Reads bt_sequences.json and generates a textual narrative for each sequence
using a cheap LLM (DeepSeek via OpenRouter). Output: sequences_narrative.jsonl

Each narrative is a 3-sentence institutional story that Graphify can
semantically cluster to find meaningful pattern communities.

Usage:
    python scripts/bt_narrative_bulk.py [--max N] [--resume]

Options:
    --max N    Only process first N sequences (for testing)
    --resume   Skip sequences already present in output file
    --batch N  Number of sequences to send per LLM call (default: 10)
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE     = Path(__file__).parent.parent
SEQ_FILE = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "bt_sequences.json"
OUT_FILE = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "sequences_narrative.jsonl"

SYSTEM_PROMPT = """Sei un esperto trader istituzionale specializzato in NQ Futures e order flow analysis.
Ti vengono fornite sequenze di "Big Trade Node" - momenti in cui istituzionali hanno eseguito ordini >= 80 contratti.
Per ogni sequenza, scrivi UNA narrativa in inglese di massimo 4 frasi che descriva:
1. Il contesto di mercato e la posizione rispetto ai livelli chiave
2. Il comportamento dei nodi istituzionali (pattern, accelerazione, divergenze)
3. L'ipotesi sul perché gli istituzionali si sono mossi così
4. L'esito reale (profitable long/short) e cosa ci insegna

Sii preciso, usa terminologia professionale (absorption, trapped buyers/sellers, breakout, accumulation, distribution, POC, VWAP, IB extension).
Rispondi SOLO con un oggetto JSON array con chiave "narratives" contenente un narrative per ogni sequenza fornita.
"""

def build_seq_prompt(seq: dict) -> str:
    pattern   = seq.get("seq_pattern", "unknown")
    sides     = seq.get("seq_sides", "?->?->?")
    gap_trend = seq.get("seq_gap_trend", "stable")
    vol_trend = seq.get("seq_vol_trend", "stable")
    accel     = seq.get("seq_price_accel", 0)
    outcome   = "LONG +{:.1f}pt".format(seq["target_price_delta"]) if seq["is_profitable_long"] \
           else "SHORT {:.1f}pt".format(seq["target_price_delta"]) if seq["is_profitable_short"] \
           else "NEUTRAL"
    time_to   = seq.get("target_time_delta_mins", 0)
    
    contrary_max = seq.get("contrary_max_size", 0)
    contrary_cnt = seq.get("contrary_count", 0)

    steps_txt = []
    for i, step in enumerate(seq.get("steps", [])):
        side_l = "BUY" if step.get("dominant_side") == "B" else "SELL"
        phase  = step.get("session_phase", "?")
        vol    = step.get("volume", 0)
        prox   = step.get("node_proximity", "?")
        vwap   = step.get("price_vs_vwap", "?")
        ib_pos = step.get("ib_position", "?")
        poc    = step.get("price_vs_poc", "?")
        poc_t  = step.get("poc_ticks", 0) or 0
        divg   = "DELTA DIVERGENCE" if step.get("delta_divergence") else ""
        consec = step.get("consecutive_same_side", 1)
        elapsed= step.get("elapsed_mins", 0)
        pchg   = step.get("price_change", 0)
        cvd    = step.get("session_cvd", 0)

        steps_txt.append(
            f"  Node {i+1} [{phase}] {side_l} x{vol}ct | "
            f"{ib_pos} | {poc} POC ({poc_t:+.0f}t) | VWAP:{vwap} | "
            f"elapsed:{elapsed}min prox:{prox} pchange:{pchg:+.2f}pt consec:{consec} "
            f"CVD:{cvd:+d} {divg}"
        )

    return (
        f"SEQ_ID: {seq['sequence_id']} | {seq['date']} {seq['start_time']}-{seq['end_time']}\n"
        f"Pattern: {pattern} | Sides: {sides} | GapTrend:{gap_trend} | VolTrend:{vol_trend} | "
        f"PriceAccel:{accel:+.1f}pt\n"
        f"Contrary Flow: Count={contrary_cnt} | Max Size={contrary_max}ct\n"
        + "\n".join(steps_txt) +
        f"\nOUTCOME: {outcome} in {time_to:.0f} min"
    )

def call_llm(client: OpenAI, batch: list[dict]) -> list[str] | None:
    """Send a batch of sequences and return list of narratives."""
    user_content = "Generate narratives for these " + str(len(batch)) + " sequences:\n\n"
    for i, seq in enumerate(batch):
        user_content += f"--- SEQUENCE {i+1} ---\n{build_seq_prompt(seq)}\n\n"

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "deepseek/deepseek-chat"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.3,
            max_tokens=len(batch) * 300,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        narratives = data.get("narratives", [])
        if len(narratives) != len(batch):
            print(f"  [WARN] Expected {len(batch)} narratives, got {len(narratives)}")
        return narratives
    except Exception as e:
        print(f"  [ERROR] LLM call failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max",    type=int, default=None)
    parser.add_argument("--batch",  type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    # Load sequences
    with open(SEQ_FILE, encoding="utf-8") as f:
        sequences = json.load(f)
    if args.max:
        sequences = sequences[:args.max]

    total = len(sequences)
    print(f"Loaded {total} sequences. Batch size: {args.batch}")

    # Resume: load already-processed IDs
    done_ids = set()
    if args.resume and OUT_FILE.exists():
        with open(OUT_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["sequence_id"])
                except Exception:
                    pass
        print(f"Resuming: {len(done_ids)} already done.")

    to_process = [s for s in sequences if s["sequence_id"] not in done_ids]
    print(f"To process: {len(to_process)} sequences")

    if not to_process:
        print("Nothing to do!")
        return

    # Init OpenAI client pointing to OpenRouter
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    out_f = open(OUT_FILE, "a", encoding="utf-8")
    processed = 0
    errors = 0

    for i in range(0, len(to_process), args.batch):
        batch = to_process[i:i + args.batch]
        print(f"  Batch {i//args.batch + 1}/{(len(to_process)-1)//args.batch + 1} ({len(batch)} seq)...", end=" ", flush=True)

        narratives = call_llm(client, batch)
        if narratives is None:
            errors += len(batch)
            print("FAILED")
            time.sleep(2)
            continue

        for j, seq in enumerate(batch):
            narrative = narratives[j] if j < len(narratives) else "N/A"
            record = {
                "sequence_id":   seq["sequence_id"],
                "date":          seq["date"],
                "start_time":    seq.get("start_time"),
                "seq_pattern":   seq.get("seq_pattern"),
                "seq_sides":     seq.get("seq_sides"),
                "is_profitable_long":  seq["is_profitable_long"],
                "is_profitable_short": seq["is_profitable_short"],
                "target_price_delta":  seq["target_price_delta"],
                "target_time_delta_mins": seq.get("target_time_delta_mins"),
                "contrary_max_size":      seq.get("contrary_max_size", 0),
                "contrary_count":         seq.get("contrary_count", 0),
                "has_contrary_100":       seq.get("has_contrary_100", False),
                "has_contrary_150":       seq.get("has_contrary_150", False),
                "has_contrary_250":       seq.get("has_contrary_250", False),
                "narrative": narrative,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            processed += 1

        out_f.flush()
        print(f"OK (+{len(batch)})")
        time.sleep(0.3)  # gentle rate limit

    out_f.close()
    print(f"\nDone! Processed: {processed} | Errors: {errors}")
    print(f"Output: {OUT_FILE}")

if __name__ == "__main__":
    main()
