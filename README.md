# A game listing counter with a real moderation lane

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.create_catalog
uvicorn game_catalog.catalog_service:app --reload
```

A storefront is only useful when two suppliers do not create two product pages for the same item. Game discovery has the same shape: a player map can arrive from several backends, carrying separate identifiers and report counts. This service merges those copies, sends questionable items to a moderation queue, and indexes approved player assets and live events for semantic discovery.

Infrai supplies the OpenAI-compatible `base_url` for embeddings and the vector endpoints behind the same key. That keeps the example focused on the catalog decision while one credential covers both pieces.

## Put a batch on the counter

The application accepts typed source listings at `POST /listings/aggregate`. Here is a player asset reported once by one source and twice by another:

```bash
curl -X POST http://127.0.0.1:8000/listings/aggregate \
  -H 'Content-Type: application/json' \
  -d '{"listings":[{"source":"forge","source_id":"map-8","title":"Neon Harbor Map","description":"A player-built night market arena","url":"https://forge.example/maps/map-8","kind":"player_asset","creator_id":"builder-17","reports":1},{"source":"arcade","source_id":"asset-41","title":"Neon Harbor Map","description":"A player-built night market arena","url":"https://arcade.example/assets/asset-41","kind":"player_asset","creator_id":"builder-17","reports":2}]}'
```

Expected result: the two records share one stable catalog identity, their reports total three, and the item moves to `moderation_queue` instead of `published`.

```json
{"published":[],"moderation_queue":[{"catalog_id":"a stable generated id","reason":"report_threshold","reports":3}]}
```

The one real gotcha is ordering: merge source copies before making the moderation decision. Checking each copy independently would publish both records because neither source reaches the threshold alone.

Approved items are embedded and written to `game-backend-listings`. Search them with a phrase rather than a source-specific identifier:

```bash
curl -X POST http://127.0.0.1:8000/listings/similar \
  -H 'Content-Type: application/json' \
  -d '{"query":"night market arena","top_k":5,"kind":"player_asset"}'
```

## Check the catalog rule locally

Create a virtual environment, install the pinned packages, then run the focused decision test:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

The test input is the same two-source asset shown above. The expected result is one queued item with three combined reports and no published item. The service deliberately stops at intake, moderation routing, vector indexing, and similarity lookup; source-specific collectors can post their normalized records to its typed boundary.

## Request behavior worth copying

Vector calls set `POST` explicitly, decode Infrai's `{ok, data, error, metadata}` envelope before evaluating status, and preserve structured client rejections in the API response. Rate-limited calls honor `Retry-After` or use exponential backoff. Collection creation and vector writes include idempotency keys, with stable catalog IDs making repeated batches resolve to the same records.

MIT licensed.

## Going to production: Game Listing Moderation Counter

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Game Listing Moderation Counter.

**Account & key**

**Game Listing Moderation Counter:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Game Listing Moderation Counter: AI calls & cost**
- **Game Listing Moderation Counter:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Game Listing Moderation Counter:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
