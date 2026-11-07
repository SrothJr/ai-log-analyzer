import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote


AUTH_PATH = "/auth/login"
SENSITIVE_PATHS = (
    "/.env",
    "/.git/",
    "/wp-admin",
    "/phpmyadmin",
    "/actuator/env",
    "/server-status",
    "/backup.sql",
    "/config.json",
)
SQL_PATTERN = re.compile(
    r"(?:\bunion\s+select\b|\bor\s+\d+\s*=\s*\d+\b|\bselect\s+sleep\s*\(|;\s*select\b|--)",
    re.IGNORECASE,
)
TRAVERSAL_PATTERN = re.compile(r"(?:\.\./|%2e%2e(?:%2f|/)|\.\\)", re.IGNORECASE)
PROMPT_INJECTION_PATTERN = re.compile(
    r"ignore\s+(?:all\s+)?previous\s+instructions|remove\s+.*evidence",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Observation:
    line: int
    timestamp: datetime | None
    actor_id: str | None
    event_type: str
    summary: str
    attributes: dict[str, Any] = field(default_factory=dict)


def _decode(value: Any) -> str:
    return unquote(unquote(str(value or "")))


def _load(line: str) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _timestamp(entry: dict[str, Any]) -> datetime | None:
    value = entry.get("time")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def detect_observations(path: str | Path) -> list[Observation]:
    observations: list[Observation] = []
    with Path(path).open("r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            entry = _load(raw_line)
            if not entry:
                continue
            timestamp = _timestamp(entry)
            actor = entry.get("client_ip")
            actor_id = actor if isinstance(actor, str) and actor else None
            method = str(entry.get("method") or "").upper()
            path_value = _decode(entry.get("path"))
            auth_result = str(entry.get("auth_result") or "").lower()
            status = entry.get("status")

            if method == "POST" and AUTH_PATH in path_value and (
                status == 401 or auth_result in {"invalid_password", "failure", "failed"}
            ) and actor_id:
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "authentication_failure",
                        "Failed authentication for the login endpoint.",
                        {"username": entry.get("username"), "status": status},
                    )
                )

            if method == "POST" and AUTH_PATH in path_value and (
                status == 200 or auth_result in {"success", "successful"}
            ) and actor_id:
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "authentication_success",
                        "Successful authentication for the login endpoint.",
                        {"username": entry.get("username"), "session_id": entry.get("session_id")},
                    )
                )

            if (
                actor_id
                and entry.get("session_id")
                and isinstance(status, int)
                and 200 <= status < 300
                and ("/admin/" in path_value.lower() or "/export" in path_value.lower())
            ):
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "administrative_activity",
                        "Authenticated actor accessed an administrative or export endpoint.",
                        {"path": path_value, "status": status, "session_id": entry.get("session_id")},
                    )
                )

            decoded_path = _decode(path_value)
            if actor_id and SQL_PATTERN.search(decoded_path):
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "sql_injection_attempt",
                        "Request contains SQL injection syntax in its path or query.",
                        {"path": path_value, "status": status},
                    )
                )

            if actor_id and any(marker in decoded_path.lower() for marker in SENSITIVE_PATHS):
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "endpoint_scan",
                        "Request probes a sensitive or commonly exposed endpoint.",
                        {"path": path_value, "status": status},
                    )
                )

            if actor_id and TRAVERSAL_PATTERN.search(path_value):
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "path_traversal_attempt",
                        "Request contains a path traversal sequence.",
                        {"path": path_value, "status": status},
                    )
                )

            requests_in_window = entry.get("requests_in_window")
            if actor_id and isinstance(requests_in_window, (int, float)) and requests_in_window >= 100:
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "request_rate_anomaly",
                        "Request rate exceeds the deterministic anomaly threshold.",
                        {
                            "requests_in_window": requests_in_window,
                            "window_seconds": entry.get("window_seconds"),
                            "status": status,
                        },
                    )
                )

            submitted_text = str(entry.get("submitted_text") or "")
            if submitted_text and PROMPT_INJECTION_PATTERN.search(submitted_text):
                observations.append(
                    Observation(
                        line_number,
                        timestamp,
                        actor_id,
                        "prompt_injection_payload",
                        "Log field contains an instruction-like payload; it is treated as data only.",
                        {"field": "submitted_text"},
                    )
                )
    return observations
