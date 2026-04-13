# Agent Context

This file is the working memory for the `travel` repo. Before making non-trivial changes, review this file to re-ground on product scope, architecture, current state, and open decisions. After each meaningful instruction set is completed, update this file.

## Project Goal

Build a practical v1 for travel-media curation aimed at digital nomads:

- choose or create an album
- upload images and videos from phone or desktop
- generate or save an album description after upload
- run AI review on the uploaded media
- prepare the foundation for later ranking, grouping, reels, posting, and live map updates

The product is intentionally narrower than the original idea. V1 is about ingestion, review, and AI context building, not full social automation.

## Repo Shape

- Active project root: `/home/renancatan/renan/projects/travel`
- Legacy app archived in: `legacy/travel-v0/`
- Current frontend: `apps/web` using Next.js
- Current backend: `services/api` using FastAPI
- Local storage for now: `storage/local`
- Future infra target: AWS first, but keep architecture portable

## Current Product Flow

### Step 1

Choose target album:

- `New album` creates a fresh target
- `Existing album` uses sidebar selection as the target

### Step 2

Upload files:

- hidden until a target album exists
- drag and drop or file picker
- uploads go straight to the chosen album

### Step 3

Describe the album:

- `Automatic AI` generates a saved description from uploaded content
- `Manual` lets the user write and save the description directly

### Step 4

Review and AI analysis:

- album-level AI summary
- trip-story read
- likely category tags
- caption ideas
- per-image notes when available

## What Has Been Built

### Repo reset and structure

- old project moved to `legacy/travel-v0/`
- new project docs and structure created
- AWS-first but portable architecture documented

### Backend

Implemented in `services/api`:

- `GET /healthz`
- `GET /runtime`
- `POST /ask`
- `GET /albums`
- `POST /albums`
- `DELETE /albums/{album_id}`
- `PATCH /albums/{album_id}`
- `GET /albums/{album_id}`
- `POST /albums/{album_id}/upload`
- `DELETE /albums/{album_id}/media/{media_id}`
- `GET /albums/{album_id}/media/{media_id}/content`
- `GET /albums/{album_id}/media/{media_id}/thumbnail`
- `POST /albums/{album_id}/description/auto`
- `POST /albums/{album_id}/suggestions`

Current backend capabilities:

- local album persistence
- local media storage
- image metadata extraction including JPEG EXIF timestamp, device, and GPS when present
- ISO-based video parsing for common `mp4` / `mov` style uploads without external tooling
- optional `ffprobe` enrichment and optional `ffmpeg` thumbnail generation when those binaries are available
- heuristic media scoring for images and videos
- Gemini-backed LLM routing reused from the sibling analytics project
- multimodal image-aware suggestion path for supported raster images
- metadata fallback path when image analysis is unavailable

### Frontend

Implemented in `apps/web`:

- album sidebar
- new vs existing target flow
- hidden upload step until target exists
- post-upload description mode chooser
- AI review panel
- media card preview grid
- image review cards now show captured time, source device, and GPS when available
- richer video review cards with poster support when thumbnails exist
- delete actions for the current album and for individual media items
- local new-album draft persistence in the browser while the user is still editing
- duplicate-name blocking for new albums before creation

## Current State

### Confirmed working

- API smoke test passes
- Next.js production build passes
- album creation, upload, description generation, description save, and AI review all work end to end

### Recently fixed

- upload step is hidden until a target album exists
- description is no longer part of album creation
- AI description and manual description are real backend-backed actions
- new album flow now resets more explicitly instead of always carrying forward the previous created album target
- the frontend no longer throws a runtime overlay just because `/albums` cannot be fetched; it now surfaces a normal in-app connection error message instead
- albums can now be deleted from the active flow
- individual media items can now be deleted from their review cards
- deleting media clears stale AI-derived state for that album so the review does not lie about current contents
- new album creation is now explicitly confirmed and disabled while the request is in flight
- unfinished new album names are stored as local draft state instead of becoming real albums
- exact duplicate album names are now blocked in both the frontend flow and the API create route
- upload now clears stale AI-derived state so a refreshed album is not reviewed using old suggestions
- video uploads can now expose duration, codec, frame rate, metadata source, and quality signal when the format is supported
- existing JPEG-heavy albums can now backfill EXIF-derived metadata when the full album is opened

### Operational note

- The local API is expected on `http://127.0.0.1:8000`
- If the browser shows fetch errors again, first verify the API with `/healthz` before assuming the frontend flow is broken
- `GET /runtime` now reports media tooling availability so it is easy to see whether `ffmpeg` / `ffprobe` are installed locally

## Known Gaps

- no guaranteed video thumbnail generation on this machine because `ffmpeg` is not installed here
- no `ffprobe`-based video enrichment on this machine because `ffprobe` is not installed here
- no duplicate grouping yet
- no semantic or taste-aware quality scoring yet beyond the new heuristic signal
- no best-shot ranking yet
- no carousel or reel generation yet
- no live map update flow yet
- no S3/R2 abstraction wired for production storage yet
- no auth or multi-user support yet

## Immediate Next Steps

1. Validate real video upload behavior in the browser with an actual `mp4` or `mov`.
2. If needed, tighten any remaining new-album state leaks during real interaction.
3. Improve travel-specific scene tagging beyond generic labels.
4. Add ranking and grouping for near-duplicate shots.
5. Start shaping “best picks” output for carousel vs reel candidates.
6. Decide whether local `ffmpeg` / `ffprobe` installation is worth doing now for thumbnails and richer video reads.
7. Start connecting GPS-bearing albums to the later map flow.

## Working Rules For Future Changes

- Keep v1 narrow and practical.
- Do not expand into full autoposting yet.
- Prefer web-first UX over mobile-specific complexity.
- Keep backend boundaries clean so a future Expo / React Native client can be added later.
- Keep infra abstractions generic where reasonable even if AWS is the first deployment target.
- Do not store real secrets in committed files.
- Reuse the sibling project’s provider environment only through local scripts, not committed credentials.

## Current TODO Snapshot

- validate new-album reset UX
- validate draft + duplicate-blocking UX
- validate album/media deletion UX
- keep existing-album flow simple and low-friction
- validate real video upload UX with common travel formats
- validate EXIF / GPS display with real phone photos
- improve scene classification beyond generic labels
- add richer metadata extraction
- add ranking and grouping logic
- define the first “post candidate” output contract
- start storage abstraction for local vs cloud backends

## Update Ritual

Update this file whenever one of these happens:

- product flow changes
- architecture changes
- major endpoints or screens are added
- a user decision narrows or expands scope
- a significant bug is fixed
- the next-step priority changes
