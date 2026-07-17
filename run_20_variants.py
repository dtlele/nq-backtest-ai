import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

os.makedirs("strategies/variants20", exist_ok=True)
os.makedirs("agent_memory/variants20_logs", exist_ok=True)

BASE = {
  "strategy_id": "var_x",
  "target_mode": "structural",
  "max_risk_buffer_pct": 0.05,
  "cooldown_minutes": 15,
  "no_trade_conditions": ["bar volume < 3000", "bar time < 09:40 ET", "already in open trade"]
}

BASE_TEMPLATE_NLM = "Date: {date}. Bar at {bar_time_et} ET. Price: {close}.\n\n{amt_narrative}\n\n[DATI TECNICI]\nIVB: {ib_high}-{ib_low} ({ib_range} pts). POC: {poc}, VA: {va_high}-{va_low}. LVNs: {lvn_levels}. Big trades: {wall_trade_count} trades, {wall_total_size} contracts at ~{wall_level}, side: {wall_side}. Vol: {bar_volume}, delta: {bar_delta}, pos: {ib_position}. MS: {market_structure}. Phase: {temporal_phase}. Day: {day_type}.\n\n[DECISIONE]\n"
BASE_TEMPLATE_IMB = "Date: {date}. Bar at {bar_time_et} ET. Price: {close}.\n\n{amt_narrative}\n\n[DATI TECNICI]\nIVB: {ib_high}-{ib_low} ({ib_range} pts). POC: {poc}, VA: {va_high}-{va_low}. LVNs: {lvn_levels}. Big trades: {wall_trade_count} trades, {wall_total_size} contracts at ~{wall_level}, side: {wall_side}. Vol: {bar_volume}, delta: {bar_delta}, pos: {ib_position}. MS: {market_structure}. Phase: {temporal_phase}. Day: {day_type}.\n\n[DECISIONE]\n"

RULES = [
    ("v1_pure_amt", "CRITICAL RULE: Focus ONLY on Auction Destination. If price is breaking VA and delta is supportive, trade toward the next LVN. Ignore micro-structure chop. Speed rule: MAX 2 SENTENCES."),
    ("v2_pure_predatory", "CRITICAL RULE: Hunt trapped traders. If delta > 0 on bearish close or vice-versa, fade it toward the IB. Speed rule: MAX 2 SENTENCES."),
    ("v3_strict_big_trades", "CRITICAL RULE: NEVER enter unless you see a Big Trade wall of >= 1000 contracts behind you. Otherwise skip. Speed rule: MAX 2 SENTENCES."),
    ("v4_hybrid_amt_big_trades", "CRITICAL RULE: Enter only if Auction Destination is clear AND there is a Big Trade wall >= 500 contracts protecting the stop. Speed rule: MAX 2 SENTENCES."),
    ("v5_vwap_pullbacks", "CRITICAL RULE: Only trade pullbacks to VWAP. If price tests VWAP and delta confirms absorption, enter in macro trend direction. Speed rule: MAX 2 SENTENCES."),
    ("v6_ib_breakout_only", "CRITICAL RULE: Only trade IB Breakouts. Ignore all setups inside the IB. If breaking IB, enter aggressively on momentum. Speed rule: MAX 2 SENTENCES."),
    ("v7_poc_magnet", "CRITICAL RULE: If price is inside VA, always trade toward the POC. POC is the magnet. Speed rule: MAX 2 SENTENCES."),
    ("v8_anti_chop", "CRITICAL RULE: If day_type is CHOP/BALANCE, only trade extremes (IBH/IBL reversals). If day_type is TREND, only trade continuations. Speed rule: MAX 2 SENTENCES."),
    ("v9_delta_divergence", "CRITICAL RULE: Only enter on Delta Divergence (e.g., price down, delta highly positive -> go long). Speed rule: MAX 2 SENTENCES."),
    ("v10_momentum_chaser", "CRITICAL RULE: Ignore walls. If MS is BREAKOUT UP and delta > 500, buy market immediately. Speed rule: MAX 2 SENTENCES."),
    ("v11_patient_sniper", "CRITICAL RULE: Wait for 3 confluences: Price at key level + Delta aligned + Big Trades > 800. If any missing, skip. Speed rule: MAX 2 SENTENCES."),
    ("v12_lvn_rejection", "CRITICAL RULE: Focus heavily on LVNs. If price tests an LVN and volume dries up (low bar volume), fade the LVN. Speed rule: MAX 2 SENTENCES."),
    ("v13_volume_profile_edges", "CRITICAL RULE: Trade only at VAH or VAL. Go long on VAL test, go short on VAH test in balance days. Breakout on trend days. Speed rule: MAX 2 SENTENCES."),
    ("v14_early_morning_bias", "CRITICAL RULE: Aggressive before 11:00 ET. After 11:00 ET, be highly selective and require double confirmation. Speed rule: MAX 2 SENTENCES."),
    ("v15_stop_hunt_exploiter", "CRITICAL RULE: Look for obvious stops (just outside IB or VWAP) getting swept. Enter when price sweeps them and reverses. Speed rule: MAX 2 SENTENCES."),
    ("v16_macro_trend_follower", "CRITICAL RULE: Follow the 'Day type so far'. Never trade against it. Use pullbacks to enter. Speed rule: MAX 2 SENTENCES."),
    ("v17_imbalance_rider", "CRITICAL RULE: If in IMBALANCE SESSION, ignore structure and just follow delta. If delta > 0, go long. Speed rule: MAX 2 SENTENCES."),
    ("v18_structural_walls_only", "CRITICAL RULE: Ignore big trades. Only use structural levels (IB, VA, VWAP) as walls. If level holds, enter. Speed rule: MAX 2 SENTENCES."),
    ("v19_max_confidence", "CRITICAL RULE: You must be 90% confident. If there is even one contradictory signal (e.g. body vs delta), skip. Speed rule: MAX 2 SENTENCES."),
    ("v20_fabio_standard", "CRITICAL RULE: Balance AMT and Predatory. Check Auction Destination and look for trapped traders. Speed rule: MAX 2 SENTENCES.")
]

