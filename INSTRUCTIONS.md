# Travel Project Handoff Instructions

Last updated: 2026-04-23

This is the first file a new Codex chat should read before changing the Travel Project. It summarizes the product goal, architecture, current behavior, major decisions, solved issues, known gaps, and next priorities.

If context is still unclear after this file, read:

- `AGENT_CONTEXT.md` for the rolling working memory.
- `TODO.md` for the task backlog.
- `README.md` for baseline run instructions.

## 1. Project Objective

The Travel Project is a personal-first app for digital nomads and travelers who collect too much media during trips and lose too much time selecting, editing, and posting it.

The original problem was very practical: during travel, the user records with mobile, drone, action camera, and sometimes long-form diving footage. Later, selecting the best clips/images and creating Instagram/social posts becomes so time-consuming that posting stops entirely. The app should reduce that friction by letting AI help pick, organize, edit, and eventually publish/share travel memories.

The original larger idea included:

- multi-source media ingestion from phone, desktop, drone, action camera, GoPro/DJI-style clips, and albums
- AI image/video selection
- AI reel generation
- captions and post suggestions
- optional Instagram/social publishing
- automatic map updates after a post or when the user chooses "map only"
- a live/shareable travel map with custom icons and media-rich place entries
- personal style learning over time

The current v1 is deliberately narrower:

- create or select an album
- upload images and videos
- extract metadata
- run AI review
- generate and render reel candidates
- let the user choose and edit one reel
- create a separate AI-generated map entry from the selected reel/media
- preview saved places in a first public-style map page

The target is not "replace Google Maps" or "compete with Google Reviews." The map is the user's own travel memory explorer: filters by country, city, group/category, and later personal score/rating help the user remember where they went and what they liked.

## 2. Active Repo And Runtime

Active project root:

```text
/home/renancatan/renan/projects/travel
```

Current structure:

- `apps/web` - Next.js frontend.
- `services/api` - FastAPI backend.
- `storage/local` - local persisted albums, media, rendered reels, thumbnails, drafts.
- `legacy/travel-v0` - archived old travel map project used as a visual/interaction reference.
- `docs` - architecture and deployment notes.
- `scripts` - local dev/smoke commands.

Important scripts from repo root:

```bash
./scripts/run_api_dev.sh
./scripts/run_web_dev.sh
./scripts/smoke_test_api.sh
```

Expected local URLs:

- API: `http://127.0.0.1:8000`
- Web: `http://127.0.0.1:3000`
- Map preview page: `http://127.0.0.1:3000/map`

The dev scripts source local environment from the sibling analytics project. Do not commit keys. Secrets and provider credentials should stay in local env/scripts.

## 3. Tech Stack

Current stack:

- Frontend: Next.js / React in `apps/web`.
- Backend: FastAPI in `services/api`.
- Local storage: JSON files and local media under `storage/local`.
- Media tooling: `ffmpeg` and `ffprobe` when installed locally.
- LLM routing: reused from the sibling analytics/copilot project.
- Default album/reel AI path: Gemini/multimodal where available, with fallback behavior.
- Dedicated map AI path: Azure/OpenAI `gpt4o` by default.

Map AI model configuration:

- File: `services/api/app/core/map_ai_settings.py`
- Default alias: `gpt4o`
- Env override: `TRAVEL_MAP_AI_MODEL_ALIAS`

Architecture direction:

- AWS first for learning and real deployment practice.
- Keep core boundaries portable so storage, queue, workers, and publishing adapters can later move to cheaper/free providers.
- Avoid AWS-specific logic in core product/domain logic where reasonable.

## 4. Current Product Flow

### Step 1: Choose Target Album

The user chooses either:

- `New album` - create a new album target.
- `Existing album` - use the sidebar selection.

Important current behavior:

- New album creation is explicit. It should not silently create duplicate albums while the user is typing.
- Duplicate album names are blocked.
- The app keeps local draft state while the user is preparing a new album.
- The upload step stays hidden until a target album exists.

### Step 2: Upload Files

Once a target album exists, the user can drag/drop or select files.

Current behavior:

- Images preview immediately.
- Videos upload and show available metadata.
- Upload clears stale AI-derived data for that album.
- Deleting media clears stale AI-derived state.
- Media cards show metadata, quality signal, GPS where available, and processing profile.

### Step 3: Describe The Album

Description happens after upload, not during album creation.

Modes:

