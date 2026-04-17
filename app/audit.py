"""
SIEM audit event emitter.

Every function here writes one structured JSON line via the ``guardrail.audit``
logger.  The caller never touches raw logging calls — this module owns the
audit log schema so field names stay consistent across events.

Privacy contract
----------------
* PII text is NEVER logged — not the input, not the anonymized output.
* ``text_length`` (character count) is safe and helps with capacity planning.
* ``entity_summary`` contains only entity-type names, counts, and max scores —
  never the actual matched strings (passport numbers, phone numbers, etc.).

SIEM field reference  →  see README §Logging
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from app.context import RequestContext

_logger = logging.getLogger("guardrail.audit")

SERVICE = "guardrail"
VERSION = "1.0.0"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ctx_fields(ctx: Optional[RequestContext]) -> dict[str, Any]:
    """Flatten RequestContext into a flat dict of audit fields."""
    if ctx is None:
        return {}

    fields: dict[str, Any] = {
        "request_id": ctx.request_id,
        "client_ip": ctx.client_ip,
        "user_agent": ctx.user_agent,
        "source": ctx.source,
    }

    # User / session identity — present only when provided by the caller
    optional_mappings = {
        "user_id":       ctx.litellm_user_id,
        "team_id":       ctx.litellm_team_id,
        "org_id":        ctx.litellm_org_id,
        "litellm_call_id": ctx.litellm_call_id,
        "litellm_model": ctx.litellm_model,
        "litellm_key_hash": ctx.litellm_key_hash,
        "api_key_id":    ctx.api_key_id,
    }
    for field_name, value in optional_mappings.items():
        if value is not None:
            fields[field_name] = value

    return fields


def summarize_entities(results: list) -> list[dict]:
    """
    Build a privacy-safe summary of Presidio RecognizerResult objects.

    Returns a list sorted by entity type, e.g.:
        [{"type": "UKRAINIAN_PASSPORT", "count": 1, "score_max": 0.85},
         {"type": "UKRAINIAN_PHONE",    "count": 2, "score_max": 0.9}]
    """
    buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "score_max": 0.0})
    for r in results:
        b = buckets[r.entity_type]
        b["count"] += 1
        b["score_max"] = max(b["score_max"], r.score)
    return [
        {
            "type": entity_type,
            "count": b["count"],
            "score_max": round(b["score_max"], 4),
        }
        for entity_type, b in sorted(buckets.items())
    ]


def _emit(event_type: str, severity: str, message: str, **extra: Any) -> None:
    """Core emitter — builds the envelope and hands off to the logger."""
    record_extra: dict[str, Any] = {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "log_type":       "AUDIT",          # SIEM filter field
        "severity":       severity,
        "service":        SERVICE,
        "service_version": VERSION,
        **extra,
    }
    _logger.info(message, extra=record_extra)


# ── Public API ────────────────────────────────────────────────────────────────


def emit_request_received(
    ctx: Optional[RequestContext],
    *,
    method: str,
    path: str,
) -> None:
    """Fired by middleware as soon as a request arrives."""
    _emit(
        event_type="REQUEST_RECEIVED",
        severity="INFO",
        message=f"Incoming {method} {path}",
        **_ctx_fields(ctx),
        http_method=method,
        http_path=path,
    )


def emit_pii_analyzed(
    ctx: Optional[RequestContext],
    *,
    language: str,
    text_length: int,
    score_threshold: float,
    pii_detected: bool,
    total_entities: int,
    entity_summary: list[dict],
    duration_ms: float,
) -> None:
    """
    Fired after ``/analyze`` completes successfully.

    Severity is WARN when PII is present (important for SIEM alert rules),
    INFO when the text is clean.
    """
    severity = "WARN" if pii_detected else "INFO"
    entity_types = [e["type"] for e in entity_summary]
    message = (
        f"PII detected: {total_entities} entities ({', '.join(entity_types)})"
        if pii_detected
        else f"No PII detected in {text_length}-char {language} text"
    )
    _emit(
        event_type="PII_ANALYZED",
        severity=severity,
        message=message,
        **_ctx_fields(ctx),
        language=language,
        text_length=text_length,
        score_threshold=score_threshold,
        pii_detected=pii_detected,
        total_entities=total_entities,
        entity_summary=entity_summary,
        entity_types=entity_types,
        duration_ms=duration_ms,
    )


def emit_pii_anonymized(
    ctx: Optional[RequestContext],
    *,
    language: str,
    text_length: int,
    score_threshold: float,
    pii_detected: bool,
    total_entities: int,
    entity_summary: list[dict],
    duration_ms: float,
) -> None:
    """Fired after ``/anonymize`` completes successfully."""
    severity = "WARN" if pii_detected else "INFO"
    entity_types = [e["type"] for e in entity_summary]
    message = (
        f"Text anonymized: {total_entities} PII entities masked ({', '.join(entity_types)})"
        if pii_detected
        else f"Text passed through clean — no PII found in {text_length} chars"
    )
    _emit(
        event_type="PII_ANONYMIZED",
        severity=severity,
        message=message,
        **_ctx_fields(ctx),
        language=language,
        text_length=text_length,
        score_threshold=score_threshold,
        pii_detected=pii_detected,
        total_entities=total_entities,
        entity_summary=entity_summary,
        entity_types=entity_types,
        duration_ms=duration_ms,
    )


def emit_request_completed(
    ctx: Optional[RequestContext],
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Fired by middleware after the response is sent."""
    severity = "ERROR" if status_code >= 500 else "WARN" if status_code >= 400 else "INFO"
    _emit(
        event_type="REQUEST_COMPLETED",
        severity=severity,
        message=f"{method} {path} → {status_code} in {duration_ms:.1f}ms",
        **_ctx_fields(ctx),
        http_method=method,
        http_path=path,
        http_status=status_code,
        duration_ms=duration_ms,
    )


def emit_error(
    ctx: Optional[RequestContext],
    *,
    method: str,
    path: str,
    error: str,
    duration_ms: float,
) -> None:
    """Fired when an unhandled exception occurs inside a route."""
    _emit(
        event_type="REQUEST_ERROR",
        severity="ERROR",
        message=f"Error processing {method} {path}: {error}",
        **_ctx_fields(ctx),
        http_method=method,
        http_path=path,
        error=error,
        duration_ms=duration_ms,
    )
