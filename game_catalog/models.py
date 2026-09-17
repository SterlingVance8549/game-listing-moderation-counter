from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ListingKind(str, Enum):
    PLAYER_ASSET = "player_asset"
    LIVE_EVENT = "live_event"


class SourceListing(BaseModel):
    source: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: HttpUrl
    kind: ListingKind
    creator_id: str | None = None
    starts_at: str | None = None
    reports: int = Field(default=0, ge=0)
    restricted: bool = False


class AggregateRequest(BaseModel):
    listings: list[SourceListing] = Field(min_length=1)


class CatalogItem(BaseModel):
    catalog_id: str
    title: str
    description: str
    url: HttpUrl
    kind: ListingKind
    sources: list[str]
    source_ids: list[str]
    creator_id: str | None
    starts_at: str | None
    reports: int


class ModerationItem(BaseModel):
    catalog_id: str
    reason: str
    reports: int


class AggregateResult(BaseModel):
    published: list[CatalogItem]
    moderation_queue: list[ModerationItem]


class SimilarRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=25)
    kind: ListingKind | None = None


class SimilarItem(BaseModel):
    catalog_id: str
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class SimilarResult(BaseModel):
    matches: list[SimilarItem]
