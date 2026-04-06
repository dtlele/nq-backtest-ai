import pytest, textwrap, tempfile, os
from src.data_loader import load_day, list_data_files
from pathlib import Path

SAMPLE_CSV = textwrap.dedent("""\
    ts_recv,ts_event,rtype,publisher_id,instrument_id,action,side,depth,price,size,flags,ts_in_delta,sequence,symbol
    2025-04-30T13:30:05.000000000Z,2025-04-30T13:30:05.000000000Z,0,1,1,T,A,0,20000.000000000,5,0,1000,1,NQM5
    2025-04-30T13:30:10.000000000Z,2025-04-30T13:30:10.000000000Z,0,1,1,T,B,0,19999.750000000,10,0,1000,2,NQM5
    2025-04-30T13:30:15.000000000Z,2025-04-30T13:30:15.000000000Z,0,1,1,T,A,0,20000.000000000,35,0,1000,3,NQM5
    2025-04-30T13:30:20.000000000Z,2025-04-30T13:30:20.000000000Z,0,1,1,A,A,0,20000.000000000,5,0,1000,4,NQM5
""")

def _write_csv(content: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False)
    f.write(content); f.close()
    return f.name

def test_load_day_parses_trades():
    path = _write_csv(SAMPLE_CSV)
    trades = load_day(path)
    os.unlink(path)
    assert len(trades) == 3  # action='A' row skipped
    assert trades[0].side == 'A'
    assert trades[0].price == pytest.approx(20000.0)
    assert trades[0].size == 5
    assert trades[1].side == 'B'
    assert trades[1].price == pytest.approx(19999.75)
    assert trades[2].size == 35

def test_load_day_returns_empty_for_no_trade_actions():
    # CSV with only action='A' rows (add, not trade)
    csv_no_trades = textwrap.dedent("""\
        ts_recv,ts_event,rtype,publisher_id,instrument_id,action,side,depth,price,size,flags,ts_in_delta,sequence,symbol
        2025-04-30T13:30:05.000000000Z,2025-04-30T13:30:05.000000000Z,0,1,1,A,A,0,20000.000000000,5,0,1000,1,NQM5
        2025-04-30T13:30:10.000000000Z,2025-04-30T13:30:10.000000000Z,0,1,1,C,B,0,19999.750000000,10,0,1000,2,NQM5
    """)
    path = _write_csv(csv_no_trades)
    trades = load_day(path)
    os.unlink(path)
    assert trades == []

def test_load_day_timestamp_is_utc_datetime():
    path = _write_csv(SAMPLE_CSV)
    trades = load_day(path)
    os.unlink(path)
    from datetime import timezone
    assert trades[0].ts_event.tzinfo == timezone.utc
    assert trades[0].ts_event.hour == 13  # 13:30:05 UTC

def test_list_data_files():
    with tempfile.TemporaryDirectory() as d:
        Path(d, 'glbx-mdp3-20250401.trades.csv').touch()
        Path(d, 'glbx-mdp3-20250402.trades.csv').touch()
        Path(d, 'other.txt').touch()
        files = list_data_files(d)
        assert len(files) == 2
        assert all(f.endswith('.trades.csv') for f in files)
