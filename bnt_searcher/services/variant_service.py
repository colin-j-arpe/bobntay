import logging
from datetime import datetime, timezone

from bnt_searcher.clients.mw_client import fetch_inflections
from bnt_searcher.models import WordVariant, WordVariantLookup

logger = logging.getLogger(__name__)


def get_variants(search_term: str) -> list[str]:
    """
    Return a list of inflected variant texts for *search_term*.

    Results are cached in WordVariantLookup / WordVariant. A cache hit is
    returned immediately; on a miss the M-W API is called, results are stored,
    and the list is returned.

    Returns an empty list when M-W has no inflections for the term.
    """
    lookup = WordVariantLookup.objects.filter(search_term=search_term).first()
    if lookup is not None:
        return list(lookup.variants.values_list("text", flat=True))

    inflections = fetch_inflections(search_term)
    now = datetime.now(tz=timezone.utc)

    lookup = WordVariantLookup.objects.create(
        search_term=search_term,
        fetched_at=now,
    )

    if inflections:
        WordVariant.objects.bulk_create(
            [WordVariant(lookup=lookup, text=form) for form in inflections]
        )

    return inflections
