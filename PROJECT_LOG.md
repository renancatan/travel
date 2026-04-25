# Project Log

This file is the running context for the new Travel Project. It should be updated whenever the architecture, scope, or deployment direction changes in a meaningful way.

## Project Goal

Build a travel content copilot for digital nomads that reduces the time spent sorting trip media, preparing social-ready posts, and updating a live travel map.

## Current Status

As of `2026-04-12`:

- the old app has been archived into `legacy/travel-v0`
- the repo root is now reserved for the new version
- v1 has been intentionally narrowed to avoid repeating the old project's sprawl
- the active architecture direction is AWS-first but portability-aware
- a minimal FastAPI smoke-test app now exists under `services/api/app`
- the repo can reuse the working provider and AWS activation scripts from the analytics project through `scripts/source_local_env.sh`
- a first ingestion slice now works locally:
  - create album
  - upload raw file bytes
  - persist media to local storage
  - fetch album with extracted metadata
- a minimal Next.js review app now exists under `apps/web`
- the browser UI can:
  - force a clear Step 1 -> Step 2 -> Step 3 flow
  - create a new album before upload unlocks
  - upload into an existing album selected from the sidebar
  - preview uploaded images through the API
  - request AI suggestions from the backend for album summary, likely categories, caption ideas, and per-image notes

Recent progress as of `2026-04-25`:

- the local app now has a first heavy-video processing lane with persisted job state, `ffmpeg` proxy generation, server keyframes, and timeline windows
- standard album analysis and proxy/heavy analysis are separate cached outputs so real albums can compare the normal path against the heavier discovery path
- `petar55` testing showed standard reels are still the better default, while proxy analysis is useful for discovering hidden detail beats
- first proxy-quality tuning now gives proxy analysis more video keyframes, cheap keyframe ranking/diversity, and a hybrid cap so proxy reels keep some still/story structure
- `petar56` testing moved the proxy comparison lane to `Proxy Hybrid` variants: keep the standard reel structure and inject a small number of ranked proxy-discovered detail beats
- business/pricing direction now lives in `docs/business-decisions.md`, with long originals treated as temporary processing inputs unless archive storage is explicitly paid or credit-consuming

## Locked Decisions

- Start with a personal/single-user workflow.
- Prioritize media ingestion, scoring, selection, export, and map updates.
- Do not make "full autoposting" the core promise of v1.
- Keep a human approval step before publishing or map updates.
- Design the core around provider interfaces so storage and queue backends can change later.
- Reuse the multi-provider LLM routing ideas from the other project instead of inventing a new routing layer from scratch.
- Keep secrets out of committed files in this repo. Reuse external activation scripts locally instead.

## What The Old App Taught Us

- Hardcoded paths and worker URLs become expensive quickly.
- Manual metadata generation and upload steps do not scale.
- Data models tied to coordinates and hand-maintained files are too fragile.
- A good personal travel tool needs a real ingestion pipeline, not just a map viewer.

## Proposed High-Level Architecture

- `apps/web`
  - user-facing upload, review, and map UI
- `services/api`
  - API for albums, media items, selections, and map entries
- `workers/media`
  - background processing for metadata extraction, scoring, clip generation, and exports
- `infra/aws`
  - deployment notes and AWS-first infrastructure setup
- `shared`
  - contracts, schemas, prompt shapes, and portable interfaces

## Immediate Next Step

The first working vertical slice is now present for local ingestion.

Next build target:

1. improve the review workflow in the web UI
2. add better image and video metadata extraction
3. prepare grouping and scoring logic
4. introduce S3-backed storage behind the same interface
5. begin the first map-entry flow
