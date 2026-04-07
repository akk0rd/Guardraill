from presidio_anonymizer.entities import OperatorConfig

# Default score threshold for PII detection
DEFAULT_SCORE_THRESHOLD = 0.5

# Supported languages
SUPPORTED_LANGUAGES = ["uk", "en", "ru"]

# Default anonymization operators per entity type.
# Entities not listed here fall back to Presidio's default (<ENTITY_TYPE> replacement).
DEFAULT_OPERATORS: dict[str, OperatorConfig] = {
    # ── Ukrainian ──────────────────────────────────────────────────────────
    "UKRAINIAN_PASSPORT": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 6, "from_end": True},
    ),
    "UKRAINIAN_PHONE": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<PHONE>"},
    ),
    "UKRAINIAN_ADDRESS": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<ADDRESS>"},
    ),

    # ── Russian ────────────────────────────────────────────────────────────
    "RUSSIAN_PASSPORT": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 6, "from_end": True},
    ),
    "RUSSIAN_PHONE": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<PHONE>"},
    ),
    "RUSSIAN_ADDRESS": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<ADDRESS>"},
    ),

    # ── Shared (all languages) ─────────────────────────────────────────────
    "PAYMENT_CARD": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 12, "from_end": True},
    ),
    "CREDIT_CARD": OperatorConfig(          # Presidio built-in name for English
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 12, "from_end": True},
    ),
    "PERSON": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<NAME>"},
    ),

    # ── English built-ins ──────────────────────────────────────────────────
    "EMAIL_ADDRESS": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<EMAIL>"},
    ),
    "PHONE_NUMBER": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<PHONE>"},
    ),
    "US_SSN": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 9, "from_end": True},
    ),
    "US_PASSPORT": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<PASSPORT>"},
    ),
    "IP_ADDRESS": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<IP>"},
    ),
}
