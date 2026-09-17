from fastapi import Depends, FastAPI, HTTPException

from .infrai_catalog import InfraiCatalog, InfraiError
from .models import AggregateRequest, AggregateResult, SimilarRequest, SimilarResult
from .moderation_queue import aggregate_listings


app = FastAPI(title="Game Listing Counter")


async def catalog_client():
    client = InfraiCatalog()
    try:
        yield client
    finally:
        await client.close()


def _client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code, "message": str(error)})


@app.post("/listings/aggregate", response_model=AggregateResult)
async def aggregate(
    request: AggregateRequest,
    client: InfraiCatalog = Depends(catalog_client),
) -> AggregateResult:
    result = aggregate_listings(request.listings)
    try:
        await client.index(result.published)
    except InfraiError as error:
        raise _client_error(error) from error
    return result


@app.post("/listings/similar", response_model=SimilarResult)
async def similar(
    request: SimilarRequest,
    client: InfraiCatalog = Depends(catalog_client),
) -> SimilarResult:
    try:
        matches = await client.similar(request.query, request.top_k, request.kind)
    except InfraiError as error:
        raise _client_error(error) from error
    return SimilarResult(matches=matches)
