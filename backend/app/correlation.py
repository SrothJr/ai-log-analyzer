from collections import defaultdict
import re

from .schemas import Finding, FindingsResponse


SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def merge_findings(findings: list[Finding]) -> list[Finding]:
    grouped: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[(finding.attack_type, finding.actor_id)].append(finding)

    merged: list[Finding] = []
    for group in grouped.values():
        first = group[0]
        evidence_by_line = {}
        for finding in group:
            for item in finding.evidence:
                # Keep the first validated summary, normally the deterministic one.
                evidence_by_line.setdefault(item.line, item)
        severity = max(group, key=lambda item: SEVERITY_RANK[item.severity]).severity
        merged.append(
            Finding(
                attack_type=first.attack_type,
                severity=severity,
                actor_id=first.actor_id,
                evidence=[evidence_by_line[line] for line in sorted(evidence_by_line)],
                reason=_compact(first.reason, 240),
                suggested_action=_compact(first.suggested_action, 180),
            )
        )
    return sorted(merged, key=lambda item: (item.severity, item.attack_type, item.actor_id))


def _compact(value: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def correlation_prompt(findings: list[Finding]) -> str:
    compact = FindingsResponse(findings=findings).model_dump_json(exclude_none=True)
    return f"""Combine these candidate security findings from multiple log chunks.
Merge duplicates, preserve every evidence line, and link related activity only when the evidence supports it.
Do not invent evidence. Do not turn ordinary errors into attacks. Return JSON only in the same findings schema.

CANDIDATE FINDINGS
{compact}
"""
