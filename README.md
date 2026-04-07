# Guardraill

A Ukrainian-language PII detection and masking service built on [Microsoft Presidio](https://microsoft.github.io/presidio/) and [spaCy](https://spacy.io/).

---

## Table of Contents

1. [Features](#features)
2. [Quick Start](#quick-start)
3. [Running with Docker](#running-with-docker)
4. [API Reference](#api-reference)
5. [Configuration](#configuration)
6. [How to Add a New Language](#how-to-add-a-new-language)
7. [How to Add a New PII Recognizer](#how-to-add-a-new-pii-recognizer)
8. [How to Add a New Masking Template](#how-to-add-a-new-masking-template)
9. [Running Tests](#running-tests)
10. [Project Structure](#project-structure)

---

## Features

### Ukrainian (`language: "uk"`)
| Entity | Example input | Masked output |
|---|---|---|
| `UKRAINIAN_PASSPORT` | `АБ123456` / `AB123456` | `АБ******` |
| `UKRAINIAN_PHONE` | `+380951234567` / `0951234567` | `<PHONE>` |
| `PAYMENT_CARD` | `4111 1111 1111 1111` | `4111************` |
| `UKRAINIAN_ADDRESS` | `вул. Хрещатик 15` | `<ADDRESS>` |
| `PERSON` (NER) | `Іван Петренко` | `<NAME>` |

### Russian (`language: "ru"`)
| Entity | Example input | Masked output |
|---|---|---|
| `RUSSIAN_PASSPORT` | `45 07 123456` | `45 07 ******` |
| `RUSSIAN_PHONE` | `+79051234567` / `89051234567` | `<PHONE>` |
| `PAYMENT_CARD` | `4111 1111 1111 1111` | `4111************` |
| `RUSSIAN_ADDRESS` | `ул. Арбат 15` | `<ADDRESS>` |
| `PERSON` (NER) | `Иван Петров` | `<NAME>` |

### English (`language: "en"`)
Powered by Presidio's built-in recognizers + `en_core_web_sm` NER:

| Entity | Example input | Masked output |
|---|---|---|
| `CREDIT_CARD` | `4111111111111111` | `4111************` |
| `EMAIL_ADDRESS` | `john@example.com` | `<EMAIL>` |
| `PHONE_NUMBER` | `+1 650-253-0000` | `<PHONE>` |
| `US_SSN` | `078-05-1120` | `*********` |
| `US_PASSPORT` | `A12345678` | `<PASSPORT>` |
| `IP_ADDRESS` | `192.168.1.1` | `<IP>` |
| `PERSON` (NER) | `John Smith` | `<NAME>` |

All payment card numbers are validated with the **Luhn algorithm** to eliminate false positives.

---

## Quick Start

### Prerequisites

- Python 3.11+

### Install

```bash
git clone https://github.com/akk0rd/Guardraill.git
cd Guardraill

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Language models (all three recommended; service starts with whichever are installed)
python -m spacy download uk_core_news_sm   # Ukrainian
python -m spacy download en_core_web_sm    # English
python -m spacy download ru_core_news_sm   # Russian
```

### Run

```bash
uvicorn app.main:app --reload
```

The service is available at **http://localhost:8000**.  
Interactive API docs (Swagger UI): **http://localhost:8000/docs**

---

## Running with Docker

```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down
```

The container exposes port **8000** and automatically downloads `uk_core_news_sm` at build time.

---

## API Reference

### `GET /health`

Liveness check.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "version": "1.0.0"}
```

---

### `POST /analyze`

Detect PII entities and return their positions and confidence scores.

**Request body**

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | required | Text to analyse |
| `language` | string | `"uk"` | Language code |
| `entities` | list[string] | `null` | Filter to specific entity types; `null` = all |
| `score_threshold` | float | `0.5` | Minimum confidence score (0–1) |

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Паспорт АБ123456, тел +380951234567, вул. Хрещатик 15"
  }'
```

```json
{
  "results": [
    {"entity_type": "UKRAINIAN_PASSPORT", "start": 8,  "end": 16, "score": 0.85, "text": "АБ123456"},
    {"entity_type": "UKRAINIAN_PHONE",    "start": 23, "end": 36, "score": 0.9,  "text": "+380951234567"},
    {"entity_type": "UKRAINIAN_ADDRESS",  "start": 38, "end": 54, "score": 0.75, "text": "вул. Хрещатик 15"}
  ],
  "total": 3
}
```

Filter to a single entity type:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Паспорт АБ123456, тел +380951234567", "entities": ["UKRAINIAN_PASSPORT"]}'
```

---

### `POST /anonymize`

Detect PII and return text with all entities masked/replaced.

**Request body**

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | required | Text to anonymise |
| `language` | string | `"uk"` | Language code |
| `score_threshold` | float | `0.5` | Minimum confidence score (0–1) |

```bash
curl -X POST http://localhost:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Іван Петренко, паспорт АБ123456, тел +380951234567, карта 4111111111111111, вул. Хрещатик 15"
  }'
```

```json
{
  "anonymized_text": "<NAME>, паспорт АБ******, тел <PHONE>, карта 4111************, <ADDRESS>",
  "entities_found": 5
}
```

---

## Configuration

Default masking operators are defined in `app/config.py`:

```python
DEFAULT_OPERATORS: dict[str, OperatorConfig] = {
    "UKRAINIAN_PASSPORT": OperatorConfig("mask",    {"masking_char": "*", "chars_to_mask": 6,  "from_end": True}),
    "UKRAINIAN_PHONE":    OperatorConfig("replace", {"new_value": "<PHONE>"}),
    "PAYMENT_CARD":       OperatorConfig("mask",    {"masking_char": "*", "chars_to_mask": 12, "from_end": True}),
    "UKRAINIAN_ADDRESS":  OperatorConfig("replace", {"new_value": "<ADDRESS>"}),
    "PERSON":             OperatorConfig("replace", {"new_value": "<NAME>"}),
}
```

Built-in Presidio operators:

| Operator | Effect | Key params |
|---|---|---|
| `replace` | Substitute with a fixed string | `new_value` |
| `mask` | Overwrite N chars with a symbol | `masking_char`, `chars_to_mask`, `from_end` |
| `redact` | Delete the span entirely | — |
| `hash` | Replace with SHA-256/SHA-512 hash | `hash_type` |
| `encrypt` | AES-CBC encrypt the span | `key` |

---

## How to Add a New Language

### 1. Install a spaCy model for that language

```bash
python -m spacy download fr_core_news_sm   # example: French
```

### 2. Register the model in `app/engine.py`

Open `app/engine.py` and add the new language to `nlp_config`:

```python
nlp_config = {
    "nlp_engine_name": "spacy",
    "models": [
        {"lang_code": "uk", "model_name": "uk_core_news_sm"},
        {"lang_code": "fr", "model_name": "fr_core_news_sm"},  # ← add this
    ],
}
```

Also add `"fr"` to `supported_languages`:

```python
return AnalyzerEngine(
    nlp_engine=nlp_engine,
    registry=registry,
    supported_languages=["uk", "fr"],   # ← add language code
)
```

### 3. Pass the language in requests

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Mon numéro est +33612345678", "language": "fr"}'
```

### 4. (Optional) Add language-specific recognizers

Create `app/recognizers/french_phone.py` following the same pattern as the existing Ukrainian recognizers (see [How to Add a New PII Recognizer](#how-to-add-a-new-pii-recognizer)), then register it in `app/engine.py`.

> **Tip:** Presidio ships predefined recognizers for many common entities (email, credit card, IP address, etc.) that work across languages without any extra setup. Check what is already available before writing new recognizers:
> ```python
> analyzer.get_recognizers(language="fr")
> ```

---

## How to Add a New PII Recognizer

### Option A — Regex pattern (simple)

1. **Create the recognizer file**, e.g. `app/recognizers/ukrainian_inn.py`:

```python
from presidio_analyzer import Pattern, PatternRecognizer

class UkrainianInnRecognizer(PatternRecognizer):
    """Recognizes Ukrainian individual tax numbers (РНОКПП) — 10 digits."""

    PATTERNS = [
        Pattern(
            name="ukrainian_inn",
            regex=r"\b\d{10}\b",
            score=0.6,
        ),
    ]

    CONTEXT = ["інн", "рнокпп", "податковий", "ідентифікаційний", "номер платника"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="UKRAINIAN_INN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )
```

Key parameters:

| Parameter | Description |
|---|---|
| `supported_entity` | Unique name used in API responses and operator config |
| `regex` | Python regex pattern |
| `score` | Base confidence (0–1); context words can raise it |
| `context` | Words that, when near a match, boost the score |
| `supported_language` | Language code this recognizer is valid for |

2. **Export it** in `app/recognizers/__init__.py`:

```python
from .ukrainian_inn import UkrainianInnRecognizer
```

3. **Register it** in `app/engine.py`:

```python
from app.recognizers import UkrainianInnRecognizer   # add import

# inside _build_analyzer():
for recognizer in [
    UkrainianPassportRecognizer(),
    UkrainianPhoneRecognizer(),
    UkrainianPanRecognizer(),
    UkrainianAddressRecognizer(),
    UkrainianInnRecognizer(),               # ← add here
]:
    registry.add_recognizer(recognizer)
```

### Option B — Regex + custom validation

Override `validate_result` to apply extra logic (e.g. checksum) after the regex matches. Return `True` to accept, `False` to reject, or `None` to leave the score unchanged.

```python
from typing import Optional
from presidio_analyzer import Pattern, PatternRecognizer

class UkrainianEdrpouRecognizer(PatternRecognizer):
    """ЄДРПОУ — 8-digit company registration code with checksum."""

    PATTERNS = [Pattern(name="edrpou", regex=r"\b\d{8}\b", score=0.5)]
    CONTEXT   = ["єдрпоу", "edrpou", "код підприємства", "реєстраційний код"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="UKRAINIAN_EDRPOU",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        if not pattern_text.isdigit() or len(pattern_text) != 8:
            return False
        return self._checksum_ok(pattern_text)

    @staticmethod
    def _checksum_ok(number: str) -> bool:
        weights = [1, 2, 3, 4, 5, 6, 7]
        digits  = [int(c) for c in number]
        total   = sum(w * d for w, d in zip(weights, digits))
        return total % 11 == digits[7]
```

### Option C — NER-based (machine learning)

If you have a trained NER model that labels custom entity types, configure it via `NlpEngineProvider` and map its labels to Presidio entity names using `NerModelConfiguration`. See the [Presidio docs on custom NLP models](https://microsoft.github.io/presidio/analyzer/customizing_nlp_models/).

---

## How to Add a New Masking Template

A *masking template* is an `OperatorConfig` that tells the anonymizer what to do with a matched entity.

### 1. Change the default operator for an entity

Edit `app/config.py`:

```python
# Before: replace phone with placeholder
"UKRAINIAN_PHONE": OperatorConfig("replace", {"new_value": "<PHONE>"}),

# After: mask last 7 digits, keep +380XX visible
"UKRAINIAN_PHONE": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 7, "from_end": True}),
```

### 2. Use `redact` to delete PII entirely

```python
"UKRAINIAN_ADDRESS": OperatorConfig("redact"),
```

### 3. Use `hash` to pseudonymise deterministically

```python
from presidio_anonymizer.entities import OperatorConfig

"UKRAINIAN_PASSPORT": OperatorConfig("hash", {"hash_type": "sha256"}),
```

The same passport number will always produce the same hash, which is useful for linking records without exposing the raw value.

### 4. Use `encrypt` for reversible masking

```python
"PAYMENT_CARD": OperatorConfig("encrypt", {"key": "WmZq4t7w!z%C&F)J"}),
```

The encrypted value can later be decrypted with Presidio's `DeanonymizeEngine` using the same key.

### 5. Add a per-entity-type template at runtime (advanced)

If you want callers to supply their own operator map, extend `AnonymizeRequest` in `app/models.py` to accept an `operators` field and pass it through to `anonymizer.anonymize()` in `app/main.py`.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Only recognizer unit tests
pytest tests/test_recognizers.py -v

# Only API integration tests
pytest tests/test_api.py -v

# With coverage report
pip install pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

Expected output: **44 passed**.

---

## Project Structure

```
Guardraill/
├── app/
│   ├── __init__.py
│   ├── config.py                  # Default operators and constants
│   ├── engine.py                  # Presidio AnalyzerEngine + AnonymizerEngine init
│   ├── main.py                    # FastAPI app and route handlers
│   ├── models.py                  # Pydantic request / response models
│   └── recognizers/
│       ├── __init__.py
│       ├── ukrainian_address.py   # вул. / просп. / пров. / бульв. / пл.
│       ├── ukrainian_pan.py       # Payment card + Luhn validation (uk + ru)
│       ├── ukrainian_passport.py  # АБ123456 / AB123456
│       ├── ukrainian_phone.py     # +380XX... / 0XX...
│       ├── russian_address.py     # ул. / пр. / пер. / бул. / пл. / ш. / наб.
│       ├── russian_passport.py    # 45 07 123456 / 4507 123456
│       └── russian_phone.py       # +7XXX... / 8XXX...
├── tests/
│   ├── test_api.py                # Integration tests (FastAPI TestClient) — uk/en/ru
│   ├── test_recognizers.py        # Unit tests — Ukrainian recognizers
│   └── test_russian_recognizers.py # Unit tests — Russian recognizers
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```
