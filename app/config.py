from presidio_anonymizer.entities import OperatorConfig

# Default score threshold for PII detection
DEFAULT_SCORE_THRESHOLD = 0.5

# Supported language
LANGUAGE = "uk"

# Default anonymization operators per entity type
DEFAULT_OPERATORS: dict[str, OperatorConfig] = {
    "UKRAINIAN_PASSPORT": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 6, "from_end": True},
    ),
    "UKRAINIAN_PHONE": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<PHONE>"},
    ),
    "PAYMENT_CARD": OperatorConfig(
        operator_name="mask",
        params={"masking_char": "*", "chars_to_mask": 12, "from_end": True},
    ),
    "UKRAINIAN_ADDRESS": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<ADDRESS>"},
    ),
    "PERSON": OperatorConfig(
        operator_name="replace",
        params={"new_value": "<NAME>"},
    ),
}
