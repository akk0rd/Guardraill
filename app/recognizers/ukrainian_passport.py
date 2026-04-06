from presidio_analyzer import Pattern, PatternRecognizer


class UkrainianPassportRecognizer(PatternRecognizer):
    """
    Recognizes Ukrainian passport numbers.

    Domestic passport series formats:
      - Cyrillic series: two uppercase Ukrainian letters + 6 digits  (e.g. АБ123456)
      - Latin series:    two uppercase Latin letters + 6 digits       (e.g. AB123456)

    International biometric passport: 9 digits (e.g. 123456789) — handled as a
    separate lower-confidence pattern to avoid false positives with plain numbers.
    """

    PATTERNS = [
        # Cyrillic series (А-Я plus Ukrainian-specific І, Ї, Є)
        Pattern(
            name="ukrainian_passport_cyrillic",
            regex=r"\b[А-ЯІЇЄ]{2}\d{6}\b",
            score=0.85,
        ),
        # Latin-alphabet series (as printed on older documents)
        Pattern(
            name="ukrainian_passport_latin",
            regex=r"\b[A-Z]{2}\d{6}\b",
            score=0.75,
        ),
        # Biometric / international passport number (9 digits)
        Pattern(
            name="ukrainian_passport_biometric",
            regex=r"\b\d{9}\b",
            score=0.4,
        ),
    ]

    CONTEXT = [
        "паспорт",
        "passport",
        "документ",
        "серія",
        "series",
        "посвідчення",
        "id",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="UKRAINIAN_PASSPORT",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )
