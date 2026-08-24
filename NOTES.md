# 📝 NOTE STRATEGIA & CODICE PINESCRIPT: WHALE PRINT & GEX DUAL-REGIME (APEX 50K)

## 📌 Specifiche Chiave della Strategia
* **Target Prop Firm:** Apex Trader Funding (Conto $50,000 / Trailing DD $2,500)
* **Strumento:** MNQ (Micro E-mini Nasdaq)
* **Sizing Raccomandato:** 2 Micro MNQ ($4.00/punto) -> Rischio max $80.00 / trade (3.2% del Trailing DD)
* **Finestre RTH Gold:** 09:45 – 12:00 EST & 13:30 – 15:15 EST
* **Risk Management:** Stop Loss 20.0 pt (-$80.00), Take Profit 60.0 pt (+$240.00), Break-Even Lock a +25.0 pt (+1.0 pt SL).

---

## 📈 Codice Ufficiale Pine Script v5 per TradingView

Copia e incolla il codice seguente nel **Pine Editor** di TradingView e clicca su **"Aggiungi al Grafico"**:

```pinescript
//@version=5
indicator("Matteo Whale Print & GEX Dual-Regime [Apex 50k]", shorttitle="WCE Whale+GEX", overlay=true, max_labels_count=500, max_lines_count=500)

// ── 1. INPUT PARAMETRI ────────────────────────────────────────────────────────
grp_session = "1. Finestre Orarie RTH Gold (EST)"
use_gold_filter  = input.bool(true, "Attiva Finestre Gold", group=grp_session)
gold_session_am  = input.session("0945-1200", "Sessione Mattina (EST)", group=grp_session)
gold_session_pm  = input.session("1330-1515", "Sessione Pomeriggio (EST)", group=grp_session)
session_tz       = input.string("America/New_York", "Timezone", group=grp_session)

grp_whale = "2. Parametri Whale Print & Wick"
min_wick_pts     = input.float(0.5, "Stoppino Minimo (Punti NQ)", step=0.25, group=grp_whale)
vol_multiplier   = input.float(1.8, "Spike Volume Istituzionale (Mult MA)", step=0.1, group=grp_whale)
vol_ma_len       = input.int(20, "Periodo Media Volume", group=grp_whale)

grp_gex = "3. Livelli GEX (Gamma Exposure)"
gex_offset_pts   = input.float(150.0, "Distanza Muri GEX da Zero Gamma (pt)", step=10.0, group=grp_gex)
min_headroom_pts = input.float(15.0, "Headroom Minimo da Call/Put Wall (pt)", step=5.0, group=grp_gex)
smart_tp_clamp   = input.bool(true, "Ancora TP prima della Call/Put Wall", group=grp_gex)

grp_trade = "4. Gestione Rischio & Target (Apex 50k)"
sl_pts           = input.float(20.0, "Stop Loss Fisso (Punti NQ)", step=1.0, group=grp_trade)
tp_pts           = input.float(60.0, "Take Profit Standard (Punti NQ)", step=5.0, group=grp_trade)
be_trigger_pts   = input.float(25.0, "Trigger Break-Even (Punti NQ)", step=1.0, group=grp_trade)
be_offset_pts    = input.float(1.0, "Offset Break-Even (Punti NQ)", step=0.25, group=grp_trade)

// ── 2. CALCOLO SESSIONI & ORARI GOLD ──────────────────────────────────────────
in_am = not na(time(timeframe.period, gold_session_am, session_tz))
in_pm = not na(time(timeframe.period, gold_session_pm, session_tz))
is_gold_window = use_gold_filter ? (in_am or in_pm) : true

// ── 3. CALCOLO DINAMICO LIVELLI GEX ───────────────────────────────────────────
var float zero_gamma_level = na
var float call_wall_level = na
var float put_wall_level = na

vwap_val = ta.vwap(hlc3)
if not na(vwap_val)
    zero_gamma_level := vwap_val
    call_wall_level := zero_gamma_level + gex_offset_pts
    put_wall_level := zero_gamma_level - gex_offset_pts

net_gex_positive = close >= zero_gamma_level

// Plot Livelli GEX
plot(call_wall_level, "Call Wall (Resistenza Opzioni)", color=color.new(color.red, 20), linewidth=2, style=plot.style_linebr)
plot(zero_gamma_level, "Zero Gamma / Flip Level", color=color.new(color.blue, 30), linewidth=2, style=plot.style_linebr)
plot(put_wall_level, "Put Wall (Supporto Opzioni)", color=color.new(color.green, 20), linewidth=2, style=plot.style_linebr)

// ── 4. RILEVAZIONE WHALE PRINT SU WICK ────────────────────────────────────────
vol_ma = ta.sma(volume, vol_ma_len)
is_vol_spike = volume >= (vol_ma * vol_multiplier)

body_high = math.max(open, close)
body_low = math.min(open, close)
upper_wick_pts = high - body_high
lower_wick_pts = body_low - low

is_lower_wick_rejection = lower_wick_pts >= min_wick_pts
is_upper_wick_rejection = upper_wick_pts >= min_wick_pts

// Filtri Headroom GEX
dist_to_call_wall = call_wall_level - close
dist_to_put_wall = close - put_wall_level

has_call_headroom = dist_to_call_wall > min_headroom_pts
has_put_headroom = dist_to_put_wall > min_headroom_pts

// SEGNALI ENTRY
long_signal = is_gold_window and is_vol_spike and is_lower_wick_rejection and net_gex_positive and has_call_headroom
short_signal = is_gold_window and is_vol_spike and is_upper_wick_rejection and not net_gex_positive and has_put_headroom

// ── 5. CALCOLO TARGET DINAMICI (GEX CLAMPING) ─────────────────────────────────
var float active_entry = na
var float active_sl = na
var float active_tp = na
var float active_be = na
var int active_dir = 0

if long_signal and active_dir == 0
    active_dir := 1
    active_entry := close
    active_sl := close - sl_pts
    
    float final_tp = close + tp_pts
    if smart_tp_clamp and dist_to_call_wall > 20.0 and dist_to_call_wall < tp_pts
        final_tp := call_wall_level - 2.0
    active_tp := final_tp
    active_be := close + be_offset_pts

    label.new(bar_index, low - 4.0, "🐋 WHALE BUY\nEntry: " + str.tostring(close, "#.##") + "\nSL: " + str.tostring(active_sl, "#.##") + "\nTP: " + str.tostring(active_tp, "#.##"), 
              color=color.green, textcolor=color.white, style=label.style_label_up, size=size.small)

if short_signal and active_dir == 0
    active_dir := -1
    active_entry := close
    active_sl := close + sl_pts
    
    float final_tp = close - tp_pts
    if smart_tp_clamp and dist_to_put_wall > 20.0 and dist_to_put_wall < tp_pts
        final_tp := put_wall_level + 2.0
    active_tp := final_tp
    active_be := close - be_offset_pts

    label.new(bar_index, high + 4.0, "🐋 WHALE SELL\nEntry: " + str.tostring(close, "#.##") + "\nSL: " + str.tostring(active_sl, "#.##") + "\nTP: " + str.tostring(active_tp, "#.##"), 
              color=color.red, textcolor=color.white, style=label.style_label_down, size=size.small)

// GESTIONE LIVE BRACKET & BREAK-EVEN
if active_dir == 1
    if high >= (active_entry + be_trigger_pts) and active_sl < active_be
        active_sl := active_be
        label.new(bar_index, high, "🔒 BE LOCK", color=color.blue, textcolor=color.white, style=label.style_label_down, size=size.tiny)

    if low <= active_sl or high >= active_tp
        active_dir := 0

if active_dir == -1
    if low <= (active_entry - be_trigger_pts) and active_sl > active_be
        active_sl := active_be
        label.new(bar_index, low, "🔒 BE LOCK", color=color.blue, textcolor=color.white, style=label.style_label_up, size=size.tiny)

    if high >= active_sl or low <= active_tp
        active_dir := 0

bgcolor(is_gold_window ? color.new(color.yellow, 95) : na, title="Finestra Gold RTH")

// ── 6. DASHBOARD HUD LIVE ─────────────────────────────────────────────────────
var table hud = table.new(position.bottom_right, 2, 6, bgcolor=color.new(color.black, 20), border_color=color.gray, border_width=1)
if barstate.islast
    table.cell(hud, 0, 0, "WCE WHALE + GEX", bgcolor=color.blue, text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 0, "APEX 50k", bgcolor=color.blue, text_color=color.white, text_size=size.small)
    table.cell(hud, 0, 1, "Regime GEX", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 1, net_gex_positive ? "POSITIVE (Drift)" : "NEGATIVE (Squeeze)", bgcolor=net_gex_positive ? color.green : color.red, text_color=color.white, text_size=size.small)
    table.cell(hud, 0, 2, "Zero Gamma Flip", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 2, str.tostring(zero_gamma_level, "#.##"), text_color=color.yellow, text_size=size.small)
    table.cell(hud, 0, 3, "Call Wall (+150pt)", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 3, str.tostring(call_wall_level, "#.##"), text_color=color.red, text_size=size.small)
    table.cell(hud, 0, 4, "Put Wall (-150pt)", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 4, str.tostring(put_wall_level, "#.##"), text_color=color.green, text_size=size.small)
    table.cell(hud, 0, 5, "Finestra RTH Gold", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 5, is_gold_window ? "ATTIVA (09:45-15:15)" : "BLACKOUT", bgcolor=is_gold_window ? color.teal : color.maroon, text_color=color.white, text_size=size.small)

alertcondition(long_signal, title="Segnale WHALE BUY", message="🐋 WHALE BUY Triggered! Entry: {{close}}, SL: -20pt, TP: +60pt")
alertcondition(short_signal, title="Segnale WHALE SELL", message="🐋 WHALE SELL Triggered! Entry: {{close}}, SL: -20pt, TP: +60pt")
```
