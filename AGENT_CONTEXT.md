# Agent Context

This file is the working memory for the `travel` repo. Before making non-trivial changes, review this file to re-ground on product scope, architecture, current state, and open decisions. After each meaningful instruction set is completed, update this file.

For a compact cross-chat handoff, read `INSTRUCTIONS.md` first. This file remains the rolling working memory and may contain more incremental details.

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
- ranked cover, carousel, and reel candidates
- a first-pass reel plan with ordered beats, suggested durations, and edit notes
- renderable AI reel variants for compare-first review
- manual reel editing only after one rendered AI reel is chosen
- a downloadable reel draft manifest with caption, output settings, steps, selected assets, and a render-ready `ffmpeg` spec
- a local reel render action that can produce a saved preview/download with preserved source audio on video beats when `ffmpeg` is available
- post-render reel-look controls that sit below the rendered reel preview
- a first-pass manual reel editor that can reorder beats, swap assets, edit title/caption/cover, and adjust clip windows or durations before save/render
- a simple reel-wide audio mode toggle so the user can preserve source audio or mute the reel before rendering
- draft-step reordering now supports drag-and-drop in addition to move up/down buttons
- still-image beats now support framing controls so the user can fit the full image or fill/crop the frame and adjust focus before rendering
- draft-step editing now includes a live per-step preview so image framing and video clip-window changes are visible before re-render
- reel drafts now support saved alternate versions so the user can snapshot multiple edit ideas, reload them into the editor, and delete old versions

### Step 5

Map draft:

- separate map AI call, distinct from the album-review AI
- default flow is: choose the right reel first, then use that chosen reel as the main map context
- optional `Map only` mode exists when the user wants to build the map stop without tying it to a chosen reel yet
- map AI accepts a direct user prompt such as `petar caves`
- prompt should outweigh weak GPS when it clearly implies the place
- map generation should stay a single LLM flow for now, not a separate agent-style pipeline
- edit title, group, icon, coordinates, country, state, city, region, location label, and summary
- save the map draft back onto the album
- open the current draft in OpenStreetMap for a quick location sanity check

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
- `POST /albums/{album_id}/reel-draft`
- `POST /albums/{album_id}/map-entry/auto`
- `POST /albums/{album_id}/map-entry/ai`
- `PATCH /albums/{album_id}/map-entry`
- `GET /map-entries`

Current backend capabilities:

- local album persistence
- local media storage
- image metadata extraction including JPEG EXIF timestamp, device, and GPS when present
- first-pass map draft persistence attached directly to each album record
- separate map-AI generation that can resolve place hierarchy and map grouping from prompt + reel + album context
- the dedicated map AI now defaults to the Azure/OpenAI `gpt4o` route instead of Gemini
- map entries now pass through a first-pass canonical place normalizer:
  - country/state/city/region display values are cleaned after the map AI step
  - stable slugs are derived for those fields
  - a logical storage path preview is generated for future blob/S3 organization
- ISO-based video parsing for common `mp4` / `mov` style uploads without external tooling
- browser-side video frame sampling so uploaded clips can provide real visual samples to the AI review flow
- optional `ffprobe` enrichment and optional `ffmpeg` thumbnail generation when those binaries are available
- heuristic media scoring for images and videos
- deterministic curation output for cover, carousel, and reel candidates
- deterministic reel-plan output that turns reel candidates into a short ordered sequence
- deterministic reel-draft export output that can later feed a real render worker
- reel plans now choose a `video_strategy` (`hero_video`, `multi_clip_sequence`, or `still_sequence`) and attach clip windows to video beats
- reel drafts now include a render-ready `ffmpeg` spec with working directory, concat file, normalized clip outputs, and copyable shell commands
- a reel renderer now turns that render spec into a saved `.mp4` preview/download when `ffmpeg` is available
- rendered reels now preserve source audio on video beats and use silent filler audio for still-image beats or silent clips
- duplicate-style shot grouping based on filename/media patterns
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
- curation panels for cover picks, carousel picks, reel candidates, and shot groups
- media card preview grid
- image review cards now show captured time, source device, and GPS when available
- richer video review cards with poster support when thumbnails exist
- video cards now show how many AI-readable sampled frames were attached when browser sampling succeeded
- delete actions for the current album and for individual media items
- local new-album draft persistence in the browser while the user is still editing
- duplicate-name blocking for new albums before creation
- AI review is now cached in each album record and rehydrated when albums are loaded again
- older albums without cached AI review now lazily rebuild that cache the first time they are opened in `Existing album` mode
- reel draft export UI now avoids showing raw storage paths and long overflowing identifiers in the main review cards
- reel draft export UI now shows the render backend, working directory, output paths, render notes, render clips, and copyable shell commands
- the UI now includes `Render reel`, an inline rendered preview, and `Download rendered reel` when a finished render exists
- a new Step 5 map draft panel can now:
  - switch between `Use chosen reel` and `Map only`
  - send a dedicated prompt into a separate map-AI call
  - show/edit group, icon, coords, country, state, city, region, location label, and summary
  - show the current canonical place hierarchy and storage-path preview
  - save that draft back to the album
  - open the current draft in OpenStreetMap
  - open the new `/map` public-style preview page directly from Step 5
