import logging
from datetime import UTC, datetime

from bnt_searcher.clients.mw_client import fetch_inflections
from bnt_searcher.models import WordVariant, WordVariantAlias, WordVariantLookup

logger = logging.getLogger(__name__)


def get_variants(search_term: str) -> list[str]:
    """
    Return a list of inflected variant texts for *search_term*.

    Results are cached via WordVariantAlias → WordVariantLookup / WordVariant.
    An alias hit is returned immediately. On a miss, the M-W API is called,
    results are stored under the canonical headword, and an alias is created
    so subsequent calls for the same term skip the API entirely.

    Returns an empty list when M-W has no inflections for the term.
    """
    alias = (
        WordVariantAlias.objects.filter(searched_term=search_term).select_related("lookup").first()
    )
    if alias is not None:
        return list(alias.lookup.variants.values_list("text", flat=True))

    headword, inflections = fetch_inflections(search_term)
    if headword is None:
        headword = search_term

    lookup = WordVariantLookup.objects.filter(headword=headword).first()
    if lookup is None:
        lookup = WordVariantLookup.objects.create(
            headword=headword,
            fetched_at=datetime.now(tz=UTC),
        )
        if inflections:
            WordVariant.objects.bulk_create(
                [WordVariant(lookup=lookup, text=form) for form in inflections]
            )

    WordVariantAlias.objects.create(searched_term=search_term, lookup=lookup)

    return list(lookup.variants.values_list("text", flat=True))
