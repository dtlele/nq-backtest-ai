import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.gex_manager import load_gex_for_date
from src import VolumeProfile

def test_load_gex_fallback_no_data():
    # Test fallback with overnight volume profile POC
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0)
    metrics = load_gex_for_date("20250430", overnight_vp=vp, opening_price=20010.0)
    
    assert metrics["gex_regime"] == "positive"  # opening price 20010 >= POC 20000
    assert metrics["zero_gamma_level"] == 20000.0
    assert metrics["call_wall"] == 20150.0
    assert metrics["put_wall"] == 19850.0

def test_load_gex_fallback_negative_regime():
    # Test negative regime estimation
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0)
    metrics = load_gex_for_date("2025-04-30", overnight_vp=vp, opening_price=19990.0)
    
    assert metrics["gex_regime"] == "negative"  # opening price 19990 < POC 20000
    assert metrics["zero_gamma_level"] == 20000.0

def test_load_gex_from_file(tmp_path):
    mock_gex_content = {
        "2025-04-30": {
            "gex_regime": "negative",
            "zero_gamma_level": 19950.0,
            "call_wall": 20100.0,
            "put_wall": 19800.0
        }
    }
    
    # Patch GEX_DATA_FILE path in gex_manager to point to our temp file
    mock_file = tmp_path / "gex_data.json"
    with open(mock_file, "w", encoding="utf-8") as f:
        json.dump(mock_gex_content, f)
        
    with patch("src.gex_manager.GEX_DATA_FILE", mock_file):
        metrics = load_gex_for_date("20250430")
        
    assert metrics["gex_regime"] == "negative"
    assert metrics["zero_gamma_level"] == 19950.0
    assert metrics["call_wall"] == 20100.0
    assert metrics["put_wall"] == 19800.0
