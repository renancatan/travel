# Travel Project

AI travel content copilot for digital nomads.

The goal of this repo is to help turn messy trip media from phone, drone, and action camera into social-ready content with much less manual sorting. The first version will stay narrow: ingest media, shortlist the best assets, generate a few post/reel options, and update a live travel map after approval.

## V1 Scope

- Upload media from desktop or mobile.
- Group and score photos/videos from one trip or album.
- Suggest:
  - carousel post
  - short reel
  - story-ready media set
- Generate caption and place/category suggestions.
- Update a public travel map after the user approves the selection.
- Allow "update map only" even if the user does not publish anything.

## Principles

- Personal tool first, broader product second.
- Human approval before publishing.
- AWS-first deployment for learning and real-world ops.
- Keep the architecture portable so storage, queue, and hosting can change later.
- Do not rebuild the old app in place.

## Repo Layout

- [TODO.md](/home/renancatan/renan/projects/travel/TODO.md)
- [PROJECT_LOG.md](/home/renancatan/renan/projects/travel/PROJECT_LOG.md)
- [docs/architecture.md](/home/renancatan/renan/projects/travel/docs/architecture.md)
- [docs/deployment.md](/home/renancatan/renan/projects/travel/docs/deployment.md)
- [docs/business-decisions.md](/home/renancatan/renan/projects/travel/docs/business-decisions.md)
- [apps/web/README.md](/home/renancatan/renan/projects/travel/apps/web/README.md)
- [services/api/README.md](/home/renancatan/renan/projects/travel/services/api/README.md)
- [workers/media/README.md](/home/renancatan/renan/projects/travel/workers/media/README.md)
- [infra/aws/README.md](/home/renancatan/renan/projects/travel/infra/aws/README.md)
- [legacy/README.md](/home/renancatan/renan/projects/travel/legacy/README.md)

## Legacy App

The old map-based project was archived under:

- [legacy/travel-v0/README.md](/home/renancatan/renan/projects/travel/legacy/travel-v0/README.md)

It is preserved for reference, data migration ideas, and feature archaeology, but it is no longer the base for the new version.

## Local Run

Reuse the existing working LLM and AWS setup from the sibling analytics project without copying secrets into this repo:

```bash
cd /home/renancatan/renan/projects/travel
source scripts/source_local_env.sh
python -m uvicorn services.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

Or use the helper:

```bash
cd /home/renancatan/renan/projects/travel
./scripts/run_api_dev.sh
```

`.env.example` is intentionally blank for secret values. Real provider and AWS credentials are loaded at runtime by `scripts/source_local_env.sh` from your existing analytics project setup.

## Web App

Run the browser UI:

```bash
cd /home/renancatan/renan/projects/travel
./scripts/run_web_dev.sh
```

Then open:

```text
http://127.0.0.1:3000
```

The current UI supports:

- `New album` mode that must create the album before upload unlocks
- `Existing album` mode that uses the sidebar selection as the upload target
- drag-and-drop upload from the browser
- album list and selection
- preview cards for uploaded images
- metadata review for ingested media
- AI album analysis with likely categories, trip summary, and caption ideas

## Smoke Test

Once the API is running:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/runtime

curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Give me 3 short caption ideas for a cave travel post.","model":"ggl2"}'
```

Or use:

```bash
./scripts/smoke_test_api.sh
```

## Upload Smoke Test

The current first real vertical slice is album creation plus local file ingestion. Uploads currently use a raw request body with an `X-Filename` header so we do not depend on multipart tooling yet.

Example:

```bash
ALBUM_JSON=$(curl -sS -X POST http://127.0.0.1:8000/albums \
  -H "Content-Type: application/json" \
  -d '{"name":"Petar Weekend","description":"First ingestion test"}')

ALBUM_ID=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["id"])' <<< "$ALBUM_JSON")

cat > /tmp/travel-smoke.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1500" viewBox="0 0 1200 1500">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#165f77"/>
      <stop offset="60%" stop-color="#db7a34"/>
      <stop offset="100%" stop-color="#f4d7a1"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="1500" fill="url(#bg)"/>
  <text x="90" y="230" fill="#fff8ee" font-size="94" font-family="Georgia, serif">Travel Project</text>
  <text x="90" y="330" fill="#fff8ee" font-size="42" font-family="Georgia, serif">Visible smoke-test artwork</text>
</svg>
SVG

curl -X POST "http://127.0.0.1:8000/albums/${ALBUM_ID}/upload" \
  -H "Content-Type: image/svg+xml" \
  -H "X-Filename: travel-smoke.svg" \
  --data-binary @/tmp/travel-smoke.svg

curl "http://127.0.0.1:8000/albums/${ALBUM_ID}"
```
