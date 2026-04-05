from typing import Optional

from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer.predefined_recognizers.credit_card_recognizer import (
    CreditCardRecognizer,
)


def _luhn_check(number: str) -> bool:
    """Return True if *number* (digits only) passes the Luhn check."""
    digits = [int(d) for d in number]
    # Double every second digit from the right
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


class UkrainianPanRecognizer(PatternRecognizer):
    """
    Recognizes payment card numbers (PAN) used in Ukraine.

    Accepts 16-digit numbers written:
      - Continuously:          4111111111111111
      - With spaces:           4111 1111 1111 1111
      - With hyphens:          4111-1111-1111-1111

    Applies Luhn algorithm validation to reduce false positives.
    Context words boost the score when found nearby.
    """

    PATTERNS = [
        Pattern(
            name="pan_16_digit",
            regex=r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
            score=0.5,
        ),
        # American Express: 15-digit  (34xx / 37xx)
        Pattern(
            name="pan_amex",
            regex=r"\b3[47]\d{2}[\s\-]?\d{6}[\s\-]?\d{5}\b",
            score=0.5,
        ),
    ]

    CONTEXT = [
        "карта",
        "card",
        "платіжна",
        "кредитна",
        "дебетова",
        "visa",
        "mastercard",
        "банк",
        "bank",
        "оплата",
        "payment",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="PAYMENT_CARD",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """Validate PAN with Luhn algorithm; strip separators first."""
        digits_only = pattern_text.replace(" ", "").replace("-", "")
        if not digits_only.isdigit():
            return False
        if len(digits_only) not in (15, 16):
            return False
        return _luhn_check(digits_only)
