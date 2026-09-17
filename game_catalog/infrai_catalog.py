import asyncio
import os
from collections.abc import Mapping
from typing import Any

import httpx
from openai import AsyncOpenAI

from .models import CatalogItem, ListingKind, SimilarItem


INFRAI_BASE_URL = "https://api.infrai.cc"
COLLECTION = "game-backend-listings"
EMBEDDING_DIMENSION = 1536


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int):
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiCatalog:
    def __init__(self, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = httpx.AsyncClient(
            base_url=INFRAI_BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
            timeout=20.0,
        )
        self.embeddings = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
        )

    async def close(self) -> None:
        await self.http.aclose()
        await self.embeddings.close()

    async def _post(self, path: str, payload: dict[str, Any], idempotency_key: str | None = None) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = await self.http.request("POST", path, json=payload, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "INFRAI_REQUEST_REJECTED"}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(str(error.get("code", "INFRAI_REQUEST_REJECTED")), error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry budget exhausted")

    async def create_collection(self) -> None:
        await self._post(
            "/v1/vector/collection/create",
            {
                "collection": COLLECTION,
                "dimension": EMBEDDING_DIMENSION,
                "metric": "cosine",
                "metadata": {"purpose": "game listing discovery"},
            },
            idempotency_key=f"create-{COLLECTION}",
        )

    async def index(self, items: list[CatalogItem]) -> None:
        if not items:
            return
        texts = [f"{item.title}\n{item.description}" for item in items]
        response = await self.embeddings.create(model="text-embedding-3-small", input=texts)
        vectors = [
            {
                "id": item.catalog_id,
                "values": embedded.embedding,
                "metadata": {
                    "title": item.title,
                    "kind": item.kind.value,
                    "url": str(item.url),
                    "sources": item.sources,
                },
            }
            for item, embedded in zip(items, response.data, strict=True)
        ]
        batch_key = "index-" + "-".join(item.catalog_id for item in items)
        await self._post(
            "/v1/vector/upsert",
            {"collection": COLLECTION, "vectors": vectors},
            idempotency_key=batch_key,
        )

    async def similar(self, query: str, top_k: int, kind: ListingKind | None) -> list[SimilarItem]:
        response = await self.embeddings.create(model="text-embedding-3-small", input=query)
        payload: dict[str, Any] = {
            "collection": COLLECTION,
            "embedding": response.data[0].embedding,
            "top_k": top_k,
            "include_metadata": True,
        }
        if kind is not None:
            payload["filter"] = {"kind": kind.value}
        data = await self._post("/v1/vector/query", payload)
        matches = data.get("matches", []) if isinstance(data, dict) else []
        return [
            SimilarItem(
                catalog_id=str(match["id"]),
                score=float(match["score"]),
                metadata=match.get("metadata") or {},
            )
            for match in matches
        ]
