import pytest
from datetime import datetime, timezone
from src import Trade, NQ_BIG_TRADE_THRESHOLD
from src.bar_aggregator import aggregate_to_bars

def _t(hms: str, side: str, price: float, size: int) -> Trade:
    dt = datetime.strptime(f"2025-04-30 {hms}", "%Y-%m-%d %H:%M:%S")
    return Trade(ts_event=dt.replace(tzinfo=timezone.utc), side=side,
                 price=price, size=size)

def test_single_bar_ohlcv():
    trades = [
        _t("13:30:05", 'A', 20000.00, 10),
        _t("13:30:30", 'B', 19999.75, 20),
        _t("13:30:55", 'A', 20000.25, 5),
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 1
    b = bars[0]
    assert b.open  == pytest.approx(20000.00)
    assert b.high  == pytest.approx(20000.25)
    assert b.low   == pytest.approx(19999.75)
    assert b.close == pytest.approx(20000.25)
    assert b.volume == 35
    assert b.buy_volume == 15
    assert b.sell_volume == 20
    assert b.delta == -5
    assert b.delta_pct == pytest.approx(abs(-5) / 35 * 100)

def test_cvd_accumulates():
    trades = [
        _t("13:30:05", 'A', 20000.0, 30),  # bar1: delta +30
        _t("13:31:05", 'B', 20000.0, 10),  # bar2: delta -10
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 2
    assert bars[0].cvd == 30
    assert bars[1].cvd == 20

def test_big_trades_captured():
    trades = [
        _t("13:30:05", 'A', 20000.0, 29),   # not big
        _t("13:30:10", 'B', 20000.0, 30),   # threshold
        _t("13:30:15", 'A', 20000.0, 100),  # big
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    big = bars[0].big_trades
    assert len(big) == 2
    assert all(t.size >= NQ_BIG_TRADE_THRESHOLD for t in big)

def test_vwap():
    trades = [
        _t("13:30:05", 'A', 100.0, 10),
        _t("13:30:10", 'A', 200.0, 10),
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert bars[0].vwap == pytest.approx(150.0)

def test_empty_returns_empty():
    assert aggregate_to_bars([], freq='1min') == []
