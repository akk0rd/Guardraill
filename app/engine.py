"""
Presidio engine initialisation.

Creates a single shared AnalyzerEngine (with Ukrainian, English, and Russian
spaCy models) and AnonymizerEngine that are reused across all requests.
"""

import logging

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from app.recognizers import (
    RussianAddressRecognizer,
    RussianPassportRecognizer,
    RussianPhoneRecognizer,
    UkrainianAddressRecognizer,
    UkrainianPanRecognizer,
    UkrainianPassportRecognizer,
    UkrainianPhoneRecognizer,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["uk", "en", "ru"]

# spaCy model for each language; fall back to a blank model if not installed
_SPACY_MODELS = {
    "uk": "uk_core_news_sm",
    "en": "en_core_web_sm",
    "ru": "ru_core_news_sm",
}


def _build_analyzer() -> AnalyzerEngine:
    models = []
    for lang, model_name in _SPACY_MODELS.items():
        try:
            import spacy
            spacy.load(model_name)          # probe — raises if missing
            models.append({"lang_code": lang, "model_name": model_name})
            logger.info("Loaded spaCy model %s for language '%s'", model_name, lang)
        except OSError:
            logger.warning(
                "spaCy model '%s' not found for language '%s'. "
                "NER-based entity detection (e.g. PERSON) will be unavailable for this language. "
                "Install with: python -m spacy download %s",
                model_name, lang, model_name,
            )

    if not models:
        raise RuntimeError(
            "No spaCy models found. Install at least one with e.g.: "
            "python -m spacy download uk_core_news_sm"
        )

    nlp_config = {"nlp_engine_name": "spacy", "models": models}
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()

    available_langs = [m["lang_code"] for m in models]

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(
        languages=available_langs, nlp_engine=nlp_engine
    )

    # Ukrainian recognizers
    for recognizer in [
        UkrainianPassportRecognizer(),
        UkrainianPhoneRecognizer(),
        UkrainianPanRecognizer(language="uk"),
        UkrainianAddressRecognizer(),
    ]:
        registry.add_recognizer(recognizer)

    # Russian recognizers
    for recognizer in [
        RussianPassportRecognizer(),
        RussianPhoneRecognizer(),
        UkrainianPanRecognizer(language="ru"),   # same Luhn logic, Russian context
        RussianAddressRecognizer(),
    ]:
        registry.add_recognizer(recognizer)

    # English: Presidio's built-in recognizers (CreditCard, Email, Phone, etc.)
    # are already loaded via load_predefined_recognizers above.

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=available_langs,
    )


# Singletons — initialised once at import time
analyzer: AnalyzerEngine = _build_analyzer()
anonymizer: AnonymizerEngine = AnonymizerEngine()