for name, rule in RULES:
    strat = BASE.copy()
    strat["strategy_id"] = name
    strat["fabio_nlm_question_template"] = BASE_TEMPLATE_NLM + rule + " Direction={suggested_direction}. Conf 0-100."
    strat["fabio_imbalance_question_template"] = BASE_TEMPLATE_IMB + rule + " Direction={suggested_direction}. Conf 0-100."
    with open(f"strategies/variants20/{name}.json", "w") as f:
        json.dump(strat, f, indent=2)

def run_variant(name):
    print(f"[{name}] Starting backtest...")
    mem_dir = f"agent_memory/variants20_logs/mem_{name}"
    os.makedirs(mem_dir, exist_ok=True)
    
    # Check if already processed (resumable)
    if os.path.exists(os.path.join(mem_dir, "trades_log.jsonl")) or (os.path.exists(os.path.join(mem_dir, "reasoning_log.jsonl")) and len(open(os.path.join(mem_dir, "reasoning_log.jsonl")).readlines()) > 15):
        print(f"[{name}] Already processed. Skipping to save API calls.")
        dur = 0
    else:
        cmd = [
            "python", "run_backtest.py",
            "--start-date", "20260107",
            "--end-date", "20260108",
            "--strategy", f"variants20/{name}.json"
        ]
        
        env = os.environ.copy()
        env["AGENT_MEMORY_DIR"] = os.path.abspath(mem_dir)
        
        start_t = time.time()
        try:
            subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', timeout=1800)
        except subprocess.TimeoutExpired:
            print(f"[{name}] TIMEOUT after 30 mins")
            
        dur = time.time() - start_t
    
    # Parse trades
    trades_file = os.path.join(mem_dir, "trades_log.jsonl")
    trades = 0
    pnl = 0.0
    if os.path.exists(trades_file):
        with open(trades_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        t = json.loads(line)
                        trades += 1
                        pnl += t.get("pnl", 0)
                    except:
                        pass
                        
    print(f"[{name}] Done in {dur:.1f}s | Trades: {trades} | PnL: {pnl:.2f}")
    return {"name": name, "trades": trades, "pnl": pnl, "dur": dur}

if __name__ == "__main__":
    print("Running 20 variants on Jan 7-8 using max_workers=4...")
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_variant, name) for name, _ in RULES]
        for f in futures:
            try:
                results.append(f.result())
            except Exception as e:
                print("Error:", e)
                
    # Generate report
    results.sort(key=lambda x: x["pnl"], reverse=True)
    report = "# 20 Prompt Variants A/B Test Report\n\n"
    report += "| Variant | Trades | PnL | Avg Time (s) |\n"
    report += "|---------|--------|-----|--------------|\n"
    for r in results:
        report += f"| {r['name']} | {r['trades']} | ${r['pnl']:.2f} | {r['dur']:.1f} |\n"
        
    with open("output/variants20_report.md", "w") as f:
        f.write(report)
    print("\nReport saved to output/variants20_report.md")
