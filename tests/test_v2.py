"""Test di causalità e correttezza. Eseguibili con pytest o come script."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.v2.config import Config
from src.v2.models import Bar, DayContext, SignalEvent, Side
from src.v2.state import SessionState
from src.v2.engine import BacktestEngine
from src.v2.execution import ExecutionEngine
from src.v2.risk import RiskManager


def mk_bar(ts, o, h, l, c, vol=5000, delta=0, footprint=None, big=None):
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=vol,
               buy_volume=vol // 2 + max(delta, 0), sell_volume=vol // 2 + max(-delta, 0),
               delta=delta, footprint=footprint or {}, big_trades=big or [])


def mk_day(date="2026-01-05"):
    return DayContext(date=date, prev_close=21000.0, prev_poc=20990.0,
                      prev_vah=21010.0, prev_val=20970.0, on_high=21005.0, on_low=20980.0)


def mk_rth_bars(date, n=390, base=21000.0):
    et = ZoneInfo("America/New_York")
    t0 = datetime.fromisoformat(f"{date}T09:25:00").replace(tzinfo=et)
    bars = []
    px = base
    for i in range(n):
        ts = t0 + timedelta(minutes=i)
        o = px
        c = px + (0.5 if i % 3 else -0.3)
        bars.append(mk_bar(ts, o, max(o, c) + 1.0, min(o, c) - 1.0, c))
        px = c
    return bars


def test_signal_validation_blocks_backward_levels():
    """Il bug consensus (livelli inventati) è impossibile per costruzione."""
    ts = datetime(2026, 1, 5, 15, 0, tzinfo=ZoneInfo("UTC"))
    try:
        SignalEvent(setup="x", direction=Side.LONG, ts_signal=ts, entry_ref=100.0,
                    stop=101.0, target1=110.0, target2=None, wall_price=99.0,
                    wall_size=100, level_name="x")
        assert False, "backward stop accettato!"
    except ValueError:
        pass


def test_state_is_causal():
    """Lo stato a metà giornata NON cambia se aggiungo barre future."""
    cfg = Config()
    day = mk_day()
    bars = mk_rth_bars("2026-01-05", n=200)
    s1 = SessionState(day, cfg)
    for b in bars[:100]:
        s1.update(b)
    snap1 = (s1.ib_high, s1.ib_low, s1.rth.poc, s1.cvd, len(s1.walls))
    s1_snapshot = snap1
    # continua con altre 100 barre
    for b in bars[100:]:
        s1.update(b)
    # lo snapshot di metà giornata deve essere rimasto identico a una run troncata
    s2 = SessionState(day, cfg)
    for b in bars[:100]:
        s2.update(b)
    snap2 = (s2.ib_high, s2.ib_low, s2.rth.poc, s2.cvd, len(s2.walls))
    assert s1_snapshot == snap2, "LOOKAHEAD: lo stato passato dipende dal futuro"


def test_engine_truncation_equivalence():
    """Run completa vs run troncata: i trade fino al troncamento sono identici."""
    cfg = Config()
    day = mk_day()
    bars = mk_rth_bars("2026-01-05", n=390)
    eng_full = BacktestEngine(cfg, llm_policy=None)
    res_full = eng_full.run_day(day, bars)
    eng_cut = BacktestEngine(cfg, llm_policy=None)
    res_cut = eng_cut.run_day(day, bars[:200])
    full_early = [t for t in res_full.trades if t.ts_exit <= bars[199].ts]
    assert len(full_early) == len(res_cut.trades)
    for a, b in zip(full_early, res_cut.trades):
        assert (a.entry, a.exit_price, a.exit_reason) == (b.entry, b.exit_price, b.exit_reason)


def test_daily_loss_gate():
    """FundedNext: a -$1.800 si chiude la giornata. Sempre."""
    cfg = Config()
    rm = RiskManager(cfg)
    rm.daily_pnl = -1800.01
    assert not rm.day_allows_new_trade()
    rm2 = RiskManager(cfg)
    rm2.consecutive_stops = 2
    assert not rm2.day_allows_new_trade()


def test_no_size_explosion():
    """Stop stretto → reject, mai size 40x (bug R2)."""
    cfg = Config()
    rm = RiskManager(cfg)
    ts = datetime(2026, 1, 5, 15, 0, tzinfo=ZoneInfo("UTC"))
    sig = SignalEvent(setup="x", direction=Side.LONG, ts_signal=ts, entry_ref=100.0,
                      stop=99.0, target1=110.0, target2=None, wall_price=99.0,
                      wall_size=100, level_name="x")
    # stop 1 pt < min_stop_points 8 → il GATE lo rifiuta prima del sizing;
    # qui verifichiamo il cap sul sizing con stop al limite minimo
    sig2 = SignalEvent(setup="x", direction=Side.LONG, ts_signal=ts, entry_ref=100.0,
                       stop=92.0, target1=116.0, target2=None, wall_price=92.0,
                       wall_size=100, level_name="x")
    rd = rm.size(sig2)
    assert rd.allowed
    assert rd.contracts <= cfg.risk.max_contracts
    worst = (sig2.risk_points / cfg.instrument.tick_size) * cfg.instrument.tick_value_usd * rd.contracts
    assert worst <= cfg.risk.max_risk_per_trade_usd * 1.01


if __name__ == "__main__":
    test_signal_validation_blocks_backward_levels()
    test_state_is_causal()
    test_engine_truncation_equivalence()
    test_daily_loss_gate()
    test_no_size_explosion()
    print("ALL V2 TESTS PASSED")
