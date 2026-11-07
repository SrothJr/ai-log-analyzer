from app.normalization import PLACEHOLDER_TYPES, canonical_attack_type, canonicalize_finding
from app.schemas import EvidenceItem, Finding


def make_finding(label: str) -> Finding:
    return Finding(
        attack_type=label,
        severity="High",
        actor_id="192.0.2.1",
        evidence=[EvidenceItem(line=1, summary="evidence")],
        reason="reason",
        suggested_action="action",
    )


def test_model_aliases_map_to_canonical_types() -> None:
    assert canonical_attack_type(make_finding("brute_force_attack")) == "brute_force"
    assert canonical_attack_type(make_finding("DoS attack")) == "unusual_request_rate"
    assert canonicalize_finding(make_finding("endpoint_scan")).attack_type == "scanning"


def test_unknown_attack_types_are_preserved() -> None:
    assert canonical_attack_type(make_finding("JWT algorithm confusion")) == "jwt_algorithm_confusion"


def test_prompt_placeholder_labels_are_not_reportable_categories() -> None:
    assert "specific_attack_name" in PLACEHOLDER_TYPES