- the `Render reel` button is now disabled when `ffmpeg` is unavailable, so the app no longer fires avoidable `409` render requests on machines without local media tooling
- AI reel variants can now be rendered as real compare previews before manual editing starts
- the detailed reel editor now stays locked until one rendered AI reel is chosen
- reel-wide look controls now live in the selected compare-reel card instead of inside the step editor
- there is now an `Auto filter` preset for the final reel look:
  - brightness `0`
  - contrast `1.2`
  - saturation `1.2`
- the selected compare-reel card now exposes the most important immediate actions:
  - download compare reel
  - render final reel
  - download final reel when available
- when a compare reel is selected for editing, that chosen reel card is now the single active workspace:
  - it shows the compare reel first
  - after final render, it swaps to the current rendered output for that same draft
  - the duplicate lower rendered-reel preview is hidden for that selected-variant flow to avoid two unrelated reel surfaces
- the `/map` page now persists the chosen compare-reel variant id into the saved map entry:
  - selected stops can reopen with the chosen rendered compare reel as the main media
  - older entries without that saved variant id fall back to a best-effort draft-family match
- the `/map` Leaflet surface now forces extra relayout after load, resize, and first camera move so the page no longer depends on a manual click/reset before the basemap appears
- uploaded source videos that the browser cannot decode inline now fall back to a clearer preview state instead of only surfacing a vague browser file-read/permission-style error:
  - upload still succeeds
  - browser-side AI frame sampling is skipped with a more explicit unsupported-codec/device-track warning
  - server-side thumbnail extraction now explicitly maps the primary video stream so DJI-style sidecar tracks are less likely to interfere
- large uploads no longer require buffering the whole source file in browser memory first:
  - the frontend now streams the `File` directly in `fetch` instead of calling `file.arrayBuffer()`
  - the API now streams the request body to disk instead of calling `await request.body()`
  - metadata refresh for saved videos now avoids rereading multi-gigabyte files fully into memory
- long-form auto reel variants no longer collapse to a single compare reel as easily:
  - creative profiles now carry a clip-window offset so `Balanced`, `Motion-first`, and `Scenic` can land on different windows from the same long source video
  - this keeps heavy single-video albums closer to the intended "three distinct story candidates" behavior
- heavy long-form reels now bias much harder toward video when the source is a truly long clip:
  - for `45s+` reels built from `10m+` videos, the planner now prefers video candidates more aggressively
  - retiming now caps still-image beats to quick support shots instead of letting them stretch into long holds
  - the saved Pamilacan `27m` dive album now validates around `53.8s` video and `5.7s` to `6.0s` images on the generated `60s` variants
- map place matching is now stricter and safer:
  - place hints now match normalized tokens instead of loose substrings, so album names like `petar50` no longer accidentally trigger the `petar` location hint
  - invalid `0,0` style GPS metadata is ignored instead of counting as real coordinates
  - `Pamilacan` now has a curated place hint so prompt + filenames can resolve to a stable Bohol/Visayas location even without trustworthy media GPS
- the main media review grid now handles long filenames and AI notes more gracefully:
  - long media names wrap instead of forcing the card wider than the workspace
  - AI analysis and processing-note text now wraps instead of clipping off-screen in the right panel
- the `/map` viewport now stays anchored to the visited context:
  - empty-map-space drift is reduced by constraining panning/zoom-out to the active visited bounds
  - when a stop is selected, the bounds focus on that stop's city cluster when possible, otherwise its country cluster
  - this keeps country-level browsing much closer to the intended "walk around where we've actually been" behavior

## Current State

### Confirmed working

- API smoke test passes
- Next.js production build passes
- the heavy-video reel tuning currently validates on the saved Pamilacan album:
  - `auto-60-0-balanced`: `53.8s` video / `5.7s` image
  - `auto-60-0-motion`: `53.8s` video / `5.7s` image
  - `auto-60-0-scenic`: `53.9s` video / `6.0s` image