- `Automatic AI` - AI inspects media, filenames, metadata, and available frames to generate an album description.
- `Manual` - user writes and saves the description.

The saved description becomes context for later AI review and map generation.

### Step 4: Review And AI Analysis

This is the current main product surface.

AI review can produce:

- album read
- trip story
- likely categories
- caption ideas
- cover picks
- carousel picks
- reel candidates
- shot groups
- reel plan
- reel draft export
- reel variants

Current reel flow is compare-first:

1. User chooses a reel target: `Auto`, `10s`, `15s`, `30s`, or `Custom range`.
2. AI generates candidate reel variants.
3. The app renders compare previews.
4. User watches actual rendered variants.
5. User clicks `Choose this reel`.
6. Only then detailed editing unlocks.
7. User edits beats, timing, framing, audio, filters, and versions.
8. User renders/downloads final output.

This flow works, but the target -> variant -> editor progression still feels somewhat confusing and needs future simplification.

### Step 5: Map Draft

Map generation is intentionally a separate AI call from album/reel analysis.

Inputs can include:

- user prompt, for example `petar caves`
- selected reel draft and variant
- selected media IDs
- album description and AI review context
- GPS from media when available

Map AI generates/editable fields:

- title
- group
- icon
- latitude
- longitude
- country
- state
- city
- region
- location label
- summary

Important logic:

- Prompt/description should outweigh weak GPS when the text clearly identifies the location.
- GPS should help when it is reliable, but it should not override a clear human prompt.
- A single LLM call is preferred for now. Do not introduce a separate map agent pipeline yet.
- Map entries are stored on the album record for now.

## 5. Backend API Snapshot

Implemented endpoints include:

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
- `POST /albums/{album_id}/reel-draft`
- `POST /albums/{album_id}/map-entry/auto`
- `POST /albums/{album_id}/map-entry/ai`
- `PATCH /albums/{album_id}/map-entry`
- `GET /map-entries`

Runtime endpoint notes:

- `/runtime` reports media tooling availability.
- `/runtime` exposes reel variant preset metadata.
- `/runtime` exposes media processing policy metadata.

## 6. Important Files

Docs and handoff:

- `INSTRUCTIONS.md` - this file.
- `AGENT_CONTEXT.md` - rolling working memory.
- `TODO.md` - backlog.
- `README.md` - basic project instructions.
- `docs/architecture.md`
- `docs/deployment.md`

Frontend:

- `apps/web/app/page.tsx` - main album/reel/map draft UI.
- `apps/web/app/map/page.tsx` - public-style map preview page.
- `apps/web/app/globals.css` - visual styling.

Backend:

- `services/api/app/main.py`
- `services/api/app/routers/albums.py`
- `services/api/app/routers/map_entries.py`
- `services/api/app/models/albums.py`
- `services/api/app/models/suggestions.py`
- `services/api/app/core/file_repository.py`
- `services/api/app/core/media_metadata.py`
- `services/api/app/core/media_processing_policy.py`
- `services/api/app/core/album_suggestions.py`
- `services/api/app/core/reel_variant_presets.py`
- `services/api/app/core/reel_renderer.py`
- `services/api/app/core/map_entries.py`
- `services/api/app/core/map_ai_settings.py`
- `services/api/app/core/map_place_normalizer.py`
- `services/api/app/core/llm_router.py`

Legacy map reference:

- `legacy/travel-v0/public/js/map.js`
- `legacy/travel-v0/public/index.html`
- `legacy/travel-v0/public/css/styles.css`

The legacy app is not the target implementation, but the user liked its "inside the map" feel, custom clickable icons, and media-rich modal/card behavior.

## 7. Reel System - Current Behavior

### Reel Targets

Current target selector:

- `Auto`
- `10s`
- `15s`
- `30s`
- `Custom range`

The earlier `20s` preset was intentionally changed to `15s`. Current fixed set is `10s / 15s / 30s`.

`Auto` should not always choose `30s`. Current direction:

- prefer `10s` or `15s` for most normal albums
- choose `30s` only when the album has genuinely rich enough material
- longer targets need stronger diversity and pacing rules to avoid repeated/boring slices

`Custom range` should eventually let the user say things like:

- choose best reel between `10s` and `12s`
- choose best reel between `10s` and `15s`
- choose best reel between `15s` and `25s`
- choose best reel between `35s` and `60s`

Custom range exists now, but longer ranges still need stronger product/AI behavior.

