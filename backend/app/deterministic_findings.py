from collections import defaultdict
from datetime import datetime, timezone

from .detector import Observation
from .schemas import EvidenceItem, Finding


SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def _evidence(items: list[Observation]) -> list[EvidenceItem]:
    return [EvidenceItem(line=item.line, summary=item.summary) for item in items]


def build_findings(observations: list[Observation]) -> list[Finding]:
    by_actor_type: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for observation in observations:
        if observation.actor_id:
            by_actor_type[(observation.actor_id, observation.event_type)].append(observation)

    findings: list[Finding] = []
    for (actor, event_type), items in by_actor_type.items():
        if event_type == "authentication_failure" and len(items) >= 3:
            findings.append(
                Finding(
                    attack_type="brute_force",
                    severity="High" if len(items) >= 8 else "Medium",
                    actor_id=actor,
                    evidence=_evidence(items),
                    reason=f"{len(items)} failed authentication attempts were observed from one actor.",
                    suggested_action="Investigate the account and apply login rate limiting.",
                )
            )
        elif event_type == "sql_injection_attempt":
            findings.append(
                Finding(
                    attack_type="sql_injection",
                    severity="High",
                    actor_id=actor,
                    evidence=_evidence(items),
                    reason="The requests contain SQL injection syntax and were rejected by the application.",
                    suggested_action="Block or rate-limit the source and review query validation and database logs.",
                )
            )
        elif event_type == "endpoint_scan" and len(items) >= 3:
            findings.append(
                Finding(
                    attack_type="scanning",
                    severity="Medium",
                    actor_id=actor,
                    evidence=_evidence(items),
                    reason=f"{len(items)} sensitive endpoint probes were observed from one actor.",
                    suggested_action="Investigate the source and restrict exposure of administrative endpoints.",
                )
            )
        elif event_type == "path_traversal_attempt":
            findings.append(
                Finding(
                    attack_type="path_traversal",
                    severity="High",
                    actor_id=actor,
                    evidence=_evidence(items),
                    reason="The requests contain encoded path traversal sequences targeting a file endpoint.",
                    suggested_action="Block the source and verify file path canonicalization and access controls.",
                )
            )
        elif event_type == "request_rate_anomaly":
            findings.append(
                Finding(
                    attack_type="unusual_request_rate",
                    severity="Medium",
                    actor_id=actor,
                    evidence=_evidence(items),
                    reason="The actor exceeded the request-rate threshold and received rate-limit responses.",
                    suggested_action="Apply rate limiting and investigate the client behavior.",
                )
            )

    failures = defaultdict(list)
    successes = defaultdict(list)
    admin_activity = defaultdict(list)
    for observation in observations:
        if not observation.actor_id:
            continue
        if observation.event_type == "authentication_failure":
            failures[observation.actor_id].append(observation)
        elif observation.event_type == "authentication_success":
            successes[observation.actor_id].append(observation)
        elif observation.event_type == "administrative_activity":
            admin_activity[observation.actor_id].append(observation)

    for actor, success_items in successes.items():
        success = min(
            success_items,
            key=lambda item: item.timestamp or datetime.max.replace(tzinfo=timezone.utc),
        )
        prior_failures = [
            item
            for item in failures[actor]
            if item.timestamp and success.timestamp and item.timestamp <= success.timestamp
        ]
        if len(prior_failures) >= 3:
            related_admin = [
                item
                for item in admin_activity[actor]
                if item.timestamp and success.timestamp and item.timestamp >= success.timestamp
                and (
                    not success.attributes.get("session_id")
                    or item.attributes.get("session_id") == success.attributes.get("session_id")
                )
            ]
            related = prior_failures + success_items + related_admin
            findings.append(
                Finding(
                    attack_type="unauthorized_access",
                    severity="Critical" if admin_activity[actor] else "High",
                    actor_id=actor,
                    evidence=_evidence(related),
                    reason="Repeated failed logins were followed by successful authentication and related activity.",
                    suggested_action="Revoke the session, investigate the account, and review administrative actions.",
                )
            )

    return findings
