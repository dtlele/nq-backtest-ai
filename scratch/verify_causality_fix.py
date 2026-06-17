"""
Test di verifica del fix causality per step_trade.
Scenario: Trade LONG aperto sulla candela M5 16:00 UTC del 4 Feb 2025.
  - Low=21,634.25 tocca lo stop 21,634.75 (avvenuto PRIMA dell'entrata reale)
  - Close=21,676 recupera ampiamente sopra lo stop
  - High=21,680 raggiunge il target 21,680
Atteso CON FIX: target hit (non stop)
Atteso SENZA FIX: stop hit (falso positivo)
"""
from datetime import datetime, timezone
import sys
sys.path.insert(0, '.')
from src import Bar
from src.trade_simulator import step_trade

ts = datetime(2025, 2, 4, 16, 0, tzinfo=timezone.utc)

# La candela M5 problematica
problem_bar = Bar(
    timestamp=ts,
    open=21656.0, high=21680.0, low=21634.25, close=21676.0,
    volume=1000, buy_volume=600, sell_volume=400,
    delta=200, delta_pct=0.2, cvd=200, vwap=21660.0,
    big_trades=[]
)

class FakeConsensus:
    direction = 'long'
    entry = 21656.0
    stop = 21634.75
    target = 21680.0
    r_ratio = 1.2
    final_confidence = 80
    class fabio:
        setup_type = 'test'
        reasoning = 'test'
    class andrea:
        structural_stop = None
        reasoning = 'test'

class FakeTrade:
    direction = 'long'
    entry = 21656.0
    stop = 21634.75
    target = 21680.0
    contracts = 10
    consensus = FakeConsensus()
    entry_bar = problem_bar

trade = FakeTrade()

print("=== TEST FIX CAUSALITY ===")
print(f"Trade LONG: entry={trade.entry} stop={trade.stop} target={trade.target}")
print(f"Bar M5:     O={problem_bar.open} H={problem_bar.high} L={problem_bar.low} C={problem_bar.close}")
print(f"  low ({problem_bar.low}) <= stop ({trade.stop}): {problem_bar.low <= trade.stop}  <- il low tocca lo stop")
print(f"  close ({problem_bar.close}) > stop ({trade.stop}): {problem_bar.close > trade.stop}  <- ma il close si e' recuperato")
print(f"  high ({problem_bar.high}) >= target ({trade.target}): {problem_bar.high >= trade.target}  <- l'high tocca il target")
print()

# SENZA FIX (comportamento vecchio: first_bar_after_entry=False)
result_no_fix = step_trade(trade, [problem_bar], first_bar_after_entry=False)
# CON FIX (causality check attivo: first_bar_after_entry=True)
result_with_fix = step_trade(trade, [problem_bar], first_bar_after_entry=True)

no_fix_reason = result_no_fix.exit_reason if result_no_fix else "No exit"
with_fix_reason = result_with_fix.exit_reason if result_with_fix else "No exit"

print(f"SENZA FIX -> {no_fix_reason}")
print(f"CON FIX   -> {with_fix_reason}")
print()

# Assertions
assert no_fix_reason == 'stop', f"Bug non riprodotto: atteso stop, ottenuto {no_fix_reason}"
print("✅ Bug confermato: senza fix = STOP FALSO sulla candela M5")

assert with_fix_reason == 'target', f"Fix non funzionante: atteso target, ottenuto {with_fix_reason}"
print("✅ Fix OK: con fix = TARGET HIT correttamente")

print()
print("=== TEST 2: Barra successiva (no causality check) ===")
# Su una barra successiva (non la prima) il comportamento normale torna attivo
ts2 = datetime(2025, 2, 4, 16, 5, tzinfo=timezone.utc)
real_stop_bar = Bar(
    timestamp=ts2,
    open=21656.0, high=21660.0, low=21630.0, close=21632.0,
    volume=500, buy_volume=100, sell_volume=400,
    delta=-300, delta_pct=-0.6, cvd=-100, vwap=21640.0,
    big_trades=[]
)
result_real_stop = step_trade(trade, [problem_bar, real_stop_bar], first_bar_after_entry=True)
real_stop_reason = result_real_stop.exit_reason if result_real_stop else "No exit"
print(f"Barra 2 con close={real_stop_bar.close} sotto stop -> {real_stop_reason}")
assert real_stop_reason == 'target', f"Atteso target dalla barra 1, ottenuto {real_stop_reason}"
print("✅ Barra 1 colpisce target prima che la barra 2 possa fermarci")
print()
print("TUTTI I TEST PASSATI ✅")
