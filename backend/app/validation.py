import json
import re
from typing import Any

from pydantic import ValidationError

from .schemas import FindingsResponse


class ModelResponseError(ValueError):
    """Raised when a model response cannot be converted to valid findings."""


def extract_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ModelResponseError("Model response does not contain a JSON object") from None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ModelResponseError("Model response contains invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise ModelResponseError("Model response JSON must be an object")
    return parsed


def validate_findings(
    content: str,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
) -> FindingsResponse:
    payload = extract_json_object(content)
    try:
        response = FindingsResponse.model_validate(payload)
    except ValidationError as exc:
        raise ModelResponseError("Model response does not match the findings schema") from exc

    if start_line is not None and end_line is not None:
        for finding in response.findings:
            for evidence in finding.evidence:
                if not start_line <= evidence.line <= end_line:
                    raise ModelResponseError(
                        f"Evidence line {evidence.line} is outside chunk range "
                        f"{start_line}-{end_line}"
                    )
    return response
