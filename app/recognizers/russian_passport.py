from presidio_analyzer import Pattern, PatternRecognizer


class RussianPassportRecognizer(PatternRecognizer):
    """
    Recognizes Russian domestic passport numbers.

    Format: серия (4 digits, often written as 2+2) + номер (6 digits).
    Examples:
      "45 07 123456"   — series split with space
      "4507 123456"    — series compact with space before number
    """

    PATTERNS = [
        # "45 07 123456" — two pairs + 6 digits
        Pattern(
            name="russian_passport_spaced_series",
            regex=r"\b\d{2}\s\d{2}\s\d{6}\b",
            score=0.75,
        ),
        # "4507 123456" — 4-digit series + space + 6-digit number
        Pattern(
            name="russian_passport_compact_series",
            regex=r"\b\d{4}\s\d{6}\b",
            score=0.55,
        ),
    ]

    CONTEXT = [
        "паспорт",
        "серия",
        "номер",
        "выдан",
        "гражданин",
        "документ",
        "passport",
        "удостоверение",
        "рф",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="RUSSIAN_PASSPORT",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="ru",
        )
