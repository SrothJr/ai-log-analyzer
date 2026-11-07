import re

from .schemas import Finding


KNOWN_TYPES = {
    "brute_force",
    "sql_injection",
    "scanning",
    "path_traversal",
    "unusual_request_rate",
    "unauthorized_access",
}
PLACEHOLDER_TYPES = {"specific_attack_name", "attack_type", "unknown"}

LABEL_ALIASES = {
    "brute force": "brute_force",
    "brute_force_attack": "brute_force",
    "authentication_failure": "brute_force",
    "invalid_credentials_attempt": "brute_force",
    "invalid_password_attempt": "brute_force",
    "sql injection attempt": "sql_injection",
    "sql_injection_attempt": "sql_injection",
    "endpoint_scan": "scanning",
    "endpoint scanning": "scanning",
    "path traversal attempt": "path_traversal",
    "path_traversal_attempt": "path_traversal",
    "dos attack": "unusual_request_rate",
    "denial_of_service": "unusual_request_rate",
    "request_rate_anomaly": "unusual_request_rate",
    "credential theft": "unauthorized_access",
    "credential theft attempt": "unauthorized_access",
    "authentication_success": "unauthorized_access",
}
PLACEHOLDER_TYPES |= {"specific_attack_name_or_other", "http_404_not_found"}


def _normal_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("-", " "))


def canonical_attack_type(finding: Finding) -> str:
    label = _normal_label(finding.attack_type)
    return LABEL_ALIASES.get(label, label.replace(" ", "_"))


def canonicalize_finding(finding: Finding) -> Finding:
    return finding.model_copy(update={"attack_type": canonical_attack_type(finding)})
