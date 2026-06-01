import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
MEM_FILE = BASE_DIR / "agent_memory" / "quantitative_memory.json"

def _load_db() -> dict:
    if not MEM_FILE.exists():
        return {}
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_db(data: dict):
    MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def build_fingerprint(candidate) -> str:
    """Builds a deterministic string representing the market context."""
    # 1. Day Type
    day_type = candidate.session_ctx.day_type if candidate.session_ctx else "unknown"
    
    # 2. Setup Category
    setup = candidate.setup_category
    
    # 3. Wall Size Bucket
    wms = candidate.wall_max_size
    if wms < 50:
        wall_bucket = "small_wall"
    elif wms < 200:
        wall_bucket = "medium_wall"
    else:
        wall_bucket = "large_wall"
        
    return f"{day_type}|{setup}|{wall_bucket}"

def get_fingerprint_stats(candidate) -> str:
    """Returns a formatted warning string if historical stats exist for this context."""
    fp = build_fingerprint(candidate)
    db = _load_db()
    
    stats = db.get(fp)
    if not stats:
        return ""
        
    seen = stats.get("seen", 0)
    if seen < 3:
        return "" # Not enough statistical significance
        
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    wr = (wins / seen) * 100 if seen > 0 else 0.0
    
    total_pnl = stats.get("total_pnl_usd", 0.0)
    avg_pnl = total_pnl / seen if seen > 0 else 0.0
    
    alert = (
        f"\\n\\n> [!WARNING]\\n"
        f"> **STATISTICAL MEMORY ALERT**\\n"
        f"> You have evaluated this exact market context ({fp}) {seen} times before.\\n"
        f"> Historical Results: {wins} Wins, {losses} Losses (Win Rate: {wr:.1f}%).\\n"
        f"> Total Net P&L: ${total_pnl:.2f} (Average P&L per trade: ${avg_pnl:.2f}).\\n"
        f"> -> USE THIS QUANTITATIVE DATA to calibrate your confidence. A low Win Rate with a strongly positive Average P&L is still a valid setup. Focus on the Average P&L."
    )
    return alert

def log_trade_for_quantitative_memory(closed_trade):
    """Updates the database when a trade closes."""
    fp = getattr(closed_trade, "context_fingerprint", None)
    if not fp and hasattr(closed_trade, "consensus"):
        fp = getattr(closed_trade.consensus, "context_fingerprint", None)
        
    if not fp:
        return
        
    db = _load_db()
    if fp not in db:
        db[fp] = {
            "seen": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl_usd": 0.0,
            "total_ticks": 0.0
        }
        
    stats = db[fp]
    stats["seen"] += 1
    
    if closed_trade.pnl_usd > 0:
        stats["wins"] += 1
    elif closed_trade.pnl_usd <= 0:
        # We count break-even as a loss for the strict win-rate
        stats["losses"] += 1
        
    stats["win_rate"] = (stats["wins"] / stats["seen"]) * 100
    stats["total_pnl_usd"] = stats.get("total_pnl_usd", 0.0) + closed_trade.pnl_usd
    stats["total_ticks"] = stats.get("total_ticks", 0.0) + closed_trade.pnl_ticks
    
    _save_db(db)
