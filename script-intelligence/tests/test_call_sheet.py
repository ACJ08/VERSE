"""
VERSE Test Suite - Production Call Sheet Parser Tests.
"""

from app.parsers.call_sheet_parser import parse_call_sheet, parse_call_sheet_to_model


def test_parse_call_sheet(sample_call_sheet_text):
    data = parse_call_sheet(sample_call_sheet_text)
    assert data["production"] == "VERSE Season 1"
    assert data["date"] == "2026-07-28"
    assert data["director"] == "Jane Doe"
    assert data["location"] == "Studio 4 - Main Stage"
    assert data["shooting_time"] == "07:00 AM"
    assert "1" in data["scenes"]
    assert "2A" in data["scenes"]
    assert any("SARAH" in cast for cast in data["cast"])
    assert any("Script Supervisor" in crew for crew in data["crew"])


def test_parse_call_sheet_model(sample_call_sheet_text):
    model = parse_call_sheet_to_model(sample_call_sheet_text)
    assert model.production == "VERSE Season 1"
    assert len(model.scenes) == 2
