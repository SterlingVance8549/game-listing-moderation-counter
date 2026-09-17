import hashlib
from collections import OrderedDict

from .models import AggregateResult, CatalogItem, ModerationItem, SourceListing


REPORT_REVIEW_THRESHOLD = 3


def _identity(listing: SourceListing) -> str:
    creator = listing.creator_id or "event"
    stable = f"{listing.kind.value}:{creator}:{listing.title.strip().casefold()}"
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]


def aggregate_listings(listings: list[SourceListing]) -> AggregateResult:
    grouped: OrderedDict[str, list[SourceListing]] = OrderedDict()
    for listing in listings:
        grouped.setdefault(_identity(listing), []).append(listing)

    published: list[CatalogItem] = []
    moderation_queue: list[ModerationItem] = []
    for catalog_id, copies in grouped.items():
        primary = copies[0]
        reports = sum(item.reports for item in copies)
        restricted = any(item.restricted for item in copies)
        if restricted or reports >= REPORT_REVIEW_THRESHOLD:
            reason = "restricted_content" if restricted else "report_threshold"
            moderation_queue.append(
                ModerationItem(catalog_id=catalog_id, reason=reason, reports=reports)
            )
            continue

        published.append(
            CatalogItem(
                catalog_id=catalog_id,
                title=primary.title,
                description=primary.description,
                url=primary.url,
                kind=primary.kind,
                sources=list(dict.fromkeys(item.source for item in copies)),
                source_ids=list(dict.fromkeys(item.source_id for item in copies)),
                creator_id=primary.creator_id,
                starts_at=primary.starts_at,
                reports=reports,
            )
        )
    return AggregateResult(published=published, moderation_queue=moderation_queue)
