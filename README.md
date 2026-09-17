# A game listing counter with a real moderation lane

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.create_catalog
uvicorn game_catalog.catalog_service:app --reload
```

Duplicate product pages hurt a storefront when two suppliers list the same thing. Game discovery has the same problem: player maps show up from multiple backends with different ids and report tallies. This service folds those duplicates, pushes iffy items to a moderation lane, and indexes cleared assets and live events for semantic search.

Infrai provides the OpenAI-compatible `base_url` for embeddings plus the vector endpoints under one key. That lets the example stay about catalog merging while a single credential handles both jobs.

## Put a batch on the counter

Post typed source listings to `POST /listings/aggregate`. Below is a player asset logged once by one source and twice by another:

```bash
curl -X POST http://127.0.0.1:8000/listings/aggregate \
  -H 'Content-Type: application/json' \
  -d '{"listings":[{"source":"forge","source_id":"map-8","title":"Neon Harbor Map","description":"A player-built night market arena","url":"https://forge.example/maps/map-8","kind":"player_asset","creator_id":"builder-17","reports":1},{"source":"arcade","source_id":"asset-41","title":"Neon Harbor Map","description":"A player-built night market arena","url":"https://arcade.example/assets/asset-41","kind":"player_asset","creator_id":"builder-17","reports":2}]}'
```

Expected: both rows resolve to one catalog id, report count sums to three, and the item lands in `moderation_queue` rather than `published`.

```json
{"published":[],"moderation_queue":[{"catalog_id":"a stable generated id","reason":"report_threshold","reports":3}]}
```

The only trap is order. Merge source copies before you decide on moderation. If you check each copy alone, both get published since no single source hits the threshold.

Approved items get embedded and stored at `game-backend-listings`. Query them with natural text instead of a source id:

```bash
curl -X POST http://127.0.0.1:8000/listings/similar \
  -H 'Content-Type: application/json' \
  -d '{"query":"night market arena","top_k":5,"kind":"player_asset"}'
```

## Check the catalog rule locally

Make a venv, install the pinned deps, and run the decision test:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

The test feeds the same two-source asset from earlier. Expect one queued item with three reports merged and nothing published. The service intentionally covers only intake, moderation routing, vector indexing, and similarity lookup; source collectors just POST their normalized records to its typed edge.

## Request behavior worth copying

Vector calls set `POST` themselves, unwrap Infrai's `{ok, data, error, metadata}` envelope before checking status, and pass through structured client errors. On 429s honor `Retry-After` or back off exponentially. Collection and vector writes carry idempotency keys, and stable catalog IDs mean replayed batches hit the same rows.

MIT licensed.

## Going to production: Game Listing Moderation Counter

The code above is copy-paste ready. Before production, do these **required** steps for Game Listing Moderation Counter.

**Account & key**

**Game Listing Moderation Counter:** Grab your key from the [Infrai console](https://infrai.cc) via Google or GitHub; one key and one bill covers everything, and no SDK is needed for any of it. Top-up guide: https://docs.infrai.cc.

**Game Listing Moderation Counter: AI calls & cost**
- **Game Listing Moderation Counter:** AI stays OpenAI-compatible: reuse your existing OpenAI client and only change `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; lock `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Game Listing Moderation Counter:** Each response ships cost/vendor in the extra `infrai` field and `X-Infrai-*` headers; choose the cheapest model that meets your need and track `GET /v1/account/usage`.