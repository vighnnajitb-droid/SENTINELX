import csv
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any


def parse_csv_log(file_path: str) -> List[Dict[str, Any]]:
    """Parse CSV log file and return dictionary entries."""
    with open(file_path, mode="r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_json_log(file_path: str) -> List[Dict[str, Any]]:
    """Parse JSON log file and return dictionary entries."""
    with open(file_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "events" in data:
        return data["events"]
    return [data]


def parse_log_file(file_path: str) -> List[Dict[str, Any]]:
    extension = file_path.lower()

    if extension.endswith(".csv"):
        return parse_csv_log(file_path)
    if extension.endswith(".json"):
        return parse_json_log(file_path)

    raise ValueError(f"Unsupported file format for {file_path}")


def generate_event_hash(event: Dict[str, Any]) -> str:
    """Generate a SHA-256 hash of standardized event data."""
    event_str = json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )
    return hashlib.sha256(event_str.encode("utf-8")).hexdigest()


def prepare_security_events(
    raw_events: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Normalize log entries and generate tamper-evident hashes."""
    prepared_events = []

    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            raise ValueError("Every log event must be a JSON object or CSV row.")

        raw_data = dict(raw_event)

        # Preserve the original timestamp, or generate and store one.
        if raw_data.get("timestamp") is None:
            raw_data["timestamp"] = datetime.utcnow().isoformat()

        event = {
            "source_ip": raw_data.get("source_ip") or "",
            "destination_ip": raw_data.get("destination_ip") or "",
            "event_type": raw_data.get("event_type") or raw_data.get("type") or "unknown",
            "timestamp": raw_data["timestamp"],
            "raw_data": raw_data
        }

        event["event_hash"] = generate_event_hash(event)
        prepared_events.append(event)

    return prepared_events

