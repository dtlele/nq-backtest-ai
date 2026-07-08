"""
run_pipeline.py
===============
Esegue l'intero pipeline Big Trade → Clustering → Graphify con un solo comando.

Steps:
  1. extract_bt_sequences.py     → bt_sequences.json (VP real-time + pattern features)
  2. bt_narrative_bulk.py        → sequences_narrative.jsonl (LLM narratives)
  3. cluster_bt_patterns.py      → cluster_report.json (K-Means + Decision Tree)
  4. visualize_clusters.py       → pattern_dashboard.html (heatmap interattiva)
  5. bt_to_graphify.py           → md_narrative/ (Markdown per Graphify)
  6. graphify extract            → graph.json + graph.html
  7. graphify cluster-only       → GRAPH_REPORT.md + community labels

Usage:
    python scripts/run_pipeline.py --start-date 20250101 --end-date 20250228
    python scripts/run_pipeline.py --start-date 20250101 --end-date 20250228 --skip-extract
    python scripts/run_pipeline.py --start-date 20250101 --end-date 20250228 --skip-llm
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"

GRAPHIFY_ENV = {
    **os.environ,
    "OPENAI_API_KEY":  os.environ.get("OPENROUTER_API_KEY", ""),
    "OPENAI_BASE_URL": "https://openrouter.ai/api/v1",
    "OPENAI_MODEL":    "deepseek/deepseek-chat",
}

MD_NARR_DIR = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "md_narrative"

def run(cmd: list, env=None, cwd=None):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or BASE, env=env or os.environ)
    if result.returncode != 0:
        print(f"[ERROR] Step failed with code {result.returncode}")
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="Full Big Trade Pipeline")
    parser.add_argument("--start-date",    required=True)
    parser.add_argument("--end-date",      required=True)
    parser.add_argument("--data-dir",      default=DATA_DIR)
    parser.add_argument("--seq-len",       type=int, default=3)
    parser.add_argument("--llm-batch",     type=int, default=10, help="Sequences per LLM call")
    parser.add_argument("--skip-extract",  action="store_true", help="Skip step 1 (reuse existing bt_sequences.json)")
    parser.add_argument("--skip-llm",      action="store_true", help="Skip step 2 (reuse existing narratives)")
    parser.add_argument("--skip-graphify", action="store_true", help="Skip steps 6-7 (Graphify extract)")
    args = parser.parse_args()

    py = sys.executable

    print("=" * 60)
    print("  BIG TRADE PIPELINE")
    print(f"  Period: {args.start_date} → {args.end_date}")
    print("=" * 60)

    # ── Step 1: Extract sequences ─────────────────────────────────────────────
    if not args.skip_extract:
        print("\n[STEP 1] Extracting enriched sequences (real-time VP)...")
        run([py, "scripts/extract_bt_sequences.py",
             "--start-date", args.start_date,
             "--end-date",   args.end_date,
             "--data-dir",   args.data_dir,
             "--seq-len",    str(args.seq_len)])
    else:
        print("\n[STEP 1] Skipped (--skip-extract)")

    # ── Step 2: LLM Narrative generation ─────────────────────────────────────
    if not args.skip_llm:
        print("\n[STEP 2] Generating LLM narratives (bulk)...")
        run([py, "scripts/bt_narrative_bulk.py",
             "--batch",  str(args.llm_batch),
             "--resume"])
    else:
        print("\n[STEP 2] Skipped (--skip-llm)")

    # ── Step 3: Statistical clustering ───────────────────────────────────────
    print("\n[STEP 3] Running K-Means + Decision Tree clustering...")
    run([py, "scripts/cluster_bt_patterns.py"])

    # ── Step 4: Visual dashboard ──────────────────────────────────────────────
    print("\n[STEP 4] Generating heatmap dashboard...")
    run([py, "scripts/visualize_clusters.py"])

    # ── Step 5: Convert to Graphify Markdown ─────────────────────────────────
    print("\n[STEP 5] Converting narratives to Graphify Markdown...")
    run([py, "scripts/bt_to_graphify.py"])

    # ── Step 6-7: Graphify ────────────────────────────────────────────────────
    if not args.skip_graphify:
        print("\n[STEP 6] Graphify semantic extraction...")
        run([py, "-m", "graphify", "extract", str(MD_NARR_DIR),
             "--backend", "openai", "--model", "deepseek/deepseek-chat",
             "--token-budget", "20000", "--max-concurrency", "1"],
            env=GRAPHIFY_ENV)

        print("\n[STEP 7] Graphify clustering + community naming...")
        run([py, "-m", "graphify", "cluster-only", str(MD_NARR_DIR),
             "--backend", "openai", "--model", "deepseek/deepseek-chat"],
            env=GRAPHIFY_ENV)
    else:
        print("\n[STEP 6-7] Skipped (--skip-graphify)")

    # ── Done ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    dash = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "pattern_dashboard.html"
    graph = MD_NARR_DIR / "graphify-out" / "graph.html"
    print(f"  Dashboard:  {dash}")
    print(f"  Graph HTML: {graph}")
    print("=" * 60)

if __name__ == "__main__":
    main()
