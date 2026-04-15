"""
Tests for the SIEM logging / audit event subsystem.

Strategy
--------
* Use ``caplog`` to capture log records emitted by the ``guardrail.audit``
  logger and verify that the required SIEM fields are present and correct.
* Use the FastAPI ``TestClient`` to exercise the full middleware + route stack
  so that ``REQUEST_RECEIVED`` / ``REQUEST_COMPLETED`` events are included.
* Never assert on the actual PII text — only metadata (entity types, counts,
  text_length, etc.) to keep tests aligned with the privacy contract.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.audit import emit_pii_analyzed, summarize_entities
from app.context import RequestContext
from app.main import app

client = TestClient(app, raise_server_exceptions=True)


# ── summarize_entities ────────────────────────────────────────────────────────


class FakeResult:
    """Minimal stand-in for a Presidio RecognizerResult."""

    def __init__(self, entity_type: str, score: float):
        self.entity_type = entity_type
        self.score = score


def test_summarize_entities_counts():
    results = [
        FakeResult("UKRAINIAN_PHONE", 0.9),
        FakeResult("UKRAINIAN_PHONE", 0.8),
        FakeResult("UKRAINIAN_PASSPORT", 0.85),
    ]
    summary = summarize_entities(results)
    by_type = {e["type"]: e for e in summary}
    assert by_type["UKRAINIAN_PHONE"]["count"] == 2
    assert by_type["UKRAINIAN_PHONE"]["score_max"] == 0.9
    assert by_type["UKRAINIAN_PASSPORT"]["count"] == 1


def test_summarize_entities_empty():
    assert summarize_entities([]) == []


def test_summarize_entities_sorted():
    results = [FakeResult("Z_ENTITY", 0.5), FakeResult("A_ENTITY", 0.7)]
    summary = summarize_entities(results)
    assert summary[0]["type"] == "A_ENTITY"
    assert summary[1]["type"] == "Z_ENTITY"


# ── Audit event field presence ────────────────────────────────────────────────


def test_audit_event_required_fields(caplog):
    ctx = RequestContext(
        request_id="test-req-001",
        client_ip="10.0.0.1",
        user_agent="pytest/1.0",
        source="direct",
    )
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        emit_pii_analyzed(
            ctx,
            language="uk",
            text_length=100,
            score_threshold=0.5,
            pii_detected=True,
            total_entities=2,
            entity_summary=[{"type": "UKRAINIAN_PHONE", "count": 2, "score_max": 0.9}],
            duration_ms=12.5,
        )

    assert caplog.records, "No audit records emitted"
    record = caplog.records[0]

    # Mandatory SIEM envelope fields
    assert record.event_type == "PII_ANALYZED"
    assert record.log_type == "AUDIT"
    assert record.severity == "WARN"        # PII detected → WARN
    assert record.service == "guardrail"
    assert hasattr(record, "event_id")

    # Request context fields
    assert record.request_id == "test-req-001"
    assert record.client_ip == "10.0.0.1"
    assert record.source == "direct"

    # Detection fields
    assert record.language == "uk"
    assert record.text_length == 100
    assert record.pii_detected is True
    assert record.total_entities == 2
    assert record.duration_ms == 12.5


def test_audit_event_no_pii_severity(caplog):
    ctx = RequestContext(request_id="r", client_ip="1.2.3.4")
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        emit_pii_analyzed(
            ctx,
            language="en",
            text_length=50,
            score_threshold=0.5,
            pii_detected=False,
            total_entities=0,
            entity_summary=[],
            duration_ms=5.0,
        )
    record = caplog.records[0]
    assert record.severity == "INFO"        # No PII → INFO


def test_audit_event_litellm_fields(caplog):
    ctx = RequestContext(
        request_id="litellm-call-xyz",
        client_ip="10.0.0.2",
        source="litellm",
        litellm_user_id="user-42",
        litellm_team_id="team-finance",
        litellm_org_id="acme-corp",
        litellm_call_id="litellm-call-xyz",
        litellm_model="gpt-4o",
    )
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        emit_pii_analyzed(
            ctx,
            language="uk",
            text_length=80,
            score_threshold=0.5,
            pii_detected=False,
            total_entities=0,
            entity_summary=[],
            duration_ms=8.0,
        )
    record = caplog.records[0]
    assert record.user_id == "user-42"
    assert record.team_id == "team-finance"
    assert record.org_id == "acme-corp"
    assert record.litellm_model == "gpt-4o"
    assert record.source == "litellm"


# ── JSON formatter ────────────────────────────────────────────────────────────


def test_json_formatter_produces_valid_json(caplog):
    from app.logging_config import SiemJsonFormatter

    formatter = SiemJsonFormatter()
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        emit_pii_analyzed(
            RequestContext(request_id="r", client_ip="1.1.1.1"),
            language="ru",
            text_length=30,
            score_threshold=0.5,
            pii_detected=False,
            total_entities=0,
            entity_summary=[],
            duration_ms=3.0,
        )

    record = caplog.records[0]
    json_str = formatter.format(record)
    obj = json.loads(json_str)              # must not raise

    assert obj["level"] == "INFO"
    assert "@timestamp" in obj
    assert obj["log_type"] == "AUDIT"
    assert obj["event_type"] == "PII_ANALYZED"


def test_json_formatter_no_pii_in_output(caplog):
    """The formatter must never include the actual text being analysed."""
    from app.logging_config import SiemJsonFormatter

    secret_text = "паспорт АБ999999 телефон +380991112233"
    formatter = SiemJsonFormatter()

    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        emit_pii_analyzed(
            RequestContext(request_id="r", client_ip="1.1.1.1"),
            language="uk",
            text_length=len(secret_text),
            score_threshold=0.5,
            pii_detected=True,
            total_entities=2,
            entity_summary=[
                {"type": "UKRAINIAN_PASSPORT", "count": 1, "score_max": 0.85},
                {"type": "UKRAINIAN_PHONE", "count": 1, "score_max": 0.9},
            ],
            duration_ms=15.0,
        )

    record = caplog.records[0]
    json_str = formatter.format(record)
    # The actual PII strings must not appear in the log output
    assert "АБ999999" not in json_str
    assert "+380991112233" not in json_str
    assert secret_text not in json_str


# ── Middleware integration ─────────────────────────────────────────────────────


def test_request_id_echoed_in_response_header():
    resp = client.post(
        "/analyze",
        json={"text": "hello"},
        headers={"X-Request-ID": "my-custom-id-123"},
    )
    assert resp.headers.get("x-request-id") == "my-custom-id-123"


def test_request_id_generated_when_absent():
    resp = client.post("/analyze", json={"text": "hello"})
    rid = resp.headers.get("x-request-id", "")
    assert len(rid) > 0


def test_litellm_call_id_used_as_request_id():
    resp = client.post(
        "/analyze",
        json={"text": "hello"},
        headers={"x-litellm-call-id": "litellm-abc-123"},
    )
    assert resp.headers.get("x-request-id") == "litellm-abc-123"


def _audit_records(caplog, event_type: str | None = None):
    """Filter caplog records to those from the audit logger that have event_type."""
    records = [r for r in caplog.records if getattr(r, "log_type", None) == "AUDIT"]
    if event_type:
        records = [r for r in records if getattr(r, "event_type", None) == event_type]
    return records


def test_middleware_emits_lifecycle_events(caplog):
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        client.post("/analyze", json={"text": "Паспорт АБ123456"})

    event_types = {getattr(r, "event_type", None) for r in _audit_records(caplog)}
    assert "REQUEST_RECEIVED" in event_types
    assert "REQUEST_COMPLETED" in event_types


def test_middleware_emits_pii_analyzed_event(caplog):
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        client.post("/analyze", json={"text": "Паспорт АБ123456"})

    assert _audit_records(caplog, "PII_ANALYZED"), "PII_ANALYZED not emitted"


def test_middleware_emits_pii_anonymized_event(caplog):
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        client.post("/anonymize", json={"text": "Паспорт АБ123456"})

    assert _audit_records(caplog, "PII_ANONYMIZED"), "PII_ANONYMIZED not emitted"


def test_litellm_headers_captured_in_audit(caplog):
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        client.post(
            "/analyze",
            json={"text": "hello"},
            headers={
                "x-litellm-user-id": "user-99",
                "x-litellm-team-id": "team-security",
                "x-litellm-model": "gpt-4o",
                "x-litellm-call-id": "call-xyz",
            },
        )

    pii_records = _audit_records(caplog, "PII_ANALYZED")
    assert pii_records, "PII_ANALYZED event not emitted"
    record = pii_records[0]
    assert record.user_id == "user-99"
    assert record.team_id == "team-security"
    assert record.litellm_model == "gpt-4o"
    assert record.source == "litellm"


def test_request_completed_has_duration(caplog):
    with caplog.at_level(logging.INFO, logger="guardrail.audit"):
        client.post("/analyze", json={"text": "test"})

    completed = _audit_records(caplog, "REQUEST_COMPLETED")
    assert completed
    assert completed[0].duration_ms > 0
    assert completed[0].http_status == 200
