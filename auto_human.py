import time
import json
import re
from pathlib import Path

MAILBOX = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\mailbox")

print("Avvio Auto-Human Proxy V2... (Simulatore Matematico Robusto basato su REGOLE)")

def parse_request(req_file):
    with open(req_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def generate_decision(req_data):
    user_msg = req_data.get("user_msg", "")
    
    if "precision entry knowledge" in user_msg.lower():
        dir_m = re.search(r"Direction:\s*(long|short)", user_msg)
        entry_m = re.search(r"M5 Entry:\s*([\d.]+)", user_msg)
        
        if not dir_m or not entry_m:
            raise ValueError(f"Auto-Human Precision could not find Direction or M5 Entry. Prompt snippet: {user_msg[:200]}")
            
        direction = dir_m.group(1)
        bar_close = float(entry_m.group(1))
        
        if direction == "long":
            stop = bar_close - 40.0
            target = bar_close + 100.0
        else:
            stop = bar_close + 40.0
            target = bar_close - 100.0
            
        return {
            "entry": bar_close,
            "stop": stop,
            "target": target,
            "abort": False,
            "entry_reasoning": "Auto-Human Precision: market order near close.",
            "stop_reasoning": "Auto-Human: tight structural stop.",
            "target_reasoning": "Auto-Human: mechanical target."
        }
        
    elif "andrea knowledge" in user_msg.lower() or "andrea structural" in user_msg.lower() or "ibob" in user_msg.lower():
        return {
            "decision": {
                "decision": "trade",
                "confirmation": True,
                "confidence": 95,
                "setup_type": "auto_setup",
                "reasoning": "Andrea Auto-Human: Confirmed. R:R is mechanically structured."
            }
        }
        
    else:
        # PREDATORY LOGIC PARSING
        price_m = re.search(r"Price:\s*([\d]+(?:\.\d+)?)", user_msg)
        ibh_m = re.search(r"IVB high:\s*([\d]+(?:\.\d+)?)|IB high:\s*([\d]+(?:\.\d+)?)", user_msg)
        ibl_m = re.search(r"IVB low:\s*([\d]+(?:\.\d+)?)|IB low:\s*([\d]+(?:\.\d+)?)", user_msg)
        delta_m = re.search(r"delta:\s*([+-]?\d+)", user_msg)
        vol_m = re.search(r"Bar volume:\s*(\d+)", user_msg)
        
        if not (price_m and ibh_m and ibl_m and delta_m):
            return {"direction": "none", "confidence": 0, "entry": None, "stop": None, "target": None, "setup_type": "none", "reasoning": "Missing critical data for math sim.", "market_narrative_update": ""}
            
        price = float(price_m.group(1))
        ibh = float(ibh_m.group(1) or ibh_m.group(2))
        ibl = float(ibl_m.group(1) or ibl_m.group(2))
        delta = int(delta_m.group(1))
        vol = int(vol_m.group(1)) if vol_m else 0
        
        # 1. Breakout LONG
        if price > ibh and delta > 100 and vol >= 3000:
            return {
                "direction": "long", "confidence": 90,
                "entry": price, "stop": ibh - 15.0, "target": price + 50.0,
                "setup_type": "ivb_breakout",
                "reasoning": "Auto-Math: Solid IB High breakout with positive delta and high volume.",
                "market_narrative_update": "IB Breakout detected."
            }
            
        # 2. Breakout SHORT
        elif price < ibl and delta < -100 and vol >= 3000:
            return {
                "direction": "short", "confidence": 90,
                "entry": price, "stop": ibl + 15.0, "target": price - 50.0,
                "setup_type": "ivb_breakout",
                "reasoning": "Auto-Math: Solid IB Low breakout with negative delta and high volume.",
                "market_narrative_update": "IB Breakdown detected."
            }
            
        # 3. Reversal SHORT (Near IB High but rejecting)
        elif ibh - 25 <= price <= ibh + 5 and delta < -200:
            return {
                "direction": "short", "confidence": 85,
                "entry": price, "stop": ibh + 15.0, "target": price - 60.0,
                "setup_type": "reversal",
                "reasoning": "Auto-Math: Rejected at IB High with strong negative delta (absorption).",
                "market_narrative_update": "Reversal at IB High."
            }
            
        # 4. Reversal LONG (Near IB Low but rejecting)
        elif ibl - 5 <= price <= ibl + 25 and delta > 200:
            return {
                "direction": "long", "confidence": 85,
                "entry": price, "stop": ibl - 15.0, "target": price + 60.0,
                "setup_type": "reversal",
                "reasoning": "Auto-Math: Rejected at IB Low with strong positive delta (absorption).",
                "market_narrative_update": "Reversal at IB Low."
            }
            
        else:
            return {
                "direction": "none", "confidence": 0, "entry": None, "stop": None, "target": None,
                "setup_type": "none", "reasoning": "Auto-Math: No edge detected based on mechanical rules.",
                "market_narrative_update": ""
            }

while True:
    try:
        for req_file in MAILBOX.glob("request_*.json"):
            key = req_file.stem.split("_")[1]
            decision_file = MAILBOX / f"decision_{key}.json"
            
            if not decision_file.exists():
                print(f"[{time.strftime('%H:%M:%S')}] Processing {req_file.name}...")
                req_data = parse_request(req_file)
                decision = generate_decision(req_data)
                
                with open(decision_file, 'w', encoding='utf-8') as f:
                    json.dump(decision, f, indent=2)
                
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.1)
