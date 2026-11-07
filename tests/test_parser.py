import json
import pytest

from utils.parser import parse_log_file, prepare_security_events, generate_event_hash


def test_parse_csv():
    events = parse_log_file("sample_data/normal_activity.csv")
    assert len(events) == 5
    assert events[0]["source_ip"] == "192.168.1.10"


def test_parse_json(tmp_path):
    data = [{"source_ip": "1.1.1.1", "event_type": "login"}]
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    events = parse_log_file(str(p))
    assert len(events) == 1
    assert events[0]["source_ip"] == "1.1.1.1"


def test_prepare_security_events():
    raw = [{"source_ip": "1.1.1.1", "type": "login"}]
    prepared = prepare_security_events(raw)

    assert len(prepared) == 1
    assert prepared[0]["event_type"] == "login"
    assert "event_hash" in prepared[0]


def test_none_fields_are_normalized():
    raw = [{
        "source_ip": None,
        "destination_ip": None,
        "event_type": None,
        "type": "login"
    }]

    event = prepare_security_events(raw)[0]

    assert event["source_ip"] == ""
    assert event["destination_ip"] == ""
    assert event["event_type"] == "login"

    payload = {key: event[key] for key in (
        "source_ip", "destination_ip", "event_type", "timestamp", "raw_data"
    )}
    assert generate_event_hash(payload) == event["event_hash"]


def test_parse_invalid_file():
    with pytest.raises(ValueError):
        parse_log_file("sample_data/invalid_file.txt")