### Reel Variants

For a chosen target length, AI can create same-length variants:

- `Balanced`
- `Motion-first`
- `Scenic`

The business rule is that these should be meaningfully different. They should not be tiny variations of the same reel.

Current compare-first UX:

- render the variants as real videos first
- user watches them
- user chooses one
- detailed manual editing appears only after that choice

This was built because the user did not want to edit blindly or have to guess from JSON/plans. The user wants to see the actual result first.

### Reel Strategy Values

Reel plans can use:

- `hero_video` - one strong video drives most of the reel.
- `multi_clip_sequence` - multiple videos/images form a sequence.
- `still_sequence` - mostly images.

The app currently supports rendering all three styles.

### Ordering Rules

Important reel ordering rule from the user:

- Videos should come first.
- If the same source video is used multiple times, its snippets should stay grouped together.
- Images should always come after video scenes.

Avoid awkward ordering like:

```text
video A scene 1
video A scene 2
image
video A scene 3
```

Better:

```text
video A scene 1
video A scene 2
video A scene 3
image
image
```

### Manual Reel Editor

After one compare reel is chosen, the editor supports:

- add beats
- remove beats
- drag reorder
- move up/down
- swap assets
- edit role/title
- edit duration
- edit video clip start/end
- clamp video duration to real media duration and backend max cap
- image fill/crop mode
- image horizontal focus
- image vertical focus
- live per-step preview
- save alternate versions
- load/delete versions
- render/re-render
- download draft JSON
- download final rendered reel

Known UX issue:

- `Apply draft edits` and `Save as version` both exist.
- There is an open question whether `Save as version` should also apply/save active edits.
- Do not spend time redesigning this unless the user asks. It is noted as a future UX cleanup.

### Rendering

Rendering uses `ffmpeg` locally when available.

Render behavior:

- normalize clips to `1080x1920`
- render at `30fps`
- use H.264 video
- preserve source audio on video beats when requested
- add silent filler for image beats or silent clips
- concatenate normalized clips
- output final `.mp4`

Audio modes:

- keep source audio when useful
- mute/remove audio

Current audio is simple. Soundtrack selection, gain control, voice/music mixing, and audio ducking are not implemented yet.

### Post-render Look Controls

Filters live after a reel exists, not before.

Current reel-wide controls:

- brightness
- contrast
- saturation

Auto filter preset:

- brightness `0`
- contrast `1.2`
- saturation `1.2`

These controls are reel-wide, not per-step. That was intentional to keep v1 simple.

## 8. Heavy Video And Long-form Business Rules

This is a critical future area because the user's real footage can be very heavy:

- diving: sometimes `3 x 1h` videos, potentially 4K
- drone: often 4K, commonly 5 to 7 minutes, sometimes 5 to 15 minutes
- mobile/action camera: mixed shorter and longer clips

The current interactive/browser-friendly path is fine for:

- images
- short videos
- low-minute travel clips

It is not enough for:

- 1 hour 4K diving videos
- multiple long raw clips in one album
- large mixed-device albums

### Current Heavy-video Status

First-pass classification exists, but real async processing does not.

File:

```text
services/api/app/core/media_processing_policy.py
```

Current media processing profiles:

- `standard`
- `long_form`
- `heavy_async`

Media items can carry:

- `processing_profile`
- `processing_profile_label`
- `processing_recommendation`
- `analysis_strategy`
- `video_duration_tier`
- `video_resolution_tier`

The UI shows the processing profile on media cards. `/runtime` exposes the policy rules.

This only classifies media. It does not yet route heavy media to a worker.

### Future Heavy-video Processing Path

For heavy videos, do not try to have AI inspect the raw full video in the normal request path.

Planned path:

1. Keep original upload untouched.
2. Generate a smaller analysis proxy/mezzanine.
3. Run `ffprobe` metadata extraction.
4. Extract thumbnails/keyframes/contact sheets.
5. Generate candidate timeline windows.
6. Later add scene detection and/or transcript/audio cues.
7. Ask AI to reason over representative windows, frames, metadata, and summaries.
8. Process in background workers.
9. Show progressive status in UI.

### Long-form Reel Business Decision

For longer videos, the app should not simply generate one reel.

Product direction:

- For heavy/long-form sources, generate multiple distinct story candidates.
- The default should likely be `3` different reels from the source, not `3` tiny variations of the same cut.
- These should be meaningfully different, with low overlap.
- Good future target lengths for long-form:
  - `15s`
  - `30s`
  - `60s`