- album creation, upload, description generation, description save, and AI review all work end to end
- local reel rendering now works end to end on this machine with installed `ffmpeg`
- local reel rendering now exports a final `.mp4` with both H.264 video and AAC audio when the draft includes video beats
- map draft generation and save now work against real album GPS metadata
- map draft generation is now its own AI flow and no longer depends only on GPS media
- the live `/map` page was re-verified in headless Chrome after hydration:
  - it no longer starts as a blank gray surface in the tested flow
  - the selected stop now triggers rendered-variant media requests instead of only raw-media fallback requests

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
- AI review responses now include first-pass best-pick candidates and duplicate-style grouping
- newly uploaded videos can now attach sampled browser frames, so AI review is no longer limited to video metadata only
- AI review responses now include a step-by-step reel plan with ordered beats, estimated timing, and edit guidance
- AI review responses now include a downloadable reel draft JSON with caption, target output settings, step list, and source assets
- cached AI review and description metadata are now persisted in `album.json` instead of living only in browser state
- reel plans and reel draft exports now expose video clip windows so one strong video can drive multiple beats instead of every strong video being treated as a separate flat pick
- reel draft exports now include a render-ready `render_spec` so the assembly flow is directly actionable even before `ffmpeg` execution is installed locally
- the app can now execute that render spec into a saved output file when `ffmpeg` is present
- the final concat render now explicitly maps both video and audio, so rendered reels keep the expected AAC track instead of dropping back to silent output
- duplicate image filenames no longer appear twice on media cards
- reel drafts can now be edited in the UI, saved back to album cache, and rendered from the edited version
- re-rendering an edited reel now uses a staging directory and no longer deletes the newly rendered output when the final saved path is unchanged
- stale rendered-reel metadata is now cleared automatically if the UI asks for a file that no longer exists on disk
- rendered-reel preview and download now include a cache-busting URL tied to `rendered_at`, and the backend serves that content with `no-store` headers so browsers stop reusing old reel bytes after re-render
- manual reel editing now clamps video clip windows and durations to the smaller of the real asset duration and the backend-configured max clip cap, so the editor no longer allows values that later fail at render time
- the new clip-duration clamp has been sanity-checked with a longer video and now behaves cleanly in real use
- manual reel editing now also supports adding extra beats and removing AI-suggested beats before save/render
- reel drafts can now switch between preserved source audio and a fully muted output path before render
- manual reel editing now supports drag-and-drop beat reordering in addition to the move buttons
- manual reel editing now supports still-image framing controls with fill/crop plus horizontal and vertical focus
- compare-first reel selection now works:
  - render compare reels
  - preview the actual rendered variants
  - choose one reel
  - only then unlock detailed editing and final export actions
- saving draft edits or saving a version no longer kicks the user back into the locked compare state for the same album
- the chosen reel workspace now stays visually tied to the same draft the user is editing below, so render/filter/export actions no longer feel split across two separate reel previews
- Step 5 map drafting is now a dedicated AI step:
  - prompt-driven
  - chosen-reel-aware
  - map-only capable
  - with state/city/group support in the saved schema
  - but place canonicalization is still first-pass and needs a stronger normalization pass before public map scale
- current map entries now also persist canonical path fields:
  - `country_slug`
  - `state_slug`
  - `city_slug`
  - `region_slug`
  - `location_slug`
  - `title_slug`
  - `storage_path`
- there is now a first public-style map preview page at `/map`:
  - it fetches saved albums with map entries
  - keeps owner-side filters for country, city, and group
  - keeps a slimmer saved-stop rail on the left
  - restores a larger, more dominant map stage so the user is already "inside the map view"
  - uses a cleaner light basemap instead of the busier default OSM look
  - renders a real interactive Leaflet marker map instead of only a raw OSM handoff
  - uses de-collided display positions for exact / near-identical stop coordinates so markers do not stack directly on top of each other
  - clicking a marker focuses that stop and updates one floating place card tied to the map itself
  - clicking empty map space, or using `Unselect`, clears the current focused place
  - the selected place card now lives inside the map surface and shows icon, summary, GPS link, and chosen media with videos first and images after them
  - but the real legacy target interaction is still richer:
    - custom category icons directly on the interactive map
    - clicking a place opens an expanded modal/card
    - that expanded place view shows images and videos inline
    - the next step is to make the selected-place experience feel more like a real media expansion than only a stronger floating info card
    - this behavior lives in the archived reference files:
      - [legacy/travel-v0/public/js/map.js](/home/renancatan/renan/projects/travel/legacy/travel-v0/public/js/map.js)
      - [legacy/travel-v0/public/index.html](/home/renancatan/renan/projects/travel/legacy/travel-v0/public/index.html)
      - [legacy/travel-v0/public/css/styles.css](/home/renancatan/renan/projects/travel/legacy/travel-v0/public/css/styles.css)

