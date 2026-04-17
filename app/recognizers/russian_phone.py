from presidio_analyzer import Pattern, PatternRecognizer


class RussianPhoneRecognizer(PatternRecognizer):
    """
    Recognizes Russian phone numbers.

    Supported formats:
      +7 (XXX) XXX-XX-XX   — international with country code
      +7XXXXXXXXXX          — international compact
      8 (XXX) XXX-XX-XX    — domestic prefix 8
      8XXXXXXXXXX           — domestic compact
    """

    PATTERNS = [
        # International: +7 with optional separators
        Pattern(
            name="russian_phone_international",
            regex=r"\+7\s?\(?\d{3}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
            score=0.9,
        ),
        # Domestic: starts with 8 followed by 10 digits (with optional separators)
        Pattern(
            name="russian_phone_domestic",
            regex=r"\b8\s?\(?\d{3}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b",
            score=0.7,
        ),
    ]

    CONTEXT = [
        "телефон",
        "тел",
        "мобильный",
        "номер",
        "phone",
        "звонок",
        "call",
        "связь",
        "контакт",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="RUSSIAN_PHONE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="ru",
        )
