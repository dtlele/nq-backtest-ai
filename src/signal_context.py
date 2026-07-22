import json
from pathlib import Path
from datetime import timezone
import pytz
from src import CandidateBar, FabioSignal, Bar, NQ_TICK_SIZE, SessionContext

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
            
        trapped_str = analyze_trapped_participants(b)
        trapped_info = f" | {trapped_str}" if trapped_str else ""
        lines.append(
            f"  {t_et.strftime('%H:%M:%S')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume}{rvol_str}"
            f"{delta_str}{big_info}{trapped_info}"
        )
        if is_last:
            lines.append(f"\n---> CURRENT CANDIDATE BAR DELTA: {b.delta:+d} <---")
            
    return "\n".join(lines)

def build_amt_narrative(ctx: SessionContext, candidate: CandidateBar, ignition_info: dict = None, m1_bars: list = None) -> str:
    narrative = []

    # ── DETECT RECENT INSTITUTIONAL ABSORPTION WALLS (M1 Flow) ──
    if m1_bars:
        recent_m1 = m1_bars[-30:]
        bigs = [t for b in recent_m1 for t in b.big_trades]
        if bigs:
            from collections import defaultdict
            levels_group = defaultdict(list)
            for t in bigs:
                rounded_p = round(t.price * 4) / 4.0
                levels_group[rounded_p].append(t)
            
            significant_walls = []
            for lvl, ts in levels_group.items():
                total_size = sum(x.size for x in ts)
                if total_size >= 100:
                    significant_walls.append((lvl, total_size))
            
            if significant_walls:
                narrative.append("\n═══════════════════════════════════════")
                narrative.append("[ACTIVE INSTITUTIONAL ABSORPTION WALLS (Last 30 mins)]")
                significant_walls.sort()
                m1_high = max(b.high for b in recent_m1)
                m1_low = min(b.low for b in recent_m1)
                for lvl, size in significant_walls:
                    is_near_high = abs(lvl - m1_high) <= 5.0
                    is_near_low = abs(lvl - m1_low) <= 5.0
                    
                    wall_type = "Seller Wall (Resistance/Absorption)" if is_near_high else \
                                "Buyer Wall (Support/Absorption)" if is_near_low else "Order Flow Ledge"
                    
                    dist_to_cand = candidate.bar.close - lvl
                    if dist_to_cand < 0:
                        dist_str = f"{abs(dist_to_cand):.2f} points BELOW"
                    else:
                        dist_str = f"{abs(dist_to_cand):.2f} points ABOVE"
                    
                    narrative.append(
                        f"• {wall_type} at {lvl:.2f} | Size: {size} contracts | Price is {dist_str} this wall."
                    )
                narrative.append("═══════════════════════════════════════")

    # 0. IGNITION STATUS — injected first so LLM reads it immediately
    is_big_trade_or_map = str(candidate.setup_category).startswith('liquidity_map_') or str(candidate.setup_category) == 'big_trade_event'
    
    if ignition_info and not is_big_trade_or_map:
        label = ignition_info.get('label', '')
        if label:
            narrative.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            narrative.append("[IGNITION / ACCUMULATION STATUS (Python-computed, NO LLM)]")
            narrative.append(label)
            if ignition_info.get('in_accumulation') and not ignition_info.get('is_ignition'):
                narrative.append(
                    "➔ REGOLA: Sei in MID-ACCUMULATION. NON ENTRARE. "
                    "Aspetta che il prezzo rompa la zona sopra indicata con delta confermato."
                )
            elif ignition_info.get('is_ignition'):
                narrative.append(
                    "➔ REGOLA: Questo è il momento di entrare. "
                    "La rottura è appena avvenuta su questa barra."
                )
            elif 0 <= ignition_info.get('bars_since_ignition', -1) <= 20:
                narrative.append(
                    "➔ REGOLA: Siamo in EARLY EXPANSION. "
                    "Entrata ancora valida se la struttura lo supporta."
                )
            narrative.append("═══════════════════════════════════════")

    # 1. Profile Shape & POC Migration
    if ctx.profile_shape == 'P':
        narrative.append("Profile Shape is 'P' (Short Covering / Value building higher).")
    elif ctx.profile_shape == 'B' or ctx.profile_shape == 'b':
        narrative.append("Profile Shape is 'b' (Long Liquidation / Value building lower).")
    elif ctx.profile_shape == 'D':
        narrative.append("Profile Shape is 'D' (Pure Balance / Ranging).")
        
    if ctx.prev_day_vp and ctx.vp:
        if ctx.vp.poc > ctx.prev_day_vp.poc:
            narrative.append("Value Migration is UP.")
        elif ctx.vp.poc < ctx.prev_day_vp.poc:
            narrative.append("Value Migration is DOWN.")
        else:
            narrative.append("Value is UNCHANGED.")

    # 2. AMT Market State & Phase Definitions (Minimax)
    is_outside_ib = False
    if ctx.ib_complete and ctx.ib_range > 0:
        is_outside_ib = candidate.bar.close > ctx.ib_high or candidate.bar.close < ctx.ib_low
    elif ctx.vp:
        is_outside_ib = candidate.bar.close > ctx.vp.va_high or candidate.bar.close < ctx.vp.va_low

    if is_outside_ib:
        ib_breakouts_count = getattr(ctx, 'ib_breakouts_count', 0)
        ib_first_breakout_dir = getattr(ctx, 'ib_first_breakout_dir', 'none')
        
        narrative.append("\n[CONTESTO MINIMAX AMT]")
        narrative.append("Il mercato è in stato di IMBALANCE (fuori dall'Initial Balance o Overnight VA).")
        
        if ib_breakouts_count == 1:
            narrative.append(f"⭐ PRIMO BREAKOUT ESPANSIVO della sessione! Direzione: {ib_first_breakout_dir.upper()}. "
                           "Questo è il setup A+ — la prima rottura dell'IB è statisticamente la più forte. "
                           "ENTRA sul segnale di Fabio/Andrea SENZA ESITARE se c'è assorbimento e follow-through.")
        elif ib_breakouts_count == 2:
            narrative.append(f"⚠️ SECONDO breakout espansivo della sessione. La prima rottura era {ib_first_breakout_dir.upper()}. "
                           "Rischio di estensione/esaurimento aumentato. Richiedi confluenza più alta prima di entrare.")
        elif ib_breakouts_count >= 3:
            narrative.append(f"🔴 TERZO o successivo breakout espansivo. Alta probabilità di ESAURIMENTO. "
                           "Evita di inseguire. Attendi solo setup di reversal o con micro-accumulo confermato dal footprint.")
        
        narrative.append("In Imbalance, esistono due fasi:")
        narrative.append("1) Fase Espansiva (Initiative): Il mercato stampa nuovi massimi/minimi con aggressività e alta volatilità.")
        narrative.append("2) Fase di Accumulo/Consolidamento (Response): Il prezzo si ferma, ritraccia dai massimi/minimi, i range si comprimono e gli istituzionali assorbono. L'OBIETTIVO È RILEVARE L'ASSORBIMENTO E POSIZIONARSI PER LA SUCCESSIVA ESPANSIONE.")
    else:
        narrative.append("\n[CONTESTO MINIMAX AMT]")
        narrative.append("Il mercato è in stato di BILANCIAMENTO (all'interno dell'IB o VA).")
        narrative.append("Asta a due vie. La priorità è attendere la rottura (Imbalance) o operare mean-reversion agli estremi.")

    # 3. Structural Facts Calculation
    narrative.append("\n[FATTI STRUTTURALI (Calcolati dal sistema)]")
    if hasattr(candidate, 'recent_bars') and candidate.recent_bars:
        recent_bars = candidate.recent_bars
        local_high = max(b.high for b in recent_bars)
        local_low = min(b.low for b in recent_bars)
        dist_high = local_high - candidate.bar.close
        dist_low = candidate.bar.close - local_low
        
        narrative.append(f"- Il prezzo dista {dist_high:.2f} punti dal massimo locale recente ({local_high:.2f}).")
        narrative.append(f"- Il prezzo dista {dist_low:.2f} punti dal minimo locale recente ({local_low:.2f}).")
        
        if len(recent_bars) >= 4:
            # Range compression check
            last_bar = recent_bars[-1]
            prev_bars = recent_bars[-4:-1]
            avg_prev_range = sum((b.high - b.low) for b in prev_bars) / 3.0
            last_range = last_bar.high - last_bar.low
            
            if avg_prev_range > 0:
                compression = (last_range / avg_prev_range) * 100
                if compression < 75:
                    narrative.append(f"- Compressione del Range: Il range dell'ultima barra M5 è sceso al {compression:.0f}% rispetto alla media delle 3 precedenti (Volatilità in contrazione / Possibile Accumulo).")
                elif compression > 150:
                    narrative.append(f"- Espansione del Range: Il range dell'ultima barra M5 è il {compression:.0f}% rispetto alla media delle 3 precedenti (Forte spinta / Momentum).")
                else:
                    narrative.append(f"- Range Stabile: Il range dell'ultima barra M5 è il {compression:.0f}% rispetto alla media recente.")
        
        if hasattr(candidate, 'effort_no_result') and candidate.effort_no_result:
            narrative.append("- SFORZO SENZA RISULTATO: Rilevata possibile divergenza tra lo sforzo volumetrico/delta e il movimento del prezzo (Possibile Assorbimento/Accumulo).")
    else:
        narrative.append("- Dati recenti insufficienti per estrarre fatti strutturali.")

    narrative.append("\n[COMPITO FASE]")
    narrative.append("Basandoti sui Fatti Strutturali e sull'Order Flow, stabilisci se siamo in Fase 'expansive' o 'accumulation'. Se il mercato è in Bilanciamento, usa 'none'.")
    narrative.append("CRITICO: Se il prezzo HA GIA' rotto l'IB (sopra IB High o sotto IB Low) e ora sta pullback SUL livello IB (IB High come supporto per long, IB Low come resistenza per short):")
    narrative.append("  -> Classificare come imbalance_phase='accumulation'. Il ritracciamento è normale assorbimento istituzionale, NON un ritorno al balance.")
    narrative.append("  -> I wick negativi e il delta debole SUL livello IB sono SFORZO SENZA RISULTATO dei venditori retail contro ordini passivi istituzionali: questo è il setup A+ per entrare LONG (o SHORT se sotto IB Low).")
    narrative.append("  -> imbalance_phase='expansive' si usa SOLO quando il prezzo sta aggressivamente stampando NUOVI massimi/minimi ben LONTANO dal livello IB (chasing attivo).")

    return "\n".join(narrative)