### Operational note

- The local API is expected on `http://127.0.0.1:8000`
- If the browser shows fetch errors again, first verify the API with `/healthz` before assuming the frontend flow is broken
- `GET /runtime` now reports media tooling availability so it is easy to see whether `ffmpeg` / `ffprobe` are installed locally
- `GET /runtime` now also exposes reel-variant preset metadata so the frontend duration selector can stay in sync with the backend presets
- map-entry drafts are stored in each album `album.json` for now, and `GET /map-entries` is the first public-map foundation endpoint
- the new map AI is intentionally separate from the album-review AI so map resolution can evolve independently of caption/reel analysis
- the dedicated map AI model is now controlled from one place:
  - [map_ai_settings.py](/home/renancatan/renan/projects/travel/services/api/app/core/map_ai_settings.py)
  - default alias: `gpt4o`
  - optional env override: `TRAVEL_MAP_AI_MODEL_ALIAS`

## Known Gaps

- older videos do not get browser-sampled AI frames automatically; this currently happens during new browser uploads
- no semantic or taste-aware quality scoring yet beyond the new heuristic signal
- no semantic or taste-aware best-shot ranking yet beyond the new deterministic curation pass
- no carousel or reel generation yet
- reel logic now chooses one of:
  - `hero_video`
  - `multi_clip_sequence`
  - `still_sequence`
- this is still heuristic; it does not yet detect the best scene boundaries or extract clips with `ffmpeg`
- real local reel rendering is now validated with `ffmpeg` and `ffprobe`
- rendered output now preserves source audio on video beats and uses silent filler audio elsewhere; richer soundtrack and audio-mixing behavior are still pending
- there is now a simple user-facing mute/remove-audio toggle for reels, but richer soundtrack selection, gain control, and mix rules are still pending
- render attempts now log clearer API-side messages for request, failure, and success, which will help once real `ffmpeg` debugging starts
- manual reel editing is still first-pass:
  - swap assets per beat
  - adjust clip windows and durations
  - edit title, caption, and cover
- the editor now supports add/remove beats, drag-and-drop reordering, audio mode changes, still-image framing, live step previews, and saved alternate draft versions
- the editor now also supports one reel-wide look layer with:
  - brightness
  - contrast
  - saturation
- reel-wide look settings are saved with the draft/version and preview live on the rendered reel before re-render
- `Reset edits` currently resets the local editor to the last saved/applied draft, not all the way back to a fresh AI rebuild; `Refresh AI read` is the closer "start from AI again" action today
- there is also an open UX question around reel draft saving:
  - whether `Save as version` should implicitly apply/save the current active edits
  - whether `Apply draft edits` should remain a separate action or be simplified later
- the first map draft is intentionally local and album-scoped:
  - there is now a first `/map` page plus owner-side country/city/group filters
  - no clustering yet
  - no reverse geocoding yet, so country/region/location labels are still simple heuristic suggestions
- map naming still needs canonicalization work before we trust it as a long-term storage path source:
  - country, state, and city should converge on standard names without us maintaining giant manual lists
  - prompt/description should remain stronger than weak GPS when they clearly identify the stop
  - future blob/S3 layout should be able to use normalized place slugs such as:
    - `user/travel/country/state/city/group/trip-slug/...`
- public map presentation is still minimal:
  - current OpenStreetMap link is mainly a coordinate sanity check
  - `/map` is now the first richer stop-preview surface with a real map layer
  - later public map work should still add:
    - image/reel overlays directly on the interactive map layer
    - legacy-style clickable category icons that open a media-rich place modal/card
    - the current floating place card is better than the previous split layout, but it is still a first pass
    - the next interaction step should move even closer to a true modal/card expansion directly on marker click
- AI now generates first-pass reel variants at different target lengths:
  - `Quick 10s`
  - `Story 15s`
  - `Extended 30s`
- users can now choose the reel-target mode before running AI review:
  - `Auto`
  - `10s`
  - `15s`
  - `30s`
  - `Custom range`
