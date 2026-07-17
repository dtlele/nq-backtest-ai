import json
import os
import shutil
import subprocess
import time

BASE_STRATEGY = {
  "strategy_id": "fabio_trapped_v1",
  "target_mode": "structural",
  "max_risk_buffer_pct": 0.05,
  "cooldown_minutes": 15,
  "no_trade_conditions": []
}

PROMPTS = [
    {
        "name": "v11_trapped_seller_focus",
        "desc": "Focuses on trapped sellers. If big sell trades are absorbed and price goes up, enter long.",
        "template": "CRITICAL RULE: Focus heavily on TRAPPED TRADERS. When Big Trades enter on the Bid (sell side) but price does not break down, it means buyers absorbed them. If the market then moves against those sellers, they are forced to cover, fueling the trend. If you see this absorption of sellers, enter {suggested_direction}. Set direction={suggested_direction} if flow confirms. Confidence 0-100."
    },
    {
        "name": "v12_trapped_buyer_focus",
        "desc": "Focuses on trapped buyers. If big buy trades are absorbed and price goes down, enter short.",
        "template": "CRITICAL RULE: Focus heavily on TRAPPED TRADERS. When Big Trades enter on the Ask (buy side) but price fails to break up, they are absorbed. If price reverses, those buyers are trapped and must sell. If you see this absorption of buyers, enter {suggested_direction}. Set direction={suggested_direction} if flow confirms. Confidence 0-100."
    },
    {
        "name": "v13_absorption_breakout",
        "desc": "Trades breakouts ONLY if preceded by absorption of the opposing side.",
        "template": "CRITICAL RULE: For breakouts, we need to see that the opposing side tried to stop it with Big Trades but failed. If Big Trades entered against the {suggested_direction} trend but got absorbed, the breakout is genuine. Enter {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v14_failed_retest_trap",
        "desc": "Enters retests only when big trades at the retest fail to push price.",
        "template": "CRITICAL RULE: During a pullback to a key level (e.g. IB High), watch the Big Trades. If they hit the Bid aggressively but price bounces, the sellers are trapped and the pullback is over. Enter {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    },
    {
        "name": "v15_momentum_ignition_trap",
        "desc": "Looks for a sequence: Big Trades against trend -> Absorption -> Momentum Ignition in trend direction.",
        "template": "CRITICAL RULE: Identify when the opposing side is so strong they absorb Big Trades and continue their trend. If you see big trades failing to get rewarded and price moving opposite, the trap is sprung. Enter immediately {suggested_direction}. Set direction={suggested_direction}. Confidence 0-100."
    }
]

os.makedirs("strategies/ab_test_v2", exist_ok=True)
os.makedirs("agent_memory/ab_test_v2_logs", exist_ok=True)

for p in PROMPTS:
    strat = BASE_STRATEGY.copy()
    strat["strategy_id"] = p["name"]
    base_template = "Date: {date}. Bar at {bar_time_et} ET.\n\n{amt_narrative}\n\n[DATI TECNICI]\nIVB high: {ib_high}, IVB low: {ib_low}. IVB range: {ib_range} points. Volume Profile POC: {poc}, VA high: {va_high}, VA low: {va_low}. LVNs: {lvn_levels}. Big trades in last {lookback} bars: {wall_trade_count} trades totaling {wall_total_size} contracts at price ~{wall_level}, side: {wall_side}. Largest single trade: {wall_max_size} contracts. Bar volume: {bar_volume}, delta: {bar_delta}, close relative to IVB: {ib_position}. Market Structure State: {market_structure}. Temporal Phase: {temporal_phase}. Day type so far: {day_type}.\n\n[DECISIONE]\n"
    strat["fabio_nlm_question_template"] = base_template + p["template"] + " Provide entry, stop, and target in NQ points."
    strat["fabio_imbalance_question_template"] = base_template + p["template"] + " Provide entry, stop, and target in NQ points."
    
    with open(f"strategies/ab_test_v2/{p['name']}.json", "w") as f:
        json.dump(strat, f, indent=2)

def run_backtest(prompt_info):
    name = prompt_info["name"]
    print(f"Starting V2 backtest for {name}...")
    
    cmd = [
        "python", "run_backtest.py",
        "--start-date", "20260107",
        "--end-date", "20260107",
        "--strategy", f"ab_test_v2/{name}.json"
    ]
    
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
    
    try:
        shutil.move("agent_memory/reasoning_log.jsonl", f"agent_memory/ab_test_v2_logs/reasoning_{name}.jsonl")
    except:
        pass
    try:
        shutil.move("agent_memory/trades_log.jsonl", f"agent_memory/ab_test_v2_logs/trades_{name}.jsonl")
    except:
        pass
        
    print(f"Finished {name} in {duration:.1f}s")
    return name

print("Running 5 Trapped Traders backtests sequentially...")
for p in PROMPTS:
    run_backtest(p)

print("\n--- V2 TRAPPED RESULTS ---")
report_lines = ["# Prompt A/B Test V2 (Trapped Traders) Results (Jan 7, 2026)\n"]
for p in PROMPTS:
    name = p["name"]
    trades_file = f"agent_memory/ab_test_v2_logs/trades_{name}.jsonl"
    trades_count = 0
    if os.path.exists(trades_file):
        with open(trades_file, "r") as f:
            for line in f:
                if line.strip():
                    trades_count += 1
    
    res = f"- **{name}**: {trades_count} trades opened. ({p['desc']})"
    print(res)
    report_lines.append(res + "\n")

with open("output/ab_test_v2_report.md", "w") as f:
    f.writelines(report_lines)

print("Report saved to output/ab_test_v2_report.md")
