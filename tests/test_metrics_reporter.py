import pytest
from datetime import datetime, timezone
from src import ClosedTrade
from src.metrics_reporter import compute_metrics

def _trade(pnl_usd, setup='squeeze', conf=75):
    sign = 1 if pnl_usd >= 0 else -1
    exit_p = 20000 + sign * abs(pnl_usd) / 5  # rough
    return ClosedTrade(
        'long', 20000.0, 19990.0, 20020.0, exit_p,
        'target' if pnl_usd > 0 else 'stop',
        pnl_usd/5, pnl_usd,
        datetime(2025,4,30,9,45,tzinfo=timezone.utc),
        datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
        'fabio reasoning', 'andrea reasoning', setup, conf, 2.0
    )

def test_win_rate():
    trades = [_trade(500), _trade(500), _trade(-250)]
    m = compute_metrics(trades)
    assert m['win_rate'] == pytest.approx(2/3)

def test_profit_factor():
    trades = [_trade(500), _trade(500), _trade(-250)]
    m = compute_metrics(trades)
    assert m['profit_factor'] == pytest.approx(1000/250)

def test_empty_trades():
    m = compute_metrics([])
    assert m['total_trades'] == 0