- `Auto` has been rebalanced to be more conservative:
  - it now prefers `10s` or `15s` for most albums
  - `30s` is intended to be a rarer choice that needs genuinely richer content
- AI-generated reel ordering is now stricter:
  - all video snippets come first
  - repeated snippets from the same source video stay grouped together
  - still images only appear after the video block ends
- for a selected target length, AI can now fan out into same-length creative variants such as:
  - `Balanced`
  - `Motion-first`
  - `Scenic`
- users can load one suggested AI variant into the editor before continuing with manual edits
- AI variant compare mode now renders the candidate reels themselves first, so the user can choose from real outputs before opening the detailed editor
- there is now also a UX note to revisit later:
  - after selecting a reel target, the current step flow still feels a bit confusing
  - likely direction is still to simplify the post-selection flow even though deeper editing is now delayed until one variant is clearly chosen
- longer hero-video variants now try to spread reused clips across distinct non-overlapping windows instead of repeating the same slice when one strong video is reused several times
- longer variants also now lean on a broader candidate pool and can switch into more still-heavy storytelling instead of overusing one hero video
- the current fixed variant presets now live in one backend file for easier future tuning:
  - [services/api/app/core/reel_variant_presets.py](/home/renancatan/renan/projects/travel/services/api/app/core/reel_variant_presets.py)
- the reel-variant rules are now explicitly split into short-form and long-form policies:
  - short-form keeps the current `10s / 15s / 30s` behavior for ordinary albums
  - long-form uses separate auto-target preferences and can evolve without rewriting the short-form path
  - the activation thresholds and future story-bundle targets are now centralized in the preset module instead of hidden in album-suggestion heuristics
  - `/runtime` now exposes those policy rules for easier debugging and future frontend wiring
- the current reel/media pipeline is still best suited to short and medium clips:
  - browser-side frame sampling and sync review are fine for travel clips in the rough `seconds -> low minutes` range
  - it is not yet the right long-term path for realistic heavy albums such as:
    - 4K diving footage
    - multiple `5m` to `15m` drone files
    - several `1h` action-cam / dive files in one album
  - those heavy cases need a separate async ingest lane instead of trying to push full-length source files through the current interactive path
- the planned heavy-media direction is:
  - keep the original upload untouched
  - generate a smaller proxy/mezzanine version for analysis
  - extract timeline candidates server-side with `ffprobe` / `ffmpeg` and later scene segmentation
  - ask AI to reason over representative frames, clip windows, transcripts, and metadata instead of the full raw video
  - move heavy processing into background jobs so the UI becomes "processing and then reviewing", not "block and wait"
- first-pass heavy-media classification now exists:
  - central rules live in:
    - [services/api/app/core/media_processing_policy.py](/home/renancatan/renan/projects/travel/services/api/app/core/media_processing_policy.py)
  - media items now carry:
    - `processing_profile`
    - `processing_profile_label`
    - `processing_recommendation`
    - `analysis_strategy`
    - `video_duration_tier`
    - `video_resolution_tier`
  - current profiles are:
    - `standard`
    - `long_form`
    - `heavy_async`
  - the frontend media cards now display this profile so we can validate behavior before building the real worker
  - `/runtime` exposes `media_processing_rules`
  - this does not yet route heavy videos into a background job; it only makes the classification explicit and debuggable
- for longer single-source videos, the product direction is shifting from "one reel suggestion" to "multiple distinct story candidates":
  - for heavy clips, AI should be able to propose several clearly different reels from one source video
  - these should be different narrative cuts, not tiny variations of the same cut
  - the likely future presets for long-form sources are:
    - one user-selected target length with multiple distinct reels
    - or one AI-chosen best target length with multiple distinct reels
  - avoid combinatorial explosion by not defaulting to "3 durations x 3 variants each"
  - likely future long-form-friendly target lengths:
    - `15s`
    - `30s`
    - `60s`
  - long videos should emphasize distinct chapter/story extraction first, then reel generation second
- remaining follow-up work for reel variants is:
  - make `Auto` smarter about content richness and pacing instead of relying on the current first-pass heuristic
  - improve `Custom range` so it picks stronger cuts inside user-provided windows such as:
    - `10s to 12s`
    - `10s to 15s`
    - `15s to 25s`
    - `35s to 60s`
  - keep improving same-length variants so they feel more meaningfully different in practice
  - support even stronger creative-angle differences and audience targets
  - only then expose deeper editing for the selected reel variant(s)
