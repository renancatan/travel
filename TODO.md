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
- [ ] Change reel video logic so it does not just list all strong videos:
  - pick one hero video when that is the best reel path
  - or extract/select moments across multiple videos to build one reel
- [x] Export a render-ready reel draft spec with clip windows and `ffmpeg` command planning.
- [x] Add a real local reel render action plus preview/download flow.
- [x] Validate real local reel rendering with installed `ffmpeg`.
- [x] Preserve source audio on video beats during local reel rendering, with silent filler audio for still-image beats.
- [x] Make re-rendering safe when edited drafts reuse the same saved output path.
- [x] Clamp manual video clip editing to the smaller of the real asset duration and the configured reel clip cap.
- [x] Add a simple mute/remove-audio option for rendered reels.
- [ ] Propose:
  - best photo shortlist
  - carousel set
  - short reel cut
  - story set
- [ ] Let the user approve, reject, and remove assets.
- [ ] Generate caption options and hashtags.
- [ ] Let the user choose "publish later" or "map only".
- [ ] Update the map entry once the user confirms the final selection.

## Phase 3: AI and Media Logic

- [ ] Add vision-based scene/category suggestions such as cave, beach, bar, boat, city, food.
- [ ] Add basic aesthetic ranking heuristics before personal-style learning.
- [ ] Add clip extraction with `ffmpeg`.
- [ ] Add soundtrack selection and audio-mixing controls on top of the current source-audio-preserving render path.
- [x] Add first-pass manual reel editing controls:
  - reorder beats
  - swap chosen assets
  - adjust clip windows
- [x] Expand manual reel editing:
  - add beats from extra images/videos
  - remove beats from the AI draft
- [x] Add live per-step previews in the reel editor so image framing and video clip windows are visible before re-render.
- [ ] Continue expanding manual reel editing:
  - richer soundtrack selection and mixing controls
- [x] Save alternate draft versions and load/delete them from the reel editor.
- [x] Add a simple final-reel filter layer before map work:
  - one reel-wide filter control set, not per-step
  - brightness, contrast, saturation
  - apply it at render time and preview it live on the rendered reel
- [x] Move reel-wide look controls to the post-render area so filters are adjusted only after a reel exists.
- [x] Add an `Auto filter` preset for the final reel look:
  - brightness `0`
  - contrast `1.2`
  - saturation `1.2`
- [x] Add first-pass AI reel variants across target lengths:
  - suggest multiple reel drafts such as 10s, 15s, and 30s
  - let the user load one suggested variant into the editor
- [x] Render AI reel variants as real compare previews before manual editing starts.
- [x] Add an explicit reel target selector for AI review:
  - `Auto`
  - `10s`
  - `15s`
  - `30s`
  - `Custom range`
  - centralize preset lengths in:
    - [services/api/app/core/reel_variant_presets.py](/home/renancatan/renan/projects/travel/services/api/app/core/reel_variant_presets.py)
- [ ] Expand AI reel variants further:
  - refine the new `Auto` / `10s` / `15s` / `30s` / `Custom range` selector with better duration-picking logic
  - keep tuning `Auto` so `30s` stays a rare, justified choice instead of the default for medium albums
  - make `Custom range` better at choosing the strongest cut inside a user-provided interval
    - including longer windows like `35s to 60s`
  - keep improving the new same-length variants so `Balanced` / `Motion-first` / `Scenic` feel meaningfully different in practice
  - support stronger creative angles or audience targets across those variants
  - keep longer hero-video variants from feeling repetitive when one strong video is reused several times
  - keep checking that AI-generated reels preserve motion flow:
    - videos first
    - grouped by source video
    - images last
- [ ] Revisit the reel-variant UX:
  - keep variant selection lightweight before showing deeper editing
  - the compare-first flow works now, but the overall target-to-variant-to-editor progression can still be simplified
  - revisit whether the initial compare render should stay a separate action or become the default path more explicitly
- [x] Show advanced reel editing only after the user selects which suggested reel variant(s) they want to keep.
- [ ] Normalize exports for social-ready output sizes and frame rates.
- [ ] Keep all AI decisions explainable in the UI.
- [ ] Log accept/reject feedback for future personalization.
- [ ] Do not fine-tune or train on personal taste in v1.

## Small UI fixes

- [x] Fix duplicate image filename display on media cards.
- [ ] Revisit reel draft save UX:
  - decide whether `Save as version` should also apply/save the active draft edits
  - decide whether `Apply draft edits` should stay separate or be merged into a simpler action model
- [ ] Revisit compare-reel action layout again after real usage:
  - the most important actions now sit in the chosen reel card
  - keep checking whether final export and editor actions still feel too split between the chosen reel card and the lower draft section
  - keep checking whether the chosen reel card and the lower draft editor still need to be visually merged even more
- [ ] Revisit the reel-range / variant flow UX:
  - the current selector-to-editor progression feels a bit confusing
  - simplify the number of visible decisions after picking a reel target
  - likely defer deeper editing until after one variant is clearly chosen

## Phase 4: Map Experience

- [x] Define the map entry schema:
  - title
  - coordinates
  - country
  - region
  - category/icon
  - selected media
  - optional notes
- [x] Add a first-pass album map draft step:
  - auto-build from album GPS, AI categories, and album summary
  - edit title, icon, coordinates, country, region, and summary
  - save the draft back onto the album record
- [x] Add a `GET /map-entries` foundation endpoint for the later public map page.
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
