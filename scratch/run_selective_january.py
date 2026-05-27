import json
import os
import sys
from pathlib import Path
import pandas as pd
import pytz

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.backtest_runner import run_day, DATA_DIR, run_backtest
from src.data_loader import list_data_files
from src.agent_memory import LOG_FILE, reset_session, log_reasoning, log_trade_result

JAN_LOG_FILE = Path(__file__).parent.parent / "agent_memory" / "reasoning_log_jan2025.jsonl"

def extract_january_decisions():
    """Extract list of dates and ET times where Fabio made a decision in Jan 2025."""
    decisions = []
    if not JAN_LOG_FILE.exists():
        print(f"Error: {JAN_LOG_FILE} not found.")
        return decisions

    with open(JAN_LOG_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # We target only Jan 2025 dates
                date_str = data.get("date") # e.g. "2025-01-02"
                if date_str and date_str.startswith("2025-01"):
                    # We keep candidates that went beyond light skip (confidence > 50 or decision != light_skip)
                    decision = data.get("decision")
                    if decision not in ["light_skip", "prefiltered"] or data.get("fabio_confidence", 0) >= 65:
                        decisions.append({
                            "date": date_str,
                            "time_et": data.get("bar_time_et"),
                            "setup": data.get("fabio_setup"),
                            "direction": data.get("fabio_direction")
                        })
    
    df = pd.DataFrame(decisions)
    if df.empty:
        return df
    
    df_unique = df.drop_duplicates(subset=["date", "time_et"])
    print(f"Found {len(df_unique)} unique trade-decision moments in January 2025.")
    return df_unique

def run_selective_backtest():
    decisions_df = extract_january_decisions()
    if decisions_df.empty:
        print("No decisions to re-run.")
        return

    # Let's map target dates to files in databento directory
    files = list_data_files(DATA_DIR)
    jan_files = []
    for f in files:
        name = Path(f).name
        # databento filename format: glbx-mdp3-20250102.trades.csv
        if "202501" in name:
            jan_files.append(f)
            
    print(f"Matched {len(jan_files)} databento files for January 2025.")

    # We will temporarily patch backtest_runner to ONLY evaluate candidates that match our selective times.
    # To do this cleanly, we can inject a target set into os.environ or directly patch it.
    target_moments = set()
    for _, row in decisions_df.iterrows():
        # standardizing formats: YYYY-MM-DD and HH:MM
        target_moments.add((row["date"], row["time_et"]))
        
    import src.backtest_runner as runner
    original_should_prefilter = runner._should_prefilter

    # Selective filter function
    def selective_prefilter(candidate):
        ctx = candidate.session_ctx
        bar = candidate.bar
        bar_ts = bar.timestamp
        
        ET = pytz.timezone('America/New_York')
        bar_et = bar_ts.astimezone(ET).strftime('%H:%M')
        
        # Format candidate date to match log key
        candidate_date = ctx.date # e.g. "2025-01-02"
        
        # If this moment is NOT in our target list, filter it out immediately to save API calls
        if (candidate_date, bar_et) not in target_moments:
            return "selective_skip_not_a_historical_decision"
            
        # If it is, run original prefilter rules (or bypass if we want to force re-evaluation)
        return original_should_prefilter(candidate)

    # Apply the patch!
    runner._should_prefilter = selective_prefilter
    print("Injected selective pre-filtering patch into backtest_runner.")

    # We want to force writing new logs, so let's set BACKTEST_FORCE to true
    os.environ['BACKTEST_FORCE'] = 'true'

    # Clear current January records from main log files to prevent cluttering or duplication before appending new ones
    print("Clearing historical January logs from reasoning_log.jsonl and trades_log.jsonl...")
    from src.agent_memory import LOG_FILE as am_LOG_FILE, TRADES_FILE as am_TRADES_FILE
    for file_path in [am_LOG_FILE, am_TRADES_FILE]:
        if file_path.exists():
            lines_to_keep = []
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if not data.get("date", "").startswith("2025-01"):
                            lines_to_keep.append(line)
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines_to_keep)

    print("Running selective backtest for January 2025...")
    # Execute backtest on the matched files using the patched runner
    all_trades = []
    prev_day_vp = None
    
    # We run in quiet mode, without dry_run, using the true models. 
    # Andrea consensus is active by default now so both Fabio and Andrea will be re-queried!
    for f in sorted(jan_files):
        abs_p = str(Path(f).absolute())
        print(f"Selective run on: {abs_p}")
        day_trades, today_vp = runner.run_day(f, dry_run=False, quiet=True, prev_day_vp=prev_day_vp)
        all_trades.extend(day_trades)
        if today_vp is not None:
            prev_day_vp = today_vp

    print(f"\nSelective re-run complete. Total trades executed: {len(all_trades)}")

if __name__ == "__main__":
    run_selective_backtest()
