"""Small session event log for WaveTone CLI runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import now_iso


def append_event(session_path: str | Path, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = Path(session_path).expanduser().resolve()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": "wavetone-session/v1", "events": []}
    record = {"time": now_iso(), "event": event, "payload": payload}
    data.setdefault("events", []).append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def load_events(session_path: str | Path) -> list[dict[str, Any]]:
    path = Path(session_path).expanduser().resolve()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("events", []))
