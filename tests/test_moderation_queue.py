from game_catalog.models import ListingKind, SourceListing
from game_catalog.moderation_queue import aggregate_listings


def listing(source: str, source_id: str, reports: int) -> SourceListing:
    return SourceListing(
        source=source,
        source_id=source_id,
        title="Neon Harbor Map",
        description="A player-built night market arena",
        url=f"https://{source}.example/maps/{source_id}",
        kind=ListingKind.PLAYER_ASSET,
        creator_id="builder-17",
        reports=reports,
    )


def test_duplicate_reports_are_combined_before_moderation() -> None:
    result = aggregate_listings(
        [listing("forge", "map-8", 1), listing("arcade", "asset-41", 2)]
    )

    assert result.published == []
    assert len(result.moderation_queue) == 1
    assert result.moderation_queue[0].reason == "report_threshold"
    assert result.moderation_queue[0].reports == 3
