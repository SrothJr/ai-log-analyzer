from app.correlation import merge_findings
from app.schemas import EvidenceItem, Finding


def finding(line: int, severity: str = "Low") -> Finding:
    return Finding(
        attack_type="scanning",
        severity=severity,  # type: ignore[arg-type]
        actor_id="203.0.113.90",
        evidence=[EvidenceItem(line=line, summary=f"probe {line}")],
        reason=f"reason {line}",
        suggested_action="Investigate the source",
    )


def test_merge_findings_deduplicates_actor_and_attack_type() -> None:
    merged = merge_findings([finding(10), finding(20, "High"), finding(10)])

    assert len(merged) == 1
    assert merged[0].severity == "High"
    assert [item.line for item in merged[0].evidence] == [10, 20]
