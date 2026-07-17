import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

BASE_STRATEGY = {
  "strategy_id": "fabio_andrea_hybrid_v1",
  "target_mode": "structural",
  "max_risk_buffer_pct": 0.05,
  "cooldown_minutes": 15,
  "no_trade_conditions": []
}

PROMPTS = [
    {
        "name": "v1_aggressive_breakout",
        "desc": "Aggressive on structural breakouts. If breakout confirmed, enter immediately.",
        "template": "CRITICAL RULE: If Market Structure State is 'BREAKOUT UP CONFIRMED', DO NOT WAIT FOR PULLBACK, ENTER IMMEDIATELY if delta is positive. You are looking for TREND CONTINUATION setups. The bias direction is {suggested_direction}. Are there institutional Big Trades or absorption clusters? Actually, for breakouts, ignore big trades and enter on momentum. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v2_lack_of_participation_retest",
        "desc": "Focuses on lack of participation during retests of IB high/low.",
        "template": "CRITICAL RULE: We are looking for LACK OF PARTICIPATION. If the setup is 'level_retest' and delta is very low or contradictory to the move, it means absorption. ENTER in the direction of the macro trend (away from the level). The bias direction is {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v3_strict_absorption",
        "desc": "Strictly requires absorption walls for entry.",
        "template": "CRITICAL RULE: Only enter if you see a DEFENSE or TRAPPED wall. If price tests a wall and delta shows absorption, enter {suggested_direction}. Ignore breakouts without volume. Set direction={suggested_direction} if flow confirms. Confidence 0-100."
    },
    {
        "name": "v4_pullback_momentum",
        "desc": "Buys pullbacks into the VWAP or IBH if momentum is intact.",
        "template": "CRITICAL RULE: If Market Structure State is 'PULLBACK' into a key level (IBH, VWAP) and delta is not overwhelmingly against the macro trend, buy the dip immediately. The bias direction is {suggested_direction}. Set direction={suggested_direction} if the order flow confirms the trend. Confidence 0-100."
    },
    {
        "name": "v5_pure_price_action",
        "desc": "Ignores volume and big trades, trades pure price action breakouts and pullbacks.",
        "template": "CRITICAL RULE: Ignore delta and big trades. If price closes outside IB, or if price cleanly retests IBH and rejects, enter {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v6_contrarian_trap",
        "desc": "Looks for trapped traders to fade them.",
        "template": "CRITICAL RULE: Look for TRAPPED traders. If price spikes and immediately reverses with opposite delta, fade the move. The bias direction is {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v7_hybrid_balanced",
        "desc": "Balanced approach combining structure and big trades.",
        "template": "CRITICAL RULE: If 'PULLBACK', look for absorption. If 'BREAKOUT', ensure big trades confirm. DO NOT look for reversals inside the IB. You are looking for TREND CONTINUATION setups. The bias direction is {suggested_direction}. Are there institutional Big Trades or absorption clusters that confirm? Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v8_hyper_aggressive_all",
        "desc": "Hyper aggressive, enters on almost any setup.",
        "template": "CRITICAL RULE: ENTER ALMOST ALWAYS if the setup is not 'none'. Just find any minor reason in delta or volume to enter {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v9_patient_confirmation",
        "desc": "Extremely patient, requires 3+ confluences.",
        "template": "CRITICAL RULE: REQUIRE 3 CONFLUENCES. 1) Price at key level, 2) Big trades confirming, 3) Delta aligned. Otherwise NO TRADE. The bias direction is {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v10_time_based_bias",
        "desc": "Biased towards time of day (aggressively trades 10:00-11:30).",
        "template": "CRITICAL RULE: If time is between 10:00 and 11:30 ET, be highly aggressive. The bias direction is {suggested_direction}. If flow slightly supports trend, enter. Set direction={suggested_direction}. Confidence 0-100."
    }
]

os.makedirs("strategies/ab_test", exist_ok=True)
os.makedirs("agent_memory/ab_test_logs", exist_ok=True)

# Generate JSON files
for p in PROMPTS:
    strat = BASE_STRATEGY.copy()
    strat["strategy_id"] = p["name"]
    base_template = "Date: {date}. Bar at {bar_time_et} ET.\n\n{amt_narrative}\n\n[DATI TECNICI]\nIVB high: {ib_high}, IVB low: {ib_low}. IVB range: {ib_range} points. Volume Profile POC: {poc}, VA high: {va_high}, VA low: {va_low}. LVNs: {lvn_levels}. Big trades in last {lookback} bars: {wall_trade_count} trades totaling {wall_total_size} contracts at price ~{wall_level}, side: {wall_side}. Largest single trade: {wall_max_size} contracts. Bar volume: {bar_volume}, delta: {bar_delta}, close relative to IVB: {ib_position}. Market Structure State: {market_structure}. Temporal Phase: {temporal_phase}. Day type so far: {day_type}.\n\n[DECISIONE]\n"
    strat["fabio_nlm_question_template"] = base_template + p["template"] + " Provide entry, stop, and target in NQ points."
    strat["fabio_imbalance_question_template"] = base_template + p["template"] + " Provide entry, stop, and target in NQ points."
    
    with open(f"strategies/ab_test/{p['name']}.json", "w") as f:
        json.dump(strat, f, indent=2)

def run_backtest(prompt_info):
    name = prompt_info["name"]
    print(f"Starting backtest for {name}...")
    
    # Run the backtest (will write to agent_memory/reasoning_log.jsonl and trades_log.jsonl)
    # We use a completely isolated data-dir or we just run them sequentially to avoid file collision?
    # To run in parallel, we MUST isolate the agent_memory. But agent_memory paths are hardcoded in agent_memory.py.
    # To avoid changing agent_memory.py, we will just run them sequentially. It takes ~20s per run now because we filter noise!
    
    cmd = [
        "python", "run_backtest.py",
        "--start-date", "20260107",
        "--end-date", "20260107",
        "--strategy", f"ab_test/{name}.json"
    ]
    
    # Delete old logs so we don't inherit them
    try:
        os.remove("agent_memory/reasoning_log.jsonl")
    except OSError:
        pass
    try:
        os.remove("agent_memory/trades_log.jsonl")
    except OSError:
        pass
        
    start_time = time.time()
    subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    # Move logs
    try:
        shutil.move("agent_memory/reasoning_log.jsonl", f"agent_memory/ab_test_logs/reasoning_{name}.jsonl")
    except:
        pass
    try:
        shutil.move("agent_memory/trades_log.jsonl", f"agent_memory/ab_test_logs/trades_{name}.jsonl")
    except:
        pass
        
    print(f"Finished {name} in {duration:.1f}s")
    return name

print("Running 10 backtests sequentially to avoid file collision...")
# Sequential execution to prevent agent_memory conflicts
for p in PROMPTS:
    run_backtest(p)

# Analyze results
print("\n--- RESULTS ---")
report_lines = ["# Prompt A/B Test Results (Jan 7, 2026)\n"]
for p in PROMPTS:
    name = p["name"]
    trades_file = f"agent_memory/ab_test_logs/trades_{name}.jsonl"
    trades_count = 0
    if os.path.exists(trades_file):
        with open(trades_file, "r") as f:
            for line in f:
                if line.strip():
                    trades_count += 1
    
    res = f"- **{name}**: {trades_count} trades opened. ({p['desc']})"
    print(res)
    report_lines.append(res + "\n")

with open("output/ab_test_report.md", "w") as f:
    f.writelines(report_lines)

print("Report saved to output/ab_test_report.md")
