"""Integration tests for the FastAPI endpoints.

Tests run against app.main (combined app) which hosts both /analyze and
/anonymize.  Additional clients test the split analyzer_app and
anonymizer_app independently to verify the port-split architecture.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.analyzer_app import app as analyzer_app
from app.anonymizer_app import app as anonymizer_app

client = TestClient(app)
analyzer_client = TestClient(analyzer_app)
anonymizer_client = TestClient(anonymizer_app)

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


def test_analyzer_health():
    resp = analyzer_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "analyzer"


def test_anonymizer_health():
    resp = anonymizer_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "anonymizer"


# ---------------------------------------------------------------------------
# /analyze  (combined app)
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
# /analyze  (standalone analyzer_app on port 5002)
# ---------------------------------------------------------------------------

def test_analyzer_app_detects_passport():
    resp = analyzer_client.post("/analyze", json={"text": "Паспорт АБ123456"})
    assert resp.status_code == 200
    types = {e["entity_type"] for e in resp.json()["results"]}
    assert "UKRAINIAN_PASSPORT" in types


def test_analyzer_app_no_anonymize_endpoint():
    """The analyzer app must NOT expose /anonymize."""
    resp = analyzer_client.post("/anonymize", json={"text": "Паспорт АБ123456"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /anonymize  (combined app)
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


# ---------------------------------------------------------------------------
# /anonymize  (standalone anonymizer_app on port 5001)
# ---------------------------------------------------------------------------

def test_anonymizer_app_masks_passport():
    resp = anonymizer_client.post("/anonymize", json={"text": "Паспорт АБ123456"})
    assert resp.status_code == 200
    assert "АБ123456" not in resp.json()["anonymized_text"]


def test_anonymizer_app_no_analyze_endpoint():
    """The anonymizer app must NOT expose /analyze."""
    resp = anonymizer_client.post("/analyze", json={"text": "Паспорт АБ123456"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# English language
# ---------------------------------------------------------------------------

def test_english_analyze_detects_email():
    resp = client.post(
        "/analyze",
        json={"text": "Contact me at john.doe@example.com", "language": "en"},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "EMAIL_ADDRESS" in types


def test_english_analyze_detects_phone():
    resp = client.post(
        "/analyze",
        json={"text": "Call me at +1 650-253-0000", "language": "en", "score_threshold": 0.3},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "PHONE_NUMBER" in types


def test_english_analyze_detects_credit_card():
    resp = client.post(
        "/analyze",
        json={"text": "My card is 4111111111111111", "language": "en"},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "CREDIT_CARD" in types


def test_english_anonymize_masks_email():
    resp = client.post(
        "/anonymize",
        json={"text": "Email: john.doe@example.com", "language": "en"},
    )
    body = resp.json()
    assert "john.doe@example.com" not in body["anonymized_text"]


def test_english_anonymize_masks_credit_card():
    resp = client.post(
        "/anonymize",
        json={"text": "Card: 4111111111111111", "language": "en"},
    )
    body = resp.json()
    assert "4111111111111111" not in body["anonymized_text"]


# ---------------------------------------------------------------------------
# Russian language
# ---------------------------------------------------------------------------

def test_russian_analyze_detects_passport():
    resp = client.post(
        "/analyze",
        json={"text": "Паспорт 45 07 123456 выдан в Москве", "language": "ru"},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "RUSSIAN_PASSPORT" in types


def test_russian_analyze_detects_phone():
    resp = client.post(
        "/analyze",
        json={"text": "Телефон +79051234567", "language": "ru"},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "RUSSIAN_PHONE" in types


def test_russian_analyze_detects_address():
    resp = client.post(
        "/analyze",
        json={"text": "Проживает по адресу ул. Арбат 15", "language": "ru"},
    )
    body = resp.json()
    types = {e["entity_type"] for e in body["results"]}
    assert "RUSSIAN_ADDRESS" in types


def test_russian_anonymize_masks_phone():
    resp = client.post(
        "/anonymize",
        json={"text": "Мобильный: +79051234567", "language": "ru"},
    )
    body = resp.json()
    assert "+79051234567" not in body["anonymized_text"]


def test_russian_anonymize_masks_address():
    resp = client.post(
        "/anonymize",
        json={"text": "Адрес: ул. Арбат 15", "language": "ru"},
    )
    body = resp.json()
    assert "ул. Арбат 15" not in body["anonymized_text"]
