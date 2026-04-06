"""Unit tests for individual Ukrainian PII recognizers."""

import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine

from app.recognizers import (
    UkrainianAddressRecognizer,
    UkrainianPanRecognizer,
    UkrainianPassportRecognizer,
    UkrainianPhoneRecognizer,
)
from app.recognizers.ukrainian_pan import _luhn_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(*recognizers) -> AnalyzerEngine:
    """Build a minimal AnalyzerEngine with only the given recognizers."""
    nlp_engine = SpacyNlpEngine(
        models=[{"lang_code": "uk", "model_name": "uk_core_news_sm"}]
    )
    registry = RecognizerRegistry()
    for rec in recognizers:
        registry.add_recognizer(rec)
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["uk"],
    )


def _entity_types(results) -> set:
    return {r.entity_type for r in results}


def _matched_texts(text: str, results) -> list:
    return [text[r.start : r.end] for r in results]


# ---------------------------------------------------------------------------
# Passport recognizer
# ---------------------------------------------------------------------------

class TestUkrainianPassportRecognizer:
    engine = _make_engine(UkrainianPassportRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="uk", score_threshold=0.4)

    def test_cyrillic_passport(self):
        results = self._analyze("Паспорт серії АБ123456 виданий у Києві.")
        types = _entity_types(results)
        assert "UKRAINIAN_PASSPORT" in types

    def test_latin_passport(self):
        results = self._analyze("passport AB123456 issued in Kyiv")
        types = _entity_types(results)
        assert "UKRAINIAN_PASSPORT" in types

    def test_cyrillic_with_ukrainian_chars(self):
        results = self._analyze("документ ІН123456")
        types = _entity_types(results)
        assert "UKRAINIAN_PASSPORT" in types

    def test_invalid_passport_too_short(self):
        results = self._analyze("АБ12345")
        passport_results = [r for r in results if r.entity_type == "UKRAINIAN_PASSPORT"]
        assert not passport_results

    def test_invalid_passport_only_digits(self):
        results = self._analyze("123456789")
        # Biometric pattern may fire with low score; ensure it's low
        passport_results = [
            r for r in results
            if r.entity_type == "UKRAINIAN_PASSPORT" and r.score >= 0.75
        ]
        assert not passport_results


# ---------------------------------------------------------------------------
# Phone recognizer
# ---------------------------------------------------------------------------

class TestUkrainianPhoneRecognizer:
    engine = _make_engine(UkrainianPhoneRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="uk", score_threshold=0.5)

    def test_international_compact(self):
        results = self._analyze("+380951234567")
        assert "UKRAINIAN_PHONE" in _entity_types(results)

    def test_international_formatted(self):
        results = self._analyze("+380 (95) 123-45-67")
        assert "UKRAINIAN_PHONE" in _entity_types(results)

    def test_domestic_compact(self):
        results = self._analyze("0951234567")
        assert "UKRAINIAN_PHONE" in _entity_types(results)

    def test_domestic_formatted(self):
        results = self._analyze("095 123 45 67")
        assert "UKRAINIAN_PHONE" in _entity_types(results)

    def test_invalid_too_short(self):
        results = self._analyze("+38095123")
        assert "UKRAINIAN_PHONE" not in _entity_types(results)


# ---------------------------------------------------------------------------
# PAN recognizer (Luhn)
# ---------------------------------------------------------------------------

class TestLuhnCheck:
    def test_valid_visa_test_card(self):
        assert _luhn_check("4111111111111111") is True

    def test_valid_mastercard_test_card(self):
        assert _luhn_check("5500005555555559") is True

    def test_invalid_random_digits(self):
        assert _luhn_check("1234567890123456") is False

    def test_invalid_sequential_digits(self):
        # 1234567890123456 does not pass Luhn
        assert _luhn_check("1234567890123456") is False


class TestUkrainianPanRecognizer:
    engine = _make_engine(UkrainianPanRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="uk", score_threshold=0.4)

    def test_valid_visa_card(self):
        results = self._analyze("Карта: 4111111111111111")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results, "Expected PAYMENT_CARD to be detected"

    def test_valid_card_with_spaces(self):
        results = self._analyze("4111 1111 1111 1111")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results

    def test_valid_card_with_hyphens(self):
        results = self._analyze("4111-1111-1111-1111")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results

    def test_invalid_luhn(self):
        # 1234567890123456 fails Luhn
        rec = UkrainianPanRecognizer()
        assert rec.validate_result("1234567890123456") is False

    def test_valid_luhn(self):
        rec = UkrainianPanRecognizer()
        assert rec.validate_result("4111111111111111") is True

    def test_amex(self):
        results = self._analyze("378282246310005")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results


# ---------------------------------------------------------------------------
# Address recognizer
# ---------------------------------------------------------------------------

class TestUkrainianAddressRecognizer:
    engine = _make_engine(UkrainianAddressRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="uk", score_threshold=0.4)

    def test_street_vulytsia(self):
        results = self._analyze("Проживає на вул. Хрещатик 15.")
        assert "UKRAINIAN_ADDRESS" in _entity_types(results)

    def test_street_prospekt(self):
        results = self._analyze("просп. Перемоги 10")
        assert "UKRAINIAN_ADDRESS" in _entity_types(results)

    def test_street_provulok(self):
        results = self._analyze("пров. Садовий 3б")
        assert "UKRAINIAN_ADDRESS" in _entity_types(results)

    def test_city_prefix(self):
        results = self._analyze("м. Київ")
        assert "UKRAINIAN_ADDRESS" in _entity_types(results)

    def test_boulevard(self):
        results = self._analyze("бульв. Тараса Шевченка 27")
        assert "UKRAINIAN_ADDRESS" in _entity_types(results)

    def test_no_false_positive_plain_text(self):
        results = self._analyze("Привіт, як справи?")
        assert "UKRAINIAN_ADDRESS" not in _entity_types(results)
