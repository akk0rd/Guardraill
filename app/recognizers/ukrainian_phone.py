from presidio_analyzer import Pattern, PatternRecognizer


class UkrainianPhoneRecognizer(PatternRecognizer):
    """
    Recognizes Ukrainian phone numbers.

    Supported formats:
      +380 (XX) XXX-XX-XX   — international with country code
      +380XXXXXXXXX          — international compact
      0XX XXX XX XX          — domestic 10-digit
      0XXXXXXXXX             — domestic compact
    """

    PATTERNS = [
        # International: +380 with optional separators
        Pattern(
            name="ukrainian_phone_international",
            regex=r"\+380\s?\(?\d{2}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
            score=0.9,
        ),
        # Domestic 10-digit starting with 0 (e.g. 0951234567)
        Pattern(
            name="ukrainian_phone_domestic",
            regex=r"\b0\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b",
            score=0.7,
        ),
    ]

    CONTEXT = [
        "телефон",
        "phone",
        "мобільний",
        "номер",
        "тел",
        "tel",
        "дзвінок",
        "call",
        "зв'язок",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="UKRAINIAN_PHONE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )
