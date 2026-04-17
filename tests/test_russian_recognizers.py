"""Unit tests for Russian PII recognizers."""

import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine

from app.recognizers import (
    RussianAddressRecognizer,
    RussianPassportRecognizer,
    RussianPhoneRecognizer,
    UkrainianPanRecognizer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(*recognizers) -> AnalyzerEngine:
    nlp_engine = SpacyNlpEngine(
        models=[{"lang_code": "ru", "model_name": "ru_core_news_sm"}]
    )
    registry = RecognizerRegistry()
    for rec in recognizers:
        registry.add_recognizer(rec)
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["ru"],
    )


def _entity_types(results) -> set:
    return {r.entity_type for r in results}


# ---------------------------------------------------------------------------
# Russian Passport
# ---------------------------------------------------------------------------

class TestRussianPassportRecognizer:
    engine = _make_engine(RussianPassportRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="ru", score_threshold=0.4)

    def test_spaced_series_format(self):
        results = self._analyze("Паспорт 45 07 123456 выдан в Москве.")
        assert "RUSSIAN_PASSPORT" in _entity_types(results)

    def test_compact_series_format(self):
        results = self._analyze("паспорт 4507 123456")
        assert "RUSSIAN_PASSPORT" in _entity_types(results)

    def test_too_short(self):
        results = self._analyze("4507 12345")
        passport_results = [r for r in results if r.entity_type == "RUSSIAN_PASSPORT"]
        assert not passport_results

    def test_no_context_low_score(self):
        # Compact series without context should be below 0.75 threshold
        results = self.engine.analyze(text="4507 123456", language="ru", score_threshold=0.75)
        passport_results = [r for r in results if r.entity_type == "RUSSIAN_PASSPORT"]
        assert not passport_results


# ---------------------------------------------------------------------------
# Russian Phone
# ---------------------------------------------------------------------------

class TestRussianPhoneRecognizer:
    engine = _make_engine(RussianPhoneRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="ru", score_threshold=0.5)

    def test_international_compact(self):
        results = self._analyze("+79051234567")
        assert "RUSSIAN_PHONE" in _entity_types(results)

    def test_international_formatted(self):
        results = self._analyze("+7 (905) 123-45-67")
        assert "RUSSIAN_PHONE" in _entity_types(results)

    def test_domestic_compact(self):
        results = self._analyze("89051234567")
        assert "RUSSIAN_PHONE" in _entity_types(results)

    def test_domestic_formatted(self):
        results = self._analyze("8 (905) 123-45-67")
        assert "RUSSIAN_PHONE" in _entity_types(results)

    def test_invalid_too_short(self):
        results = self._analyze("+7905123")
        assert "RUSSIAN_PHONE" not in _entity_types(results)


# ---------------------------------------------------------------------------
# Russian Address
# ---------------------------------------------------------------------------

class TestRussianAddressRecognizer:
    engine = _make_engine(RussianAddressRecognizer())

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="ru", score_threshold=0.4)

    def test_ulitsa(self):
        results = self._analyze("ул. Арбат 15")
        assert "RUSSIAN_ADDRESS" in _entity_types(results)

    def test_prospekt(self):
        results = self._analyze("пр. Ленина 10")
        assert "RUSSIAN_ADDRESS" in _entity_types(results)

    def test_pereulok(self):
        results = self._analyze("пер. Сивцев 3")
        assert "RUSSIAN_ADDRESS" in _entity_types(results)

    def test_city_prefix(self):
        results = self._analyze("г. Москва")
        assert "RUSSIAN_ADDRESS" in _entity_types(results)

    def test_shosse(self):
        results = self._analyze("ш. Волоколамское 45")
        assert "RUSSIAN_ADDRESS" in _entity_types(results)

    def test_no_false_positive(self):
        results = self._analyze("Привет, как дела?")
        assert "RUSSIAN_ADDRESS" not in _entity_types(results)


# ---------------------------------------------------------------------------
# PAN recognizer for Russian language
# ---------------------------------------------------------------------------

class TestPanRecognizerRussian:
    engine = _make_engine(UkrainianPanRecognizer(language="ru"))

    def _analyze(self, text: str):
        return self.engine.analyze(text=text, language="ru", score_threshold=0.4)

    def test_valid_card_with_russian_context(self):
        results = self._analyze("Карта 4111111111111111")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results

    def test_valid_card_compact(self):
        results = self._analyze("4111111111111111")
        pan_results = [r for r in results if r.entity_type == "PAYMENT_CARD"]
        assert pan_results
