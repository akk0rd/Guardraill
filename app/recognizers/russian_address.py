from presidio_analyzer import Pattern, PatternRecognizer


class RussianAddressRecognizer(PatternRecognizer):
    """
    Recognizes Russian street addresses and city mentions.

    Handles common Russian address prefixes:
      ул.   — улица     (street)
      пр.   — проспект  (avenue)
      пер.  — переулок  (lane)
      бул.  — бульвар   (boulevard)
      пл.   — площадь   (square)
      ш.    — шоссе     (highway)
      наб.  — набережная (embankment)
      туп.  — тупик     (dead end)
      г.    — город     (city prefix)
    """

    # Street / address line with house number
    _STREET_PATTERN = (
        r"(?:ул\.|пр\.|пер\.|бул\.|пл\.|ш\.|наб\.|туп\.)\s+"
        r"[А-Яа-я'\-]{2,}(?:\s+[А-Яа-я'\-]{2,}){0,4}"
        r"\s*,?\s*д?\.?\s*\d+[а-яА-Я]?"
    )

    # City prefix "г. Москва"
    _CITY_PATTERN = r"г\.\s+[А-Яа-я]{2,30}"

    PATTERNS = [
        Pattern(
            name="russian_street_address",
            regex=_STREET_PATTERN,
            score=0.75,
        ),
        Pattern(
            name="russian_city",
            regex=_CITY_PATTERN,
            score=0.55,
        ),
    ]

    CONTEXT = [
        "адрес",
        "address",
        "улица",
        "город",
        "проживает",
        "зарегистрирован",
        "зарегистрирована",
        "прописан",
        "прописана",
        "место жительства",
        "registration",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="RUSSIAN_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="ru",
        )
