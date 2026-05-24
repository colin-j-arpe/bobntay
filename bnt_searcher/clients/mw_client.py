import logging
import os

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.dictionaryapi.com/api/v3/references/collegiate/json"


def fetch_inflections(word: str) -> list[str]:
    """
    Call the M-W Collegiate Dictionary API for *word* and return a list of
    unique inflected forms (e.g. plurals, past tenses, conjugations).

    Returns an empty list if the API is unreachable, returns no entries, or
    returns a suggestion list (strings) rather than entry objects.
    """
    api_key = os.environ["MW_API_KEY"]
    url = f"{_BASE_URL}/{word}"

    try:
        response = requests.get(url, params={"key": api_key}, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("M-W API request failed for word=%r", word)
        return []

    data = response.json()

    # M-W returns a list of strings (spelling suggestions) when the word is not
    # found — nothing useful for us.
    if not data or not isinstance(data[0], dict):
        return []

    inflections: list[str] = []
    for entry in data:
        for inflection in entry.get("ins", []):
            form = inflection.get("if", "")
            # Strip the interpunct bullet M-W uses as a syllable separator.
            form = form.replace("\u00b7", "").replace("*", "").strip()
            if form and form not in inflections:
                inflections.append(form)

    return inflections
