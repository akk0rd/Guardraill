"""
Presidio engine initialisation.

Creates a single shared AnalyzerEngine (with Ukrainian spaCy model) and
AnonymizerEngine that are reused across all requests.
"""

import logging

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from app.recognizers import (
    UkrainianAddressRecognizer,
    UkrainianPanRecognizer,
    UkrainianPassportRecognizer,
    UkrainianPhoneRecognizer,
)

logger = logging.getLogger(__name__)


def _build_analyzer() -> AnalyzerEngine:
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "uk", "model_name": "uk_core_news_sm"}],
    }

    try:
        provider = NlpEngineProvider(nlp_config=nlp_config)
        nlp_engine = provider.create_engine()
    except Exception:
        logger.warning(
            "uk_core_news_sm not found, falling back to blank spaCy model. "
            "Person-name detection via NER will be unavailable. "
            "Run: python -m spacy download uk_core_news_sm"
        )
        from presidio_analyzer.nlp_engine import SpacyNlpEngine

        nlp_engine = SpacyNlpEngine(
            models=[{"lang_code": "uk", "model_name": "uk_core_news_sm"}]
        )

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(languages=["uk"], nlp_engine=nlp_engine)

    # Register custom Ukrainian recognizers
    for recognizer in [
        UkrainianPassportRecognizer(),
        UkrainianPhoneRecognizer(),
        UkrainianPanRecognizer(),
        UkrainianAddressRecognizer(),
    ]:
        registry.add_recognizer(recognizer)

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["uk"],
    )


# Singletons — initialised once at import time
analyzer: AnalyzerEngine = _build_analyzer()
anonymizer: AnonymizerEngine = AnonymizerEngine()
