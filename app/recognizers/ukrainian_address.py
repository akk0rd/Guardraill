from presidio_analyzer import Pattern, PatternRecognizer


class UkrainianAddressRecognizer(PatternRecognizer):
    """
    Recognizes Ukrainian street addresses and city mentions.

    Handles common Ukrainian address prefixes:
      вул.   — вулиця  (street)
      просп. — проспект (avenue / prospect)
      пров.  — провулок (lane)
      бульв. — бульвар  (boulevard)
      пл.    — площа    (square)
      м.     — місто    (city prefix)
      смт.   — селище міського типу (urban-type settlement)
    """

    # Street / address line with house number
    _STREET_PATTERN = (
        r"(?:вул\.|просп\.|пров\.|бульв\.|пл\.|шосе|смт\.)\s+"
        r"[А-ЯІЇЄа-яіїє'\-]{2,}(?:\s+[А-ЯІЇЄа-яіїє'\-]{2,}){0,4}"
        r"\s*,?\s*\d+[а-яА-ЯІЇЄіїє]?"
    )

    # City prefix "м. Київ" or full city mention
    _CITY_PATTERN = r"м\.\s+[А-ЯІЇЄа-яіїє]{2,30}"

    PATTERNS = [
        Pattern(
            name="ukrainian_street_address",
            regex=_STREET_PATTERN,
            score=0.75,
        ),
        Pattern(
            name="ukrainian_city",
            regex=_CITY_PATTERN,
            score=0.55,
        ),
    ]

    CONTEXT = [
        "адреса",
        "address",
        "вулиця",
        "місто",
        "проживає",
        "зареєстрований",
        "зареєстрована",
        "реєстрація",
        "registration",
        "мешкає",
        "lives at",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="UKRAINIAN_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="uk",
        )