- no live map update flow yet
- no S3/R2 abstraction wired for production storage yet
- no auth or multi-user support yet
- map-side filters are explicitly for the owner's own place-memory browsing:
  - country
  - city
  - group
  - later personal rating/score
  - this should not drift toward a public review-platform model

## Immediate Next Steps

1. Validate real video upload behavior in the browser with an actual `mp4` or `mov`.
2. If needed, tighten any remaining new-album state leaks during real interaction.
3. Validate that sampled video frames improve AI review quality on real clips.
4. Validate the cached AI review rehydration across a full page refresh with older albums.
5. Validate the reel draft export against a few real mixed albums.
6. Re-test manual draft edits plus re-render on real albums to confirm preview and download always use the newest reel bytes after clip-window changes.
7. Improve clip-window logic so `multi_clip_sequence` albums split across the best video moments more intelligently.
8. Improve travel-specific scene tagging beyond generic labels.
9. Improve the curation scoring so it reflects actual aesthetic quality better.
10. Improve audio handling beyond source-audio preservation with soundtrack selection, gain control, and mix rules.
11. Continue expanding the reel editor with alternate saved draft versions.
12. Validate the new AI reel variants across 10s / 15s / 30s albums and refine how different they feel in practice.
13. Keep improving same-length creative variant separation and audience targeting.
14. Keep refining the compare-first reel flow now that deeper editing is gated behind selecting the desired reel variant.
15. Revisit whether `Save as version` and `Apply draft edits` should be merged into a simpler action model later.
16. Replace the current first-pass `/map` stop interaction with the richer legacy pattern:
   - category-specific icons on the map itself
   - click marker to open the place
   - expand images and videos directly from that place interaction
17. Keep refining the owner-side map browsing flow:
   - stronger country/city/group filters
   - later personal score/rating filters for the user's own places
   - keep the mental model as "my travel memory explorer," not "public place reviews"
18. The `/map` page now prefers the chosen reel preview or final rendered reel over raw source clips when one is available, and it forces an initial Leaflet relayout to avoid the blank white first paint.
19. Design the heavy-video ingest lane before promising real long-form diving support:
   - define thresholds for `light` vs `heavy` video handling
   - start by testing server-side processing on `5m` to `15m` 4K files
   - then validate `30m+` handling
   - only after that move to realistic worst-case albums like `3 x 1h 4K` dive files plus drone/mobile footage
   - make heavy analysis asynchronous with worker jobs, proxy generation, and timeline summaries instead of browser-only sampling
20. Define the long-form reel business/product rule for heavy videos:
   - for clips above the short-form threshold, do not stop at one reel suggestion
   - generate multiple clearly different story candidates from the same source video
   - keep those candidates non-overlapping enough to feel meaningfully different
   - likely UX:
     - user picks a target length and gets `3` distinct reels
     - or AI picks one best target length and still gives `3` distinct reels
   - reserve "all durations and all variants" for an advanced mode later

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
- validate browser video frame sampling on real travel clips
- validate EXIF / GPS display with real phone photos
- improve scene classification beyond generic labels
- add richer metadata extraction
- validate ranking and grouping behavior with real travel albums
- validate cached AI review persistence across reloads and older albums
- validate the new reel-plan output with real albums and mixed media
- validate the reel-draft export with real albums and mixed media
- validate the new reel `render_spec` output with real albums and mixed media
- validate rendered reel quality with real albums and mixed media
- validate the new mute/remove-audio toggle with real albums and mixed media
- validate the new AI reel selector and variants together:
  - `Auto`
  - `Quick 10s`
  - `Story 15s`
  - `Extended 30s`
  - `Custom range`
- validate that 15s / 30s hero-video variants no longer reuse the same clip window repeatedly
- validate that selected target lengths now produce multiple same-length variants that are meaningfully different:
  - `Balanced`
  - `Motion-first`
  - `Scenic`
- validate the new compare-first workflow:
  - render compare reels
  - choose one rendered reel
  - then open detailed editing
- improve reel selection so videos become:
  - one chosen hero clip
  - or a sequence of selected moments across multiple videos
- validate the new `video_strategy` and clip-window output with real albums that contain 2+ strong videos
- improve rendered reel quality now that the real backend render step is validated
- improve source-audio handling with soundtrack support and mixing controls
- continue expanding manual reel editing beyond the current add/remove/drag-reorder/image-framing controls
- keep improving AI reel variants within the same target length and across stronger creative angles
- show deeper editing controls after the user picks the reel variant(s) they want to keep
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