def find_similar_trades(setup_category: str, direction: str, day_type: str) -> str:
    from pathlib import Path
    import json
    
    trades_path = Path(__file__).parent.parent / 'agent_memory' / 'trades_log.jsonl'
    if not trades_path.exists():
        return ""
        
    similar_trades = []
    try:
        with open(trades_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                trade = json.loads(line)
                
                score = 0
                if str(trade.get('setup_type', '')).lower() == str(setup_category).lower():
                    score += 3
                if str(trade.get('direction', '')).lower() == str(direction).lower():
                    score += 2
                if str(trade.get('day_type', '')).lower() == str(day_type).lower():
                    score += 1
                    
                if score >= 2:
                    similar_trades.append((score, trade))
    except Exception:
        pass
        
    if not similar_trades:
        return ""
        
    similar_trades.sort(key=lambda x: x[0], reverse=True)
    top_trades = similar_trades[:3]
    
    lines = ["## HISTORICAL SIMILAR TRADES MEMORY (Few-Shot Context)"]
    for score, t in top_trades:
        entry_t = t.get('entry_time', '')
        if 'T' in entry_t:
            entry_t = entry_t.split('T')[0]
        pnl = t.get('pnl_usd', 0.0)
        pnl_ticks = t.get('pnl_ticks', 0.0)
        exit_r = t.get('exit_reason', 'unknown')
        
        # Safe string slicing
        fab_reas = str(t.get('fabio_reasoning', ''))
        fab_reas_trunc = fab_reas[:150] + "..." if len(fab_reas) > 150 else fab_reas
        
        lines.append(
            f"- Date: {entry_t} | Setup: {t.get('setup_type')} | Direction: {t.get('direction').upper()} | "
            f"Result: {exit_r.upper()} (PnL: ${pnl:.2f}, {pnl_ticks:.1f} ticks) | "
            f"Fabio's reasoning: {fab_reas_trunc}"
        )
    return "\n".join(lines)

def build_fabio_question(candidate: CandidateBar, session_context: list = None, m1_bars: list[Bar] = None, market_narrative: str = "", bars_since_last: list[Bar] = None) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    bar_et_time = t_et
    ib_end_time = bar_et_time.replace(hour=10, minute=0, second=0, microsecond=0)

    # Compute ignition status from M1 bars (pure Python, no LLM)
    m1_bars_ignition = detect_accumulation_breakout(m1_bars or [], candidate.bar, session_ctx=ctx) if m1_bars else None

    amt_narrative = build_amt_narrative(ctx, candidate, ignition_info=m1_bars_ignition, m1_bars=m1_bars)
    
    # Calculate Temporal Phase (IVB = 09:30 - 10:00, trade attivi da 09:55)
    time_val = bar_et_time.hour + bar_et_time.minute / 60.0
    if time_val < 10.0:
        temporal_phase = "The Open / IVB Phase (09:30 - 10:00 ET) — IVB forming, wait for edges"
    elif 10.0 <= time_val < 10.5:
        temporal_phase = "Transition / Post-IVB (10:00 - 10:30 ET) — first breakout confirmation window"
    elif 10.5 <= time_val < 12.0:
        temporal_phase = "Mid-Morning (10:30 - 12:00 ET) — trend continuation or chop detection"
    elif 12.0 <= time_val < 13.5:
        temporal_phase = "The Lunch Lull (12:00 - 13:30 ET) — low conviction zone, toxic flow risk"
    else:
        temporal_phase = "Power Hour / PM Session (13:30 - 16:00 ET) — retest sensitive levels, second drive"

    if bar_et_time >= ib_end_time:
        ib_pos = 'above IVB' if bar.close > ctx.ib_high else \
                 'below IVB' if bar.close < ctx.ib_low  else 'inside IVB'
    else:
        if ctx.vp:
            ib_pos = 'above Overnight VA' if bar.close > ctx.vp.va_high else \
                     'below Overnight VA' if bar.close < ctx.vp.va_low else 'inside Overnight VA'
        else:
            ib_pos = 'Price Discovery (First Hour)'
    if ctx.day_type == 'trend_up':
        suggested = 'long'
    elif ctx.day_type == 'trend_down':
        suggested = 'short'
    else:
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
    
    print(f"DEBUG_SUGGESTED: time={bar.timestamp} category={candidate.setup_category} ib_pos={ib_pos} wall_side={candidate.wall_side} suggested={suggested}")
    candidate.session_bias = suggested
    
    m5_sequence = _format_m5_sequence(candidate.recent_bars) if candidate.recent_bars else ""
    m1_sequence = _format_m1_sequence(m1_bars) if m1_bars else ""
    
    # Select appropriate template: imbalance_hunting and liquidity_map get a trend-continuation framing
    if (candidate.setup_category == 'imbalance_hunting' or str(candidate.setup_category).startswith('liquidity_map_')) and 'fabio_imbalance_question_template' in templates:
        tpl = templates['fabio_imbalance_question_template']
    else:
        tpl = templates['fabio_nlm_question_template']
    question = tpl.format(
        date            = bar.timestamp.strftime('%Y-%m-%d'),
        bar_time_et     = t_et.strftime('%H:%M'),
        amt_narrative   = amt_narrative,
        close           = bar.close,
        ib_high         = f"{ctx.ib_high} (Forming)" if not ctx.ib_complete else ctx.ib_high,
        ib_low          = f"{ctx.ib_low} (Forming)" if not ctx.ib_complete else ctx.ib_low,
        ib_range        = f"{ctx.ib_range} (Forming)" if not ctx.ib_complete else ctx.ib_range,
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
        market_structure= ctx.market_structure_state,
        temporal_phase  = temporal_phase,
        suggested_direction = suggested,
    )
    # Add previous day VP context for reference levels
    if ctx.prev_day_vp:
        pvp = ctx.prev_day_vp
        question += (
            f"\n\nPrevious day VP: POC={pvp.poc:.2f} VAH={pvp.va_high:.2f} "
            f"VAL={pvp.va_low:.2f} HVN={pvp.hvn_levels} LVN={pvp.lvn_levels}"
        )
    # Inject Inter-Day Memory (Telegram Analysis and End-of-Day Narrative)
    # To optimize performance and cache hits, we only inject full day reviews early in the day (before 09:45 ET)
    if ctx.historical_days and time_val < 9.75:
        question += "\n\n### MULTI-DAY MEMORY & LESSONS LEARNED ###\n"
        question += "You must adapt your trading logic based on the feedback from the previous days below.\n\n"
        for i, h_day in enumerate(ctx.historical_days):
            day_label = f"T-{i+1} ({h_day.date})"
            question += f"--- {day_label} ---\n"
            if h_day.market_narrative:
                question += f"Your Final Narrative on {day_label}:\n{h_day.market_narrative}\n\n"
            if h_day.telegram_analysis:
                question += f"End of Day Performance Review on {day_label}:\n{h_day.telegram_analysis}\n\n"
    elif ctx.historical_days:
        # Keep a ultra-compact summary to prevent token bloat during active session
        question += "\n\n### MULTI-DAY SUMMARY ###\n"
        question += "Previous days dates: " + ", ".join(f"T-{i+1} ({h.date})" for i, h in enumerate(ctx.historical_days)) + "\n"
        
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
        question += "\n\n### STRUCTURAL MEMORY (Recent Events) ###\n"
        question += "You must check how levels reacted earlier today to avoid traps (showing max last 6 events):\n"
        question += "\n".join(f"- {line}" for line in struc_mem[-6:])

    # Inject Liquidity Map History (Big Trade Nodes)
    if hasattr(ctx, 'active_walls') and ctx.active_walls:
        question += "\n\n### LIQUIDITY MAP (BIG TRADE NODES - Recent 6) ###\n"
        question += "These are the key institutional levels established so far today. Use them to link events.\n"
        # Sort by time
        walls_sorted = sorted(ctx.active_walls, key=lambda w: w.timestamp)
        for w in walls_sorted[-6:]: # Show max last 6 walls to save context
            time_str = w.timestamp.astimezone(ET).strftime('%H:%M:%S')
            question += f"- {time_str} | {w.side} Wall at {w.price:.2f} | Size: {w.size} | Status: {w.status}\n"

    # (Removed redundant session_context lines to prevent prompt token accumulation and optimize caching)

        
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
        
    # Inject Level Matrix
    question += f"\n\n{build_level_matrix(ctx, bar)}"
    
    # Inject AMT Session Profile
    question += f"\n\n## AMT SESSION STRUCTURAL PROFILE\n{get_amt_structural_profile(ctx)}"
    
    # Inject Macro Regime Status
    macro_info = analyze_macro_regime(ctx, candidate.recent_bars)
    question += (
        f"\n\n## LIVE MACRO REGIME STATUS\n"
        f"Current Regime: {macro_info['regime']}\n"
        f"Regime Duration: {macro_info['duration_mins']} minutes\n"
        f"Regime Trigger: {macro_info['trigger']}\n"
        f"Suggested Trend Bias: {macro_info['bias'].upper()}\n"
    )
    
    # Inject Trapped Participants & Follow-Through
    if m1_bars:
        question += f"\n\n## TRAPPED PARTICIPANTS & FOLLOW-THROUGH (M1 Order Flow)\n{analyze_trap_follow_through(m1_bars)}"
        
    # Inject Macroeconomic News
    if getattr(candidate, 'upcoming_news', None):
        question += f"\n\n## UPCOMING MACROECONOMIC NEWS CALENDAR\n{candidate.upcoming_news}\n"



    # --- POST-LOSS WARNING ---
    if ctx.session_memory:
        for mem in reversed(ctx.session_memory):
            text = mem.get('text', '')
            if 'Closed' in text and '(Loss:' in text:
                mem_time = mem.get('timestamp')
                if mem_time:
                    time_since = (bar.timestamp - mem_time).total_seconds() / 60.0
                    if time_since < 15:
                        post_loss_warning = (
                            f"### 🚨 CRITICAL POST-LOSS WARNING 🚨\n"
                            f"You recently suffered a STOP LOSS ({time_since:.1f} minutes ago): {text}\n"
                            f"BEFORE YOU OPEN A NEW TRADE, YOU MUST EXPLICITLY REASON ABOUT WHY IT FAILED in your logic.\n"
                            f"- Did you enter too late (chasing an extended move)?\n"
                            f"- Was it a fakeout or lack of institutional follow-through?\n"
                            f"DO NOT take a new trade in the same direction unless you have a completely fresh, high-conviction structural confirmation. "
                            f"Do NOT revenge trade inside the same candle zone!\n"
                        )
                        question += f"\n\n{post_loss_warning}"
                break  # Only care about the most recent closed trade

    # ── 1. 5-DAY ATR VOLATILITY CONTEXT ──
    atr_5d = getattr(ctx, 'atr_5day', 180.0)
    question += f"\n\n## 5-DAY ATR VOLATILITY CONTEXT\n"
    question += f"The 5-day daily ATR is currently: {atr_5d:.2f} points.\n"
    question += "CRITICAL: You MUST scale your Stop Loss and Profit Target based on this volatility. For NQ, a standard Stop Loss is approximately 0.25 * ATR, and a standard Profit Target is approximately 0.6 * ATR. Do not place micro-stops (below 20 points) in high ATR regimes.\n"

    # ── 2. NEWS COUNTDOWN ALERT ──
    if getattr(candidate, 'upcoming_news', None) and "HIGH IMPACT NEWS:" in candidate.upcoming_news:
        question += f"\n\n🚨 [NEWS COUNTDOWN ALERT] 🚨\n"
        question += f"{candidate.upcoming_news}\n"
        question += "WARNING: High-impact economic releases generate unpredictable, toxic volatility. If the release is less than 10 minutes away (or occurred less than 5 minutes ago), you must EXPLICITLY justify if you want to take a trade, or veto/skip it (by outputting direction='none' or confidence < 65).\n"

    # ── 3. AUTOMATED TEMPORAL AUDIT SCORE ──
    h_m_et = t_et.hour * 60 + t_et.minute
    if 12*60 <= h_m_et < 13*60 + 30:
        q1 = 20
    elif h_m_et >= 15*60: # PM session late
        q1 = 50
    else:
        q1 = 95
        
    if 10*60 + 15 <= h_m_et < 10*60 + 30:
        q2 = 20
    else:
        q2 = 95
        
    # q3: Delta alignment or Absorption conviction
    is_absorption = (
        candidate.setup_category == 'reversal' or 
        'absorb' in str(candidate.setup_category).lower() or
        'trapped' in str(candidate.setup_category).lower() or
        'liquidity_map' in str(candidate.setup_category).lower()
    )
    if is_absorption:
        if (suggested == 'long' and bar.delta < 0) or (suggested == 'short' and bar.delta > 0):
            q3 = 90
        else:
            q3 = 50
    else:
        if (suggested == 'long' and bar.delta > 0) or (suggested == 'short' and bar.delta < 0):
            q3 = 90
        else:
            q3 = 50
        
    # q4: Trend alignment or Reversal extremes
    is_trend_aligned = False
    if suggested in ['long', 'short']:
        is_trend_aligned = True
        
    wick_ratio = getattr(candidate, 'bottom_wick_ratio', 0.0) if suggested == 'long' else getattr(candidate, 'top_wick_ratio', 0.0)
    if is_trend_aligned:
        q4 = 95
    elif candidate.setup_category == 'reversal' and wick_ratio >= 0.35:
        q4 = 90
    else:
        q4 = 40
        
    prox_dist = abs(bar.close - candidate.proximity_level) if candidate.proximity_level else 999.0
    if prox_dist <= 3.0: # 12 ticks
        q5 = 90
    else:
        q5 = 30

    temporal_audit_str = f"q1:{q1}%, q2:{q2}%, q3:{q3}%, q4:{q4}%, q5:{q5}%"
    question += f"\n\n## SYSTEM-COMPUTED TEMPORAL AUDIT SCORE\n"
    question += f"{temporal_audit_str}\n"
    question += "CRITICAL: The above percentages are calculated mathematically by the system. You MUST output this exact string in your 'temporal_audit' JSON field, and you MUST align your 'confidence' and 'direction' logic with these scores. If two or more scores are below 50%, your confidence must be below 65%.\n"

    # ── 4. HISTORICAL SIMILAR TRADES MEMORY (Few-Shot Context) ──
    similar_trades_str = find_similar_trades(candidate.setup_category, suggested, ctx.day_type)
    if similar_trades_str:
        question += f"\n\n{similar_trades_str}\n"

    # Append GEX options structure context
    gex_info = (
        f"\n\n## OPTIONS MARKET STRUCTURE (GEX DATA)\n"
        f"- Current GEX Regime: {ctx.gex_regime.upper()} (Volatility expectation: "
        f"{'Chop/Mean-Reversion' if ctx.gex_regime == 'positive' else 'Trend/Expansion'})\n"
        f"- Zero Gamma Flip Level: {ctx.zero_gamma_level:.2f}\n"
        f"- Call Wall (Major Option Resistance): {ctx.call_wall:.2f}\n"
        f"- Put Wall (Major Option Support): {ctx.put_wall:.2f}"
    )
    question += gex_info

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
        ib_high         = f"{ctx.ib_high} (Forming)" if not ctx.ib_complete else ctx.ib_high,
        ib_low          = f"{ctx.ib_low} (Forming)" if not ctx.ib_complete else ctx.ib_low,
        ib_range        = f"{ctx.ib_range} (Forming)" if not ctx.ib_complete else ctx.ib_range,
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

    # Inject Level Matrix
    question += f"\n\n{build_level_matrix(ctx, bar)}"
    
    # Inject AMT Session Profile
    question += f"\n\n## AMT SESSION STRUCTURAL PROFILE\n{get_amt_structural_profile(ctx)}"
    
    # Inject Macro Regime Status
    macro_info = analyze_macro_regime(ctx, candidate.recent_bars)
    question += (
        f"\n\n## LIVE MACRO REGIME STATUS\n"
        f"Current Regime: {macro_info['regime']}\n"
        f"Regime Duration: {macro_info['duration_mins']} minutes\n"
        f"Regime Trigger: {macro_info['trigger']}\n"
        f"Suggested Trend Bias: {macro_info['bias'].upper()}\n"
    )
    
    # Inject Trapped Participants & Follow-Through
    if m1_bars:
        question += f"\n\n## TRAPPED PARTICIPANTS & FOLLOW-THROUGH (M1 Order Flow)\n{analyze_trap_follow_through(m1_bars)}"
        
    # Inject Macroeconomic News
    if getattr(candidate, 'upcoming_news', None):
        question += f"\n\n## UPCOMING MACROECONOMIC NEWS CALENDAR\n{candidate.upcoming_news}\n"

    # Append GEX options structure context
    gex_info = (
        f"\n\n## OPTIONS MARKET STRUCTURE (GEX DATA)\n"
        f"- Current GEX Regime: {ctx.gex_regime.upper()}\n"
        f"- Zero Gamma Flip Level: {ctx.zero_gamma_level:.2f}\n"
        f"- Call Wall: {ctx.call_wall:.2f}\n"
        f"- Put Wall: {ctx.put_wall:.2f}"
    )
    question += gex_info

    return question

def analyze_trapped_participants(bar: Bar) -> str:
    """Analyze the price-by-price footprint map of a bar to find trapped participants in the wicks."""
    if not getattr(bar, 'footprint', None):
        return ""
        
    open_p = bar.open
    close_p = bar.close
    
    # Wick boundaries
    body_high = max(open_p, close_p)
    body_low = min(open_p, close_p)
    
    top_wick_vol_ask = 0
    top_wick_vol_bid = 0
    bot_wick_vol_ask = 0
    bot_wick_vol_bid = 0
    
    # Iterate over price levels in footprint
    for price, bids_asks in bar.footprint.items():
        bid_vol = bids_asks.get('bid', 0)
        ask_vol = bids_asks.get('ask', 0)
        
        # Is price in the top wick?
        if price > body_high:
            top_wick_vol_ask += ask_vol  # Buyers hitting Ask (aggressive buyers)
            top_wick_vol_bid += bid_vol  # Sellers hitting Bid
            
        # Is price in the bottom wick?
        elif price < body_low:
            bot_wick_vol_ask += ask_vol
            bot_wick_vol_bid += bid_vol  # Sellers hitting Bid (aggressive sellers)
            
    trapped_info = []
    
    if top_wick_vol_ask >= 40 and top_wick_vol_ask > top_wick_vol_bid:
        trapped_info.append(
            f"TRAPPED BUYERS: {top_wick_vol_ask} Ask contracts vs Bid {top_wick_vol_bid} "
            f"above {body_high:.2f} (close {close_p:.2f})"
        )
        
    if bot_wick_vol_bid >= 40 and bot_wick_vol_bid > bot_wick_vol_ask:
        trapped_info.append(
            f"TRAPPED SELLERS: {bot_wick_vol_bid} Bid contracts vs Ask {bot_wick_vol_ask} "
            f"below {body_low:.2f} (close {close_p:.2f})"
        )
        
    return " | ".join(trapped_info)

def analyze_trap_follow_through(bars: list[Bar]) -> str:
    """Scans the M1 bars to find where trapped participants occurred and describes the follow-through in the subsequent candle.
    
    IMPORTANT: We only analyze up to bars[-2] as 'current bar'. The follow-through is
    bars[i+1], which must be a fully-closed M1 bar at the time of the decision.
    The last bar in the list (bars[-1]) is the CURRENT bar being evaluated — we cannot
    know its follow-through yet, so it is excluded as a 'trap origin'.
    """
    if not bars or len(bars) < 2:
        return "No significant trapped events in the recent M1 window."
        
    analysis_lines = []
    # Stop at len(bars) - 1 so bars[i+1] is always the last bar (already closed historical)
    # and bars[i] never uses the current/candidate bar as the trap origin.
    for i in range(len(bars) - 1):
        b_curr = bars[i]
        b_next = bars[i+1]
        
        open_p = b_curr.open
        close_p = b_curr.close
        body_high = max(open_p, close_p)
        body_low = min(open_p, close_p)
        
        top_wick_ask = sum(val.get('ask', 0) for pr, val in getattr(b_curr, 'footprint', {}).items() if pr > body_high)
        top_wick_bid = sum(val.get('bid', 0) for pr, val in getattr(b_curr, 'footprint', {}).items() if pr > body_high)
        bot_wick_ask = sum(val.get('ask', 0) for pr, val in getattr(b_curr, 'footprint', {}).items() if pr < body_low)
        bot_wick_bid = sum(val.get('bid', 0) for pr, val in getattr(b_curr, 'footprint', {}).items() if pr < body_low)
        
        t_curr = b_curr.timestamp.astimezone(ET).strftime('%H:%M:%S')
        t_next = b_next.timestamp.astimezone(ET).strftime('%H:%M:%S')
        
        # 1. Trapped Buyers check
        if top_wick_ask >= 40 and top_wick_ask > top_wick_bid:
            next_close_vs_curr = b_next.close - b_curr.close
            next_delta = b_next.delta
            
            if next_close_vs_curr < 0 and next_delta < 0:
                outcome = f"CONFIRMED (Next bar at {t_next} closed lower by {abs(next_close_vs_curr):.2f} pts with negative delta of {next_delta:+d})"
            elif next_close_vs_curr < 0:
                outcome = f"CONFIRMED (Next bar closed lower by {abs(next_close_vs_curr):.2f} pts, delta {next_delta:+d})"
            elif next_close_vs_curr > 0 and b_next.close > b_curr.high:
                outcome = f"FAILED / RELEASED (Next bar closed above the trap high at {b_next.close:.2f}, negating short bias)"
            else:
                outcome = f"MIXED (Next bar closed slightly higher by {next_close_vs_curr:.2f} pts, delta {next_delta:+d})"
                
            analysis_lines.append(
                f"- [{t_curr}] Trapped Buyers ({top_wick_ask} Ask contracts above {body_high:.2f}) -> {outcome}"
            )
            
        # 2. Trapped Sellers check
        if bot_wick_bid >= 40 and bot_wick_bid > bot_wick_ask:
            next_close_vs_curr = b_next.close - b_curr.close
            next_delta = b_next.delta
            
            if next_close_vs_curr > 0 and next_delta > 0:
                outcome = f"CONFIRMED (Next bar at {t_next} closed higher by {next_close_vs_curr:.2f} pts with positive delta of {next_delta:+d})"
            elif next_close_vs_curr > 0:
                outcome = f"CONFIRMED (Next bar closed higher by {next_close_vs_curr:.2f} pts, delta {next_delta:+d})"
            elif next_close_vs_curr < 0 and b_next.close < b_curr.low:
                outcome = f"FAILED / RELEASED (Next bar closed below the trap low at {b_next.close:.2f}, negating long bias)"
            else:
                outcome = f"MIXED (Next bar closed slightly lower by {abs(next_close_vs_curr):.2f} pts, delta {next_delta:+d})"
                
            analysis_lines.append(
                f"- [{t_curr}] Trapped Sellers ({bot_wick_bid} Bid contracts below {body_low:.2f}) -> {outcome}"
            )
            
    if not analysis_lines:
        return "No significant trapped events in the recent M1 window."
    return "\n".join(analysis_lines)

def get_amt_structural_profile(ctx) -> str:
    """Classifies the session structure using Dalton's Auction Market Theory concepts."""
    if not getattr(ctx, 'ib_complete', False):
        return "Price Discovery Phase (First 30 minutes of session)"
        
    ib_high = getattr(ctx, 'ib_high', 0.0)
    ib_low = getattr(ctx, 'ib_low', 0.0)
    ib_range = getattr(ctx, 'ib_range', 0.0)
    high = getattr(ctx, 'session_high', 0.0)
    low = getattr(ctx, 'session_low', 0.0)
    
    if ib_high <= 0 or ib_low <= 0:
        return "Initial Balance not completed or invalid."
        
    broken_above = high > ib_high
    broken_below = low < ib_low
    
    if broken_above and broken_below:
        return "Neutral Day (IB broken on BOTH sides - high volatility, two-way auction, balance day)"
    elif broken_above:
        return "Normal Variation Day (IB broken to the upside - buyers control the extension)"
    elif broken_below:
        return "Normal Variation Day (IB broken to the downside - sellers control the extension)"
    else:
        # IB never broken
        if ib_range > 60:
            return "Normal Day (Wide IB, never broken - responsive trading at extremes expected)"
        else:
            return "Non-Trend Day / Balance Day (Narrow IB, never broken - low volume, high chop risk)"

def build_level_matrix(ctx, current_bar: Bar) -> str:
    """Builds a structured text grid of all key levels, their distance, and their test status today."""
    levels = []
    if getattr(ctx, 'prev_day_vp', None):
        levels.append(("Yesterday VAH", ctx.prev_day_vp.va_high))
        levels.append(("Yesterday VAL", ctx.prev_day_vp.va_low))
        levels.append(("Yesterday POC", ctx.prev_day_vp.poc))
    if getattr(ctx, 'ib_high', 0.0) > 0:
        levels.append(("IB High", ctx.ib_high))
        levels.append(("IB Low", ctx.ib_low))
    if getattr(ctx, 'vp', None):
        levels.append(("Overnight VAH", ctx.vp.va_high))
        levels.append(("Overnight VAL", ctx.vp.va_low))
        levels.append(("Overnight POC", ctx.vp.poc))
        
    lines = ["## SESSION STRUCTURAL LEVEL MATRIX"]
    lines.append(f"Current Price: {current_bar.close:.2f}")
    lines.append(f"{'Level Name':<20} | {'Price':<10} | {'Dist (Pts)':<10} | {'Status today'}")
    lines.append("-" * 70)
    
    for name, val in levels:
        if val is None or val <= 0:
            continue
        dist = current_bar.close - val
        dist_str = f"{dist:+.2f}"
        
        status = "Untested"
        for item in reversed(getattr(ctx, 'session_memory', [])):
            if f"Tested {name}" in item.get('text', ''):
                parts = item['text'].split("Result: ")
                if len(parts) > 1:
                    outcome = parts[1].split(".")[0]
                    status = f"Tested ({outcome})"
                break
                
        lines.append(f"{name:<20} | {val:<10.2f} | {dist_str:<10} | {status}")
        
    return "\n".join(lines)

def analyze_macro_regime(ctx, bars: list) -> dict:
    """Detects if the market is in an EXPANSIVE or ACCUMULATION/BALANCE regime, since when, and the bias."""
    if not bars:
        return {"regime": "CHOP/BALANCE", "duration_mins": 0, "trigger": "No bar data", "bias": "none"}
        
    ib_high = getattr(ctx, 'ib_high', 0.0)
    ib_low = getattr(ctx, 'ib_low', 0.0)
    ib_complete = getattr(ctx, 'ib_complete', False)
    
    current_regime = "CHOP/BALANCE"
    current_trigger = "Price trading inside Initial Balance / Value Area"
    current_bias = "none"
    duration_bars = 0
    
    for i in range(len(bars) - 1, -1, -1):
        b = bars[i]
        
        is_outside = False
        if ib_complete and ib_high > 0 and ib_low > 0:
            is_outside = (b.close > ib_high or b.close < ib_low)
            
        if is_outside:
            # Imbalance outside IB
            prev_ranges = []
            for j in range(max(0, i-4), i):
                prev_ranges.append(bars[j].high - bars[j].low)
            avg_range = sum(prev_ranges) / len(prev_ranges) if prev_ranges else 10.0
            
            curr_range = b.high - b.low
            
            if curr_range < 0.80 * avg_range:
                regime = "ACCUMULATION (Pullback/Absorption)"
                trigger = f"Range compression ({curr_range/avg_range:.0%}) outside IB"
                bias = "long" if b.close > ib_high else "short"
            else:
                regime = "EXPANSIVE (Initiative Momentum)"
                trigger = f"Breakout outside IB ({'above IB High' if b.close > ib_high else 'below IB Low'})"
                bias = "long" if b.close > ib_high else "short"
        else:
            regime = "CHOP/BALANCE"
            trigger = "Price trading inside Initial Balance / Value Area"
            bias = "none"
            
        if i == len(bars) - 1:
            current_regime = regime
            current_trigger = trigger
            current_bias = bias
            
        if regime != current_regime:
            break
            
        duration_bars += 1
        
    return {
        "regime": current_regime,
        "duration_mins": duration_bars * 5,
        "trigger": current_trigger,
        "bias": current_bias
    }

def detect_accumulation_breakout(m1_bars: list, current_bar, session_ctx=None) -> dict:
    """Accumulation zone detector using IB (Initial Balance) as primary reference.

    The IB [ib_low, ib_high] IS the accumulation zone for the opening session strategy.
    - INSIDE IB → accumulation/balance → do not enter
    - CLOSE OUTSIDE IB with delta confirmation → IGNITION (first breakout)
    - Within 3 bars of breakout → EARLY EXPANSION → still valid entry

    Falls back to dynamic range-compression detection when IB is not yet complete.

    Args:
        m1_bars     : list of Bar objects (all M1 bars before current)
        current_bar : the Bar being evaluated
        session_ctx : optional SessionContext for IB data

    Returns dict with:
      in_accumulation    : bool
      is_ignition        : bool
      ignition_direction : 'long' | 'short' | 'none'
      bars_since_ignition: int  (0=this IS ignition, -1=not found)
      accumulation_high  : float  (IB high or dynamic zone high)
      accumulation_low   : float  (IB low or dynamic zone low)
      accumulation_mins  : int
      avg_range          : float
      atr                : float
      label              : str
    """
    MAX_BARS_AFTER = 20  # 20 M1 bars (~20min) entry window after ignition
    DELTA_MIN      = 30  # minimum |delta| for ignition confirmation

    result = {
        "in_accumulation":    False,
        "is_ignition":        False,
        "ignition_direction": "none",
        "bars_since_ignition": -1,
        "accumulation_high":   0.0,
        "accumulation_low":    0.0,
        "accumulation_mins":   0,
        "avg_range":           0.0,
        "atr":                 0.0,
        "label": "Insufficient data for accumulation analysis."
    }

    curr       = current_bar
    curr_delta = getattr(curr, 'delta', 0) or 0

    # ── ATR for reference ────────────────────────────────────────────────────
    atr_bars = m1_bars[-20:] if len(m1_bars) >= 20 else m1_bars
    atr = (sum(b.high - b.low for b in atr_bars) / len(atr_bars)) if atr_bars else 0.0
    result["atr"] = round(atr, 2)

    # ── PRIMARY: Use IB as accumulation zone if available ────────────────────
    ib_high = getattr(session_ctx, 'ib_high', 0.0) if session_ctx else 0.0
    ib_low  = getattr(session_ctx, 'ib_low', 0.0) if session_ctx else 0.0
    ib_complete = getattr(session_ctx, 'ib_complete', False) if session_ctx else False

    if ib_complete and ib_high > 0 and ib_low > 0:
        acc_high = ib_high
        acc_low  = ib_low
        result["accumulation_high"] = acc_high
        result["accumulation_low"]  = acc_low

        # ── CVD over the last N M1 bars (expansive volume confirmation) ──
        # CVD = cumulative sum of bar delta — rising CVD = net buying pressure
        CVD_WINDOW = 20  # look at last 20 M1 bars to measure CVD trend
        cvd_bars = m1_bars[-CVD_WINDOW:] if len(m1_bars) >= CVD_WINDOW else m1_bars
        cvd_total = sum(getattr(b, 'delta', 0) or 0 for b in cvd_bars)
        # CVD first-half vs second-half to detect trend direction
        mid = max(1, len(cvd_bars) // 2)
        cvd_first_half  = sum(getattr(b, 'delta', 0) or 0 for b in cvd_bars[:mid])
        cvd_second_half = sum(getattr(b, 'delta', 0) or 0 for b in cvd_bars[mid:])
        cvd_rising  = cvd_second_half > cvd_first_half  # accelerating buying
        cvd_falling = cvd_second_half < cvd_first_half  # accelerating selling
        result["cvd_total"]   = cvd_total
        result["cvd_rising"]  = cvd_rising
        result["cvd_falling"] = cvd_falling

        inside_ib = acc_low <= curr.close <= acc_high
        if inside_ib:
            result["in_accumulation"] = True
            cvd_note = f"CVD({CVD_WINDOW}bars)={cvd_total:+d} {'rising' if cvd_rising else 'falling' if cvd_falling else 'flat'}"
            result["label"] = (
                f"INSIDE IB ({acc_low:.2f}-{acc_high:.2f}): accumulation/balance phase. "
                f"{cvd_note}. "
                f"WAIT for a close outside IB with |delta| >= {DELTA_MIN} before entering."
            )
            return result

        # Price is outside IB — find first bar outside IB with delta confirmation after 10:00 ET
        ign_bar_idx  = -1
        ign_dir      = "none"
        for k, b in enumerate(m1_bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.hour < 10:
                continue
            
            b_delta = getattr(b, 'delta', 0) or 0
            if b.close > acc_high and b_delta >= DELTA_MIN:
                ign_bar_idx = k
                ign_dir = "long"
                break
            elif b.close < acc_low and b_delta <= -DELTA_MIN:
                ign_bar_idx = k
                ign_dir = "short"
                break

        # Calculate bars_since if found
        bars_since = -1
        if ign_bar_idx >= 0:
            curr_idx = -1
            for idx, b in enumerate(m1_bars):
                if b.timestamp == curr.timestamp:
                    curr_idx = idx
                    break
            if curr_idx >= 0:
                bars_since = curr_idx - ign_bar_idx
            else:
                bars_since = len(m1_bars) - 1 - ign_bar_idx

        if ign_bar_idx >= 0 and 0 <= bars_since <= MAX_BARS_AFTER:
            result["is_ignition"] = (bars_since == 0)
            result["ignition_direction"] = ign_dir
            result["bars_since_ignition"] = bars_since
            
            post_ign_bars = m1_bars[ign_bar_idx:]
            cvd_since_ign = sum(getattr(b, 'delta', 0) or 0 for b in post_ign_bars)
            cvd_confirms  = (ign_dir == "long" and cvd_since_ign > 0) or \
                            (ign_dir == "short" and cvd_since_ign < 0)
            result["cvd_since_ign"] = cvd_since_ign
            
            cvd_note = f"CVD since ignition={cvd_since_ign:+d} {'OK' if cvd_confirms else 'WEAK'}"
            if bars_since == 0:
                result["label"] = (
                    f"IGNITION BAR {ign_dir.upper()} -- broke IB [{acc_low:.2f}-{acc_high:.2f}], "
                    f"close={curr.close:.2f}, delta={curr_delta:+d}, CVD={cvd_total:+d}. IDEAL ENTRY."
                )
            else:
                result["label"] = (
                    f"EARLY EXPANSION ({ign_dir.upper()}, {bars_since} bars ago) -- "
                    f"IB [{acc_low:.2f}-{acc_high:.2f}] broke. {cvd_note}. "
                    f"Still valid entry window ({bars_since}/{MAX_BARS_AFTER} bars used)."
                )
        elif ign_bar_idx >= 0:
            result["ignition_direction"] = ign_dir
            result["bars_since_ignition"] = bars_since
            result["label"] = (
                f"MID/LATE EXPANSION -- IB [{acc_low:.2f}-{acc_high:.2f}] "
                f"broke more than {MAX_BARS_AFTER} bars ago ({bars_since} bars ago). Higher chasing risk."
            )
        else:
            result["label"] = (
                f"OUTSIDE IB but NO confirmed ignition bar found (no bar had delta >= {DELTA_MIN}). Vetoed."
            )
        return result

    # ── FALLBACK: Dynamic range-compression detection (no IB yet) ────────────
    # Used during IB formation (first 30 minutes)
    EXPANSION_THRESH   = 1.2
    COMPRESSION_THRESH = 0.55
    MAX_ACC_BARS       = 300
    MIN_ACC_BARS       = 5

    if not m1_bars or len(m1_bars) < 20 + MIN_ACC_BARS:
        result["label"] = "IB not yet complete and insufficient M1 history for dynamic detection."
        return result

    atr_sample = m1_bars[-20:]
    atr_val = sum(b.high - b.low for b in atr_sample) / 20
    result["atr"] = round(atr_val, 2)
    exp_thresh = EXPANSION_THRESH * atr_val

    acc_start_idx = None
    for i in range(len(m1_bars) - 1, max(0, len(m1_bars) - 1 - MAX_ACC_BARS) - 1, -1):
        if m1_bars[i].high - m1_bars[i].low >= exp_thresh:
            acc_start_idx = i + 1
            break
    if acc_start_idx is None:
        acc_start_idx = max(0, len(m1_bars) - MAX_ACC_BARS)

    acc_bars = m1_bars[acc_start_idx:]
    if len(acc_bars) < MIN_ACC_BARS:
        result["label"] = f"Pre-IB accumulation zone too short ({len(acc_bars)} bars)."
        return result

    acc_high = max(b.high for b in acc_bars)
    acc_low  = min(b.low  for b in acc_bars)
    avg_range = sum(b.high - b.low for b in acc_bars) / len(acc_bars)
    result["accumulation_high"] = acc_high
    result["accumulation_low"]  = acc_low
    result["avg_range"]         = round(avg_range, 2)
    result["accumulation_mins"] = len(acc_bars)

    is_compressed = avg_range < COMPRESSION_THRESH * atr_val
    result["in_accumulation"] = is_compressed

    if is_compressed:
        if curr.close > acc_high and curr_delta >= DELTA_MIN:
            result["is_ignition"]        = True
            result["ignition_direction"] = "long"
            result["bars_since_ignition"] = 0
            result["label"] = (
                f"IGNITION LONG (pre-IB) -- broke [{acc_low:.2f}-{acc_high:.2f}], "
                f"close={curr.close:.2f}, delta={curr_delta:+d}."
            )
        elif curr.close < acc_low and curr_delta <= -DELTA_MIN:
            result["is_ignition"]        = True
            result["ignition_direction"] = "short"
            result["bars_since_ignition"] = 0
            result["label"] = (
                f"IGNITION SHORT (pre-IB) -- broke [{acc_low:.2f}-{acc_high:.2f}], "
                f"close={curr.close:.2f}, delta={curr_delta:+d}."
            )
        else:
            result["label"] = (
                f"PRE-IB MID-ACCUMULATION ({len(acc_bars)}min) -- "
                f"zone [{acc_low:.2f}-{acc_high:.2f}]. WAIT for breakout."
            )
    else:
        result["label"] = (
            f"PRE-IB EXPANSION -- zone [{acc_low:.2f}-{acc_high:.2f}] not compressed."
        )
    return result
