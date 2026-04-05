"""Integration tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_TEXT = (
    "Іван Петренко, паспорт серії АБ123456, "
    "телефон +380951234567, "
    "карта 4111111111111111, "
    "адреса: вул. Хрещатик 15, м. Київ."
)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# /analyze
# ---------------------------------------------------------------------------

def test_analyze_returns_200():
    resp = client.post("/analyze", json={"text": SAMPLE_TEXT})
    assert resp.status_code == 200


def test_analyze_detects_passport():
    resp = client.post("/analyze", json={"text": "Паспорт АБ123456"})
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "UKRAINIAN_PASSPORT" in types


def test_analyze_detects_phone():
    resp = client.post("/analyze", json={"text": "Мій телефон +380951234567"})
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "UKRAINIAN_PHONE" in types


def test_analyze_detects_pan():
    resp = client.post("/analyze", json={"text": "Карта 4111111111111111"})
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "PAYMENT_CARD" in types


def test_analyze_detects_address():
    resp = client.post("/analyze", json={"text": "вул. Хрещатик 15"})
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "UKRAINIAN_ADDRESS" in types


def test_analyze_entity_filter():
    resp = client.post(
        "/analyze",
        json={"text": SAMPLE_TEXT, "entities": ["UKRAINIAN_PASSPORT"]},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert types == {"UKRAINIAN_PASSPORT"}


def test_analyze_total_field():
    resp = client.post("/analyze", json={"text": SAMPLE_TEXT})
    body = resp.json()
    assert body["total"] == len(body["results"])


def test_analyze_result_structure():
    resp = client.post("/analyze", json={"text": "Паспорт АБ123456"})
    body = resp.json()
    assert body["results"]
    first = body["results"][0]
    assert "entity_type" in first
    assert "start" in first
    assert "end" in first
    assert "score" in first
    assert "text" in first
    assert first["start"] < first["end"]


def test_analyze_no_pii():
    resp = client.post("/analyze", json={"text": "Привіт, як справи?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# /anonymize
# ---------------------------------------------------------------------------

def test_anonymize_returns_200():
    resp = client.post("/anonymize", json={"text": SAMPLE_TEXT})
    assert resp.status_code == 200


def test_anonymize_masks_passport():
    resp = client.post("/anonymize", json={"text": "Паспорт АБ123456"})
    body = resp.json()
    assert "АБ123456" not in body["anonymized_text"]


def test_anonymize_masks_phone():
    resp = client.post("/anonymize", json={"text": "+380951234567"})
    body = resp.json()
    assert "+380951234567" not in body["anonymized_text"]


def test_anonymize_masks_pan():
    resp = client.post("/anonymize", json={"text": "Карта 4111111111111111"})
    body = resp.json()
    assert "4111111111111111" not in body["anonymized_text"]


def test_anonymize_masks_address():
    resp = client.post("/anonymize", json={"text": "вул. Хрещатик 15"})
    body = resp.json()
    assert "вул. Хрещатик 15" not in body["anonymized_text"]


def test_anonymize_no_pii_unchanged():
    text = "Привіт, як справи?"
    resp = client.post("/anonymize", json={"text": text})
    body = resp.json()
    assert body["anonymized_text"] == text
    assert body["entities_found"] == 0


def test_anonymize_entities_found_count():
    resp = client.post("/anonymize", json={"text": SAMPLE_TEXT})
    body = resp.json()
    assert body["entities_found"] > 0


def test_anonymize_response_structure():
    resp = client.post("/anonymize", json={"text": SAMPLE_TEXT})
    body = resp.json()
    assert "anonymized_text" in body
    assert "entities_found" in body