Avoid combinatorial explosion:

- Do not default to `3 durations x 3 variants`.
- Prefer one of:
  - user picks one target length, app gives `3` distinct reels
  - AI picks one best target length, app gives `3` distinct reels
- "all durations x all variants" can be an advanced mode later.

For long diving/drone footage, the better mental model is:

```text
raw source -> chapters/story moments -> candidate windows -> distinct reels
```

Not:

```text
raw source -> one generic reel
```

## 9. Map System - Current Behavior And Direction

### Current Map Draft Step

Map generation is separate from album/reel AI.

The user can type a prompt such as:

```text
petar caves
```

AI should infer:

- country: Brazil
- state: Sao Paulo
- city: Iporanga
- region: PETAR
- group: caves
- icon: cave

If the media has GPS, use it as evidence. If the prompt/description clearly says a place, it should outweigh weak or generic GPS.

### Canonical Place Normalization

File:

```text
services/api/app/core/map_place_normalizer.py
```

Current normalizer creates display values and slug fields:

- `country_slug`
- `state_slug`
- `city_slug`
- `region_slug`
- `location_slug`
- `title_slug`
- `storage_path`

Important storage direction:

- Display labels and storage slugs should be separate.
- Storage paths should be ASCII-safe and slug-based.
- Avoid path bugs like raw merged strings such as `PETARtravel/`.
- Avoid special character issues in paths. For example, `Sao Paulo` slug should be `sao-paulo`.

Future logical storage hierarchy:

```text
user/travel/country/state/city/group/trip-slug/...
```

Example:

```text
user/travel/brazil/sao-paulo/iporanga/caves/petar-caves/...
```

The app should not require a giant hand-maintained country/city list. We need a pragmatic normalization source later:

- stable country/common names, ideally ISO-backed
- city/state cleanup after the LLM result
- maybe reverse geocoding later when GPS exists
- prompt/description stays stronger than weak GPS for semantic place identity

### Current `/map` Page

Current `/map` page:

- fetches saved map entries
- shows owner-side filters for country, city, and group
- uses a left saved-stop rail
- shows a large Leaflet map surface
- uses a cleaner light basemap
- de-collides markers with same/near coordinates
- lets the user clear selection
- floating selected-place card shows summary and media
- selected media are videos first, images after
- attempts to show the chosen compare/final reel where available

Known issue/direction:

- The current map is better than the earlier dashboard-like version, but still not the final desired experience.
- The user liked the old legacy "inside the map" feel better.
- The target is a map-first explorer where the map occupies most of the page and custom icons are directly clickable.
- Clicking an icon should open/expand a media-rich place card/modal.
- Exact same coordinates should not stack markers directly; they should spread slightly.
- The user wants final reels first, then source media used to build the reel.
- Owner filters should support personal travel browsing, including country/city/group and later personal score.

Do not treat map ratings as public reviews. They are personal memory filters.

## 10. Major Solved Work

Important completed progress:

- archived old project into `legacy/travel-v0`
- scaffolded new Next.js + FastAPI app
- created album creation and existing-album flow
- hid upload until target album exists
- moved description after upload
- added AI/manual description modes
- added local album persistence
- added media upload and storage
- added image metadata extraction including EXIF/GPS when available
- added video metadata parsing
- added optional `ffprobe` and `ffmpeg` enrichment
- added browser-side video frame sampling
- added album AI review
- cached AI review in album JSON
- rehydrated cached AI review across reloads
- cleared stale AI state after upload/delete
- added album delete and media delete
- blocked duplicate album names
- generated curation picks and shot groups
- generated reel plans
- generated reel draft JSON
- generated render specs
- executed local reel rendering
- fixed re-render stale-file/cache issues
- preserved audio in rendered reels
- added mute/remove audio
- added manual reel editor
- added add/remove/reorder beats
- added drag-and-drop beat ordering
- added still-image framing
- added live per-step previews
- added saved reel versions
- added compare-first AI reel variants
- added selected-reel gating before detailed editor
- added final reel filter/look controls
- added separate map AI flow
- added map draft save/edit
- added canonical map path preview
- added `/map` preview page
- added first-pass heavy-media classification
- centralized reel variant business rules

## 11. Known Gaps

Product gaps:

