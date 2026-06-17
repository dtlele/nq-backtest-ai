import json
from pathlib import Path
from datetime import timezone
import pytz
from src import CandidateBar, FabioSignal, Bar, NQ_TICK_SIZE

ET = pytz.timezone('America/New_York')
STRATEGY_FILE = Path(__file__).parent.parent / 'strategies' / 'fabio_andrea_hybrid.json'

def set_active_strategy(strategy_name: str) -> None:
    global STRATEGY_FILE
    # If strategy_name is a full file name, use it, otherwise format as strategies/name.json
    if not strategy_name.endswith('.json'):
        strategy_name = f"{strategy_name}.json"
    STRATEGY_FILE = Path(__file__).parent.parent / 'strategies' / strategy_name
    print(f"  [STRATEGY] Active strategy file set to: {STRATEGY_FILE}")

def get_strategy_config() -> dict:
    return _load_templates()

def _load_templates() -> dict:
    try:
        with open(STRATEGY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Strategy file not found: {STRATEGY_FILE}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Strategy file is invalid JSON ({STRATEGY_FILE}): {e}") from e

def _format_m5_sequence(bars: list) -> str:
    """Format a list of M5 bars as a readable sequence for agent context."""
    lines = ["M5 bar sequence (oldest -> newest):"]
    for b in bars:
        t_et = b.timestamp.astimezone(ET)
        big_info = ""
        if b.big_trades:
            total_big = sum(t.size for t in b.big_trades)
            sides = {'A': 0, 'B': 0}
            for t in b.big_trades:
                sides[t.side] = sides.get(t.side, 0) + t.size
            big_info = f" | BIG={total_big} (buy={sides.get('A',0)} sell={sides.get('B',0)})"
        marker = " <-- CANDIDATE" if b is bars[-1] else ""
        lines.append(
            f"  {t_et.strftime('%H:%M')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume} "
            f"delta={b.delta:+d}{big_info}{marker}"
        )
    return "\n".join(lines)

def _format_m1_sequence(bars: list[Bar], hide_historical_delta: bool = False) -> str:
    """Format M1 bars with aggregated big trade detail for token efficiency."""
    lines = ["M1 bar sequence (oldest -> newest):"]
    for i, b in enumerate(bars):
        t_et = b.timestamp.astimezone(ET)
        big_info = ""
        if b.big_trades:
            buy_trades = [t for t in b.big_trades if t.side == 'A']
            sell_trades = [t for t in b.big_trades if t.side == 'B']
            
            zones = []
            if buy_trades:
                min_p = min(t.price for t in buy_trades)
                max_p = max(t.price for t in buy_trades)
                vol = sum(t.size for t in buy_trades)
                zones.append(f"{vol} BUY (Zone {min_p:.2f}-{max_p:.2f})" if min_p != max_p else f"{vol} BUY @ {min_p:.2f}")
            if sell_trades:
                min_p = min(t.price for t in sell_trades)
                max_p = max(t.price for t in sell_trades)
                vol = sum(t.size for t in sell_trades)
                zones.append(f"{vol} SELL (Zone {min_p:.2f}-{max_p:.2f})" if min_p != max_p else f"{vol} SELL @ {min_p:.2f}")
                
            big_info = f" | BIG_TRADES=[{', '.join(zones)}]"
            
        is_last = (i == len(bars) - 1)
        delta_str = f" delta={b.delta:+d}" if (is_last or not hide_historical_delta) else ""
        
        # Calculate local RVol against previous bars in the sequence to normalize volume across epochs
        prev_vols = [x.volume for x in bars[:i] if x.volume > 0]
        rvol_str = ""
        if prev_vols:
            avg_prev = sum(prev_vols) / len(prev_vols)
            rvol = b.volume / avg_prev
            rvol_str = f" rvol={rvol:.2f}x"
        else:
            rvol_str = " rvol=1.00x"
            
        lines.append(
            f"  {t_et.strftime('%H:%M:%S')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume}{rvol_str}"
            f"{delta_str}{big_info}"
        )
        if is_last:
            lines.append(f"\n---> CURRENT CANDIDATE BAR DELTA: {b.delta:+d} <---")
            
    return "\n".join(lines)

def build_fabio_question(candidate: CandidateBar, session_context: list = None, m1_bars: list[Bar] = None, market_narrative: str = "", bars_since_last: list[Bar] = None) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    bar_et_time = t_et
    ib_end_time = bar_et_time.replace(hour=10, minute=30, second=0, microsecond=0)
    
    if bar_et_time >= ib_end_time:
        ib_pos = 'above IVB' if bar.close > ctx.ib_high else \
                 'below IVB' if bar.close < ctx.ib_low  else 'inside IVB'
    else:
        if ctx.vp:
            ib_pos = 'above Overnight VA' if bar.close > ctx.vp.va_high else \
                     'below Overnight VA' if bar.close < ctx.vp.va_low else 'inside Overnight VA'
        else:
            ib_pos = 'Price Discovery (First Hour)'
    suggested = 'long' if candidate.wall_side == 'ask' else 'short'
    # FIX: When price is OUTSIDE the IB, suggested_direction must follow the IB breakout trend,
    # NOT the wall_side of the single bar (which can point in any direction).
    # Exception: 'reversal' setups are deliberately counter-trend — keep wall_side for those.
    if candidate.setup_category != 'reversal':
        if 'above' in ib_pos:
            suggested = 'long'   # above IB → uptrend → long continuation bias
        elif 'below' in ib_pos:
            suggested = 'short'  # below IB → downtrend → short continuation bias
        # inside IB: wall_side is the correct hint (no IB directional bias)
    m5_sequence = _format_m5_sequence(candidate.recent_bars) if candidate.recent_bars else ""
    m1_sequence = _format_m1_sequence(m1_bars) if m1_bars else ""
    
    # Select appropriate template: imbalance_hunting gets a trend-continuation framing
    if candidate.setup_category == 'imbalance_hunting' and 'fabio_imbalance_question_template' in templates:
        tpl = templates['fabio_imbalance_question_template']
    else:
        tpl = templates['fabio_nlm_question_template']
    question = tpl.format(
        date            = bar.timestamp.strftime('%Y-%m-%d'),
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        ib_range        = ctx.ib_range,
        poc             = ctx.vp.poc if ctx.vp else 'N/A',
        va_high         = ctx.vp.va_high if ctx.vp else 'N/A',
        va_low          = ctx.vp.va_low if ctx.vp else 'N/A',
        lvn_levels      = str(ctx.vp.lvn_levels if ctx.vp else []),
        lookback        = 3,
        wall_trade_count= candidate.wall_trade_count,
        wall_total_size = sum(t.size for t in bar.big_trades),
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_max_size   = candidate.wall_max_size,
        bar_volume      = bar.volume,
        bar_delta       = bar.delta,
        ib_position     = ib_pos,
        day_type        = "developing_trend" if ctx.day_type == "unknown" else ctx.day_type,
        market_state    = getattr(candidate, 'market_state', 'unknown'),
        auction_type    = getattr(candidate, 'auction_type', 'unknown'),
        suggested_direction = suggested,
    )
    # Add previous day VP context for reference levels
    if ctx.prev_day_vp:
        pvp = ctx.prev_day_vp
        question += (
            f"\n\nPrevious day VP: POC={pvp.poc:.2f} VAH={pvp.va_high:.2f} "
            f"VAL={pvp.va_low:.2f} HVN={pvp.hvn_levels} LVN={pvp.lvn_levels}"
        )
    if ctx.vp:
        question += (
            f"\n\nOvernight VP: POC={ctx.vp.poc:.2f} VAH={ctx.vp.va_high:.2f} "
            f"VAL={ctx.vp.va_low:.2f} HVN={ctx.vp.hvn_levels} LVN={ctx.vp.lvn_levels}"
        )
        
    # Inject Inter-Day Memory (Telegram Analysis and End-of-Day Narrative)
    if ctx.historical_days:
        question += "\n\n### MULTI-DAY MEMORY & LESSONS LEARNED ###\n"
        question += "You must adapt your trading logic based on the feedback from the previous days below.\n\n"
        for i, h_day in enumerate(ctx.historical_days):
            day_label = f"T-{i+1} ({h_day.date})"
            question += f"--- {day_label} ---\n"
            if h_day.market_narrative:
                question += f"Your Final Narrative on {day_label}:\n{h_day.market_narrative}\n\n"
            if h_day.telegram_analysis:
                question += f"End of Day Performance Review on {day_label}:\n{h_day.telegram_analysis}\n\n"
        
    # Inject VWAP Intraday Status
    price = bar.close
    if getattr(candidate, 'vwap', 0.0) > 0:
        vwap = candidate.vwap
        sd = getattr(candidate, 'vwap_std_dev', 0.0)
        question += f"\n\n## INTRADAY VWAP STATUS\n"
        question += f"VWAP: {vwap:.2f}\n"
        if sd > 0:
            sd_dist = (price - vwap) / sd
            question += f"Current Price is {sd_dist:+.2f} SD away from VWAP.\n"
        
        question += "You have access to the raw distance from VWAP in standard deviations. Evaluate structurally if there is overextension or room for continuation/pullback based on order flow and trapped traders rather than rigid mathematical limits.\n"
            
    # Inject Midday Penalty (12:00 - 14:30 ET)
    if 12 <= t_et.hour < 14 or (t_et.hour == 14 and t_et.minute < 30):
        question += f"\n\n🚨 [WARNING - MIDDAY KILL-ZONE] The time is {t_et.strftime('%H:%M')} ET (Lunch Session). Volume and trend continuation are statistically terrible here. REJECT TRADES unless there is an extreme institutional anomaly (NAV spike).\n"
        
    # Inject Normalized Abnormal Volume (NAV)
    if getattr(candidate, 'nav_alert', False):
        question += f"\n\n🚨🚨 [ABNORMAL VOLUME SPIKE DETECTED] 🚨🚨\n"
        question += "Current volume is > 2.33 Standard Deviations above the session's moving average! According to Bajo (2010), this signals undisclosed institutional information. Expect STRONG PRICE CONTINUATION in the direction of the spike.\n"

    # Inject Stop-Hunt Re-entry context
    if getattr(candidate, 'active_stop_hunt', False):
        sd = getattr(candidate, 'stop_hunt_direction', '')
        question += f"\n\n🚨🚨 [STOP-HUNT RE-ENTRY DETECTED] 🚨🚨\n"
        question += f"WARNING: We just got stopped out on a {sd.upper()} trade within the last 3 minutes! "
        question += "Look VERY CAREFULLY at the M1 footprint in this candle and the ones immediately preceding it. "
        question += "Is this a V-Shape liquidity sweep? Did institutions hunt our stop to fill their massive orders? "
        question += f"If you see strong absorption/reversal volume pointing back {sd.upper()}, this is a prime RE-ENTRY setup. Do not be afraid to re-enter if the footprint supports it.\n"

    # Multi-Day Structural Context
    if len(ctx.historical_days) >= 2:
        t1 = ctx.historical_days[0]
        t2 = ctx.historical_days[1]
        
        question += "\n\n## MULTI-DAY STRUCTURAL CONTEXT\n"
        question += f"T-2 (Day Before Yesterday): POC={t2.vp.poc:.2f}, Close={t2.close_price:.2f}\n"
        question += f"T-1 (Yesterday): POC={t1.vp.poc:.2f}, Close={t1.close_price:.2f}\n"
        question += f"T-0 (Today Live): POC={ctx.vp.poc:.2f} (developing)\n"
        
        if t1.vp.poc < t2.vp.poc and t1.close_price < t2.vp.poc:
            status = "[STRONG DOWNTREND MULTI-DAY] T-1 printed a lower POC and closed below T-2 POC. Sellers have Value Acceptance. Favour SHORT setups."
        elif t1.vp.poc > t2.vp.poc and t1.close_price > t2.vp.poc:
            status = "[STRONG UPTREND MULTI-DAY] T-1 printed a higher POC and closed above T-2 POC. Buyers have Value Acceptance. Favour LONG setups."
        else:
            status = "[MIXED / BALANCE MULTI-DAY] T-1 did not structurally break T-2 (e.g., lower POC but closed higher, or inside day). Market is in equilibrium or squeezing."
            
        question += f"Structural Status: {status}\n"
    
    if m1_sequence:
        # Calculate institutional stats for the M1 window
        all_bigs = [t for b in m1_bars for t in b.big_trades]
        buy_bigs = sum(t.size for t in all_bigs if t.side == 'A')
        sell_bigs = sum(t.size for t in all_bigs if t.side == 'B')
        
        question += f"\n\n## Institutional M1 Footprint (Real-time Flow)\n"
        question += f"Total big trades in window: {len(all_bigs)} ({buy_bigs} buy / {sell_bigs} sell contracts)\n"
        question += m1_sequence

    if m5_sequence:
        question += f"\n\n{m5_sequence}"
    # Inject Today's Session Structural Memory (Chronological History)
    from src.session_context import get_session_memory_up_to
    struc_mem = get_session_memory_up_to(ctx, bar.timestamp)
    if struc_mem:
        question += "\n\n## TODAY'S SESSION STRUCTURAL MEMORY (CHRONOLOGICAL HISTORY)\n"
        question += "You must check how levels reacted earlier today to avoid traps (e.g. do not short a level that was strongly rejected twice already):\n"
        question += "\n".join(f"- {line}" for line in struc_mem)

    if session_context:
        question += "\n\n## Session Context (your prior analyses today)\n"
        question += "\n".join(session_context)
        
    if market_narrative:
        question += f"\n\n## Current Market Narrative (Your continuous story of the day)\n{market_narrative}\n"
        
    if bars_since_last:
        question += f"\n\n## What happened since your last evaluation:\n"
        question += _format_m5_sequence(bars_since_last)
        
    # Inject Human Feedback (all setups, since Fabio determines the setup)
    from src.memory.feedback_injector import get_relevant_feedback
    from src.memory.quantitative_memory import build_fingerprint, get_fingerprint_stats
    
    candidate.context_fingerprint = build_fingerprint(candidate)
    stats_alert = get_fingerprint_stats(candidate)
    if stats_alert:
        question += stats_alert
        
    feedback = get_relevant_feedback(None)
    if feedback:
        question += feedback
        
    # Inject Masterclass Metrics
    question += f"\n\n## MASTERCLASS CANDLE METRICS\n"
    question += f"Delta Divergence: {getattr(candidate, 'delta_divergence', False)}\n"
    question += f"Effort vs No Result: {getattr(candidate, 'effort_no_result', False)}\n"
    question += f"Rejection Wick Ratios: Top Wick={getattr(candidate, 'top_wick_ratio', 0.0):.2%} | Bottom Wick={getattr(candidate, 'bottom_wick_ratio', 0.0):.2%}\n"
    question += f"Close Percentile of Range: {getattr(candidate, 'close_percentile', 0.5):.2%} (100% = closed at absolute high, 0% = closed at absolute low)\n"
    question += "Interpret wicks > 40% OR Close Percentile > 75% (for long reversals off lows) / < 25% (for short reversals off highs) as a strong sign of rejection/liquidity sweeps. Effort vs No Result = passive institutional defense/absorption.\n"
        
    return question

def build_andrea_question(candidate: CandidateBar,
                           fabio_signal: FabioSignal,
                           m1_bars: list[Bar] = None) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    m5_sequence = _format_m5_sequence(candidate.recent_bars) if candidate.recent_bars else ""
    m1_sequence = _format_m1_sequence(m1_bars, hide_historical_delta=True) if m1_bars else ""
    
    # Select appropriate template for Andrea
    is_imbalance = False
    if ctx.ib_complete and ctx.ib_high and ctx.ib_low:
        is_imbalance = (bar.close > ctx.ib_high or bar.close < ctx.ib_low)
        
    use_imbalance_tpl = (
        fabio_signal.setup_type in ['imbalance_hunting', 'ivb_model_1_continuation']
        or is_imbalance
    )
    
    if use_imbalance_tpl and 'andrea_imbalance_question_template' in templates:
        tpl = templates['andrea_imbalance_question_template']
    else:
        tpl = templates['andrea_nlm_question_template']
        
    question = tpl.format(
        date            = bar.timestamp.strftime('%Y-%m-%d'),
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        open            = bar.open,
        high            = bar.high,
        low             = bar.low,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        fabio_setup     = fabio_signal.setup_type,
        fabio_direction = fabio_signal.direction,
        fabio_confidence= fabio_signal.confidence,
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_trade_count= candidate.wall_trade_count,
    )
    if ctx.prev_day_vp:
        pvp = ctx.prev_day_vp
        question += (
            f"\n\nPrevious day VP: POC={pvp.poc:.2f} VAH={pvp.va_high:.2f} "
            f"VAL={pvp.va_low:.2f} HVN={pvp.hvn_levels} LVN={pvp.lvn_levels}"
        )
    if ctx.vp:
        question += (
            f"\n\nOvernight VP: POC={ctx.vp.poc:.2f} VAH={ctx.vp.va_high:.2f} "
            f"VAL={ctx.vp.va_low:.2f} HVN={ctx.vp.hvn_levels} LVN={ctx.vp.lvn_levels}"
        )
    
    if m1_sequence:
        # Calculate institutional stats for the M1 window
        all_bigs = [t for b in m1_bars for t in b.big_trades]
        buy_bigs = sum(t.size for t in all_bigs if t.side == 'A')
        sell_bigs = sum(t.size for t in all_bigs if t.side == 'B')
        
        question += f"\n\n## Institutional Activity (M1 Footprint)\n"
        question += f"Total big trades: {len(all_bigs)} ({buy_bigs} buy / {sell_bigs} sell contracts)\n"
        question += m1_sequence

    if m5_sequence:
        question += f"\n\n{m5_sequence}"
        
    # Inject Human Feedback specific to Fabio's setup choice
    from src.memory.feedback_injector import get_relevant_feedback
    from src.memory.quantitative_memory import build_fingerprint, get_fingerprint_stats
    
    candidate.context_fingerprint = build_fingerprint(candidate)
    stats_alert = get_fingerprint_stats(candidate)
    if stats_alert:
        question += stats_alert
        
    feedback = get_relevant_feedback(fabio_signal.setup_type)
    if feedback:
        question += feedback
        
    # Inject Today's Session Structural Memory (Chronological History)
    from src.session_context import get_session_memory_up_to
    struc_mem = get_session_memory_up_to(ctx, bar.timestamp)
    if struc_mem:
        question += "\n\n## TODAY'S SESSION STRUCTURAL MEMORY (CHRONOLOGICAL HISTORY)\n"
        question += "You must check how levels reacted earlier today to avoid traps:\n"
        question += "\n".join(f"- {line}" for line in struc_mem)

    # Inject Masterclass Metrics
    question += f"\n\n## MASTERCLASS CANDLE METRICS\n"
    question += f"Delta Divergence: {getattr(candidate, 'delta_divergence', False)}\n"
    question += f"Effort vs No Result: {getattr(candidate, 'effort_no_result', False)}\n"
    question += f"Rejection Wick Ratios: Top Wick={getattr(candidate, 'top_wick_ratio', 0.0):.2%} | Bottom Wick={getattr(candidate, 'bottom_wick_ratio', 0.0):.2%}\n"
    question += "Interpret wicks > 40% as a strong sign of rejection/liquidity sweeps. Effort vs No Result = passive institutional defense/absorption.\n"
        
    return question
