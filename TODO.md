# TODO

## Done

- [x] Archive the old travel app under `legacy/travel-v0`.
- [x] Remove the old GitHub Pages workflow from the active root.
- [x] Reset the repo root for a clean v1 start.

## Phase 1: Foundation

- [x] Scaffold the new web app in `apps/web`.
- [x] Scaffold the API service in `services/api`.
- [x] Add one shared local dev command to boot the project.
- [x] Reuse the existing multi-provider LLM routing pattern from the other project.
- [x] Add `.env.example` and central config loading.
- [x] Define typed request/response schemas for media ingestion, selection, and map updates.

## Phase 2: Core Product V1

- [x] Build album/trip creation flow.
- [x] Support media upload from desktop first.
- [ ] Support direct mobile upload through the web app.
- [x] Store original files plus generated derivatives.
- [x] Extract metadata:
  - capture time
  - duration
  - dimensions
  - GPS when available
  - source device
- [ ] Group similar assets by time, location, and near-duplicates.
- [ ] Score photos for quality and usefulness.
- [ ] Score videos for reel potential and clip-worthy segments.
- [ ] Propose:
  - best photo shortlist
  - carousel set
  - short reel cut
  - story set
- [ ] Let the user approve, reject, reorder, and remove assets.
- [ ] Generate caption options and hashtags.
- [ ] Let the user choose "publish later" or "map only".
- [ ] Update the map entry once the user confirms the final selection.

## Phase 3: AI and Media Logic

- [ ] Add vision-based scene/category suggestions such as cave, beach, bar, boat, city, food.
- [ ] Add basic aesthetic ranking heuristics before personal-style learning.
- [ ] Add clip extraction with `ffmpeg`.
- [ ] Normalize exports for social-ready output sizes and frame rates.
- [ ] Keep all AI decisions explainable in the UI.
- [ ] Log accept/reject feedback for future personalization.
- [ ] Do not fine-tune or train on personal taste in v1.

## Phase 4: Map Experience

- [ ] Define the map entry schema:
  - title
  - coordinates
  - country
  - region
  - category/icon
  - selected media
  - optional notes
- [ ] Build a shareable public map page.
- [ ] Add filters by country, category, and trip.
- [ ] Support manual location correction when metadata is wrong or missing.
- [ ] Keep the map usable even if the user skips social posting.

## Phase 5: Publishing and Export

- [ ] Start with export-ready deliverables before promising full autopost.
- [ ] Add Instagram-friendly export presets.
- [ ] Add safe draft metadata for caption, tags, and location.
- [ ] Research current Creator/Business account publishing limits before implementing autopost.
- [ ] Add social publisher adapters so later we can support Instagram and other networks without rewriting the app core.

## Phase 6: AWS-First Infra

- [ ] Add a storage adapter interface.
- [ ] Implement `S3StorageProvider` first.
- [ ] Add a queue adapter interface.
- [ ] Implement `SqsJobQueue` first.
- [ ] Decide whether first deploy uses:
  - one combined app container
  - separate API and worker services
- [ ] Add Postgres for metadata and map records.
- [ ] Add a background worker for processing uploads and generating derivatives.
- [ ] Add cheap first-stage deployment docs before adding heavier infra.

## Phase 7: Portability

- [ ] Keep storage, queue, and social publishing behind interfaces.
- [ ] Avoid AWS-specific logic inside the core domain layer.
- [ ] Make media processing run locally and in containers the same way.
- [ ] Keep environment variable names generic where possible.
- [ ] Document a future migration path to Cloudflare or other lower-cost hosting.

## Phase 8: Validation

- [ ] Test the app with 3 real trips.
- [ ] Track how long manual curation takes before and after the app.
- [ ] Measure upload time, selection quality, and reel usefulness.
- [ ] Identify what is still annoying after actual travel usage.
- [ ] Re-scope v2 only after real usage data.