- No true mobile-first upload polish yet.
- No direct social publishing yet.
- No Instagram API integration yet.
- No post scheduler.
- No auth or multi-user support.
- No Postgres yet.
- No cloud storage abstraction wired into production.
- No real background media worker yet.
- No heavy-video proxy/contact sheet/timeline generation yet.
- No semantic/taste-aware personal style learning.
- No strong image/video aesthetic ranking beyond first heuristics.
- No soundtrack selection/mixing beyond source audio/mute.
- Map UX is still first-pass and not yet close enough to the old desired custom-icon modal experience.

Technical gaps:

- Local storage is JSON/files, not production DB/object storage.
- Heavy video classification exists, but it does not yet trigger async jobs.
- Long-form custom ranges still need stronger validation and AI behavior.
- Compare-first reel UX works but has too many visible concepts.
- `Apply draft edits` vs `Save as version` needs future simplification.
- Map canonicalization is first-pass and should not be treated as final storage truth yet.

## 12. Next Recommended Priorities

Near-term priorities:

1. Keep the current map as acceptable first-pass for now unless the user explicitly asks to revisit it.
2. Start designing and implementing the heavy-video ingest lane.
3. Test with real 5 to 15 minute 4K video before attempting 1 hour diving footage.
4. Add server-side proxy/keyframe/contact-sheet generation.
5. Add background job/status model for heavy processing.
6. Improve reel AI for long-form sources using story/chapter extraction before clip selection.
7. Continue tuning Auto/custom reel target behavior.
8. Simplify the reel target -> variants -> chosen reel -> editor UX later.
9. Improve map modal/custom icon experience later using `legacy/travel-v0` as reference.

Medium-term priorities:

- Add storage adapter interface.
- Add S3 provider first.
- Add queue adapter interface.
- Add SQS worker path first.
- Add Postgres metadata store.
- Add mobile upload polish.
- Add final post candidate model.
- Add export/publish adapters.

## 13. Testing And Validation

Useful local checks:

```bash
./scripts/smoke_test_api.sh
```

```bash
cd apps/web
npm run build
```

When touching Python code, avoid relying on `compileall` if the environment blocks `__pycache__` writes. Use import/AST sanity checks or API smoke tests instead.

Manual feature checks:

- Create a new album.
- Upload images with GPS.
- Upload short videos.
- Generate AI description.
- Analyze album.
- Render compare reel variants.
- Choose one reel.
- Edit timing/framing/audio/look.
- Render final reel.
- Download final reel.
- Generate map entry from chosen reel.
- Save map draft.
- Open `/map`.

Heavy-video validation should be staged:

1. short phone clips
2. 5 to 15 minute 4K clips
3. 30 minute clips
4. 1 hour clips
5. multi-hour mixed albums

Do not jump directly from the current short-video path to `3 x 1h 4K` and expect it to behave well.

## 14. Working Rules For Future Codex Chats

- Always work from `/home/renancatan/renan/projects/travel`, not the sibling analytics repo.
- Read this file, `AGENT_CONTEXT.md`, and `TODO.md` before non-trivial changes.
- Keep v1 practical and personal-use focused.
- Do not promise full autoposting yet.
- Keep AWS-first but portable.
- Keep storage/queue/publishing behind interfaces when adding infra.
- Do not commit secrets.
- Do not revert user changes in a dirty worktree.
- Use `apply_patch` for manual edits.
- Run relevant build/smoke/import checks after code changes.
- Update `AGENT_CONTEXT.md` and/or `TODO.md` after meaningful changes.
- Preserve the current working flow unless intentionally replacing it.
- Be honest about tradeoffs. The user prefers realistic feedback over false positivity.

## 15. Product Philosophy

This project should solve a real travel pain first.

The target user is someone who:

- travels often
- records too much media
- works while traveling
- loses energy when manual editing/posting becomes a second job
- wants useful memories, reels, and maps without spending hours sorting footage

The app should feel like an assistant that helps the user finish:

- "Here are the best story options."
- "Here are three genuinely different reels."
- "Here is the final reel."
- "Here is the map stop with the right place, icon, and media."

It should not become a bloated dashboard full of knobs before the AI has done useful first-pass work.

The best direction is:

```text
AI does the first heavy pass -> user compares real outputs -> user makes small corrections -> final reel/map is saved.
```

For short media, keep the current fast interactive flow.

For heavy media, build a separate async pipeline that respects the reality of travel footage size and lets AI reason from summaries, windows, and story chapters instead of full raw files.
