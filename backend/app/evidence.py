import json
from pathlib import Path
from typing import Any

from .schemas import Finding


class EvidenceValidationError(ValueError):
    """Raised when finding evidence is not supported by the original source line."""


def source_entries(path: str | Path) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            entries[line_number] = value
    return entries


def validate_finding_against_source(finding: Finding, path: str | Path) -> Finding:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for item in finding.evidence:
        if item.line < 1 or item.line > len(lines):
            raise EvidenceValidationError(f"Evidence line {item.line} is outside the source file")
        try:
            entry = json.loads(lines[item.line - 1])
        except json.JSONDecodeError as exc:
            raise EvidenceValidationError(f"Evidence line {item.line} is not valid JSON") from exc
        if not isinstance(entry, dict):
            raise EvidenceValidationError(f"Evidence line {item.line} is not a log object")
        actor = entry.get("client_ip")
        if actor != finding.actor_id:
            raise EvidenceValidationError(
                f"Evidence line {item.line} actor {actor!r} does not match {finding.actor_id!r}"
            )
    return finding


KNOWN_EVENT_TYPES = {
    "brute_force": {"authentication_failure"},
    "sql_injection": {"sql_injection_attempt"},
    "scanning": {"endpoint_scan"},
    "path_traversal": {"path_traversal_attempt"},
    "unusual_request_rate": {"request_rate_anomaly"},
    "unauthorized_access": {"authentication_success", "administrative_activity"},
}


def validate_known_finding_evidence(
    finding: Finding,
    observation_lines: dict[int, set[str]],
) -> Finding:
    expected_types = KNOWN_EVENT_TYPES.get(finding.attack_type)
    if expected_types is None:
        return finding
    for item in finding.evidence:
        if not observation_lines.get(item.line, set()) & expected_types:
            raise EvidenceValidationError(
                f"Evidence line {item.line} does not support {finding.attack_type}"
            )
    return finding


def validate_novel_finding_evidence(
    finding: Finding,
    path: str | Path,
    observation_lines: dict[int, set[str]],
) -> Finding:
    """Reject novel claims supported only by ordinary traffic."""
    entries = source_entries(path)
    for item in finding.evidence:
        if item.line in observation_lines:
            continue
        entry = entries.get(item.line, {})
        status = entry.get("status")
        path_value = str(entry.get("path") or "").lower()
        message = str(entry.get("message") or "").lower()
        suspicious_path = any(
            marker in path_value
            for marker in ("..", ".env", ".git", "admin", "wp-", "phpmyadmin", "select", "union")
        )
        suspicious_status = isinstance(status, int) and status in {401, 403, 422, 429, 500, 502}
        suspicious_message = any(marker in message for marker in ("attack", "probe", "blocked", "denied"))
        if not (suspicious_path or suspicious_status or suspicious_message):
            raise EvidenceValidationError(
                f"Novel finding evidence line {item.line} has no security signal"
            )
    return finding
