# Business Decisions

Last updated: 2026-04-25

This file captures product, pricing, retention, and cost-control decisions that should guide implementation. It is intentionally separate from engineering architecture so business rules do not get buried inside code.

## Product Promise

The app should help travelers turn large, messy trip footage into useful outputs:

- final reels
- selected frames/stills
- chosen source images
- map memories with rich media
- captions and export-ready post drafts

The default product promise should not be permanent backup storage for every original 4K source video.

Large source videos are processing inputs unless the user explicitly chooses a paid original-archive option.

## Asset Retention Policy

Use three asset classes:

- Permanent assets:
  - final rendered reels
  - selected extracted frames/stills
  - chosen source images
  - map media previews
  - small draft JSON, metadata, captions, and map records
- Temporary originals:
  - large source videos kept only while processing/editing
  - deleted after a defined retention window or after the user confirms final outputs
  - used to generate proxies, reels, frames, and metadata
- Optional archived originals:
  - paid add-on or credit-consuming feature
  - stores original 4K / large source files beyond the temporary retention window
  - priced by GB-month or through the credit system

Draft threshold direction:

- videos under roughly `1m`: keep original by default while v1 is small-scale
- videos from `1m` to `10m`: treat original as temporary by default; store generated outputs and maybe a lightweight proxy
- videos over `10m`, very large files, or heavy 4K footage: temporary original only unless paid archive is enabled

When long 4K footage is processed, the app should usually create lower-resolution analysis/render proxies. Avoid defaulting to permanent original retention for multi-gigabyte source videos.

## Heavy Processing Direction

Heavy video work should move behind a background queue.

A load balancer can route traffic, but it should not be the mechanism that makes long media work safe. Long `ffmpeg` jobs should not block API requests because:

- browser and load-balancer timeouts are shorter than heavy media jobs
- API workers remain occupied while processing
- retries can duplicate expensive work
- deploys or restarts can kill in-flight work
- users need progress/status, not a hanging request

The intended shape is:

1. upload source
2. API creates a processing job
3. worker generates metadata, proxy, frames, candidate windows, and outputs
4. UI shows processing status progressively
5. final reels/frames/map assets become available as they finish

## Pricing Direction

The preferred pricing direction is a low monthly base plus usage credits.

Candidate shape:

- base plan around `$9.99/month`
- includes a monthly credit allowance
- includes a reasonable amount of stored outputs
- does not include permanent archive storage for long original videos by default

Credits should map to user-understandable actions, not raw infrastructure terms.

Good user-facing credit categories:

- long video processing
- 4K/heavy video processing
- extra reel variants
- final reel renders
- original video archive storage
- premium AI analysis

Avoid exposing separate CPU, GPU, LLM, cluster, and storage buckets in normal UI. Track those internally, but present credits as simple creative/processing units.

## Tiering Ideas

Starter / low-cost behavior:

- one generated reel by default for heavy albums
- limited long-video minutes
- generated outputs stored
- long originals temporary only
- extra variants consume credits

Creator behavior:

- more monthly credits
- more compare variants
- longer temporary retention
- more stored outputs

Archive add-on:

- keep original source videos beyond the temporary window
- charge by GB-month or through credits

The current app default of three compare reel variants is useful for creative choice, but production should make variant count entitlement-aware. For heavy videos, additional variants should be a tier feature or credit spend.

## Cost Drivers

Expected production cost pressure, roughly in priority order:

- original video storage, especially 4K and multi-hour source footage
- media egress and playback/download bandwidth
- `ffmpeg` CPU time for proxies, frame extraction, compare renders, and final renders
- retries and duplicate heavy jobs
- LLM token/image costs for album analysis and map generation
- database/object metadata operations

Current implementation note:

- reel variants are generated mostly by deterministic backend logic after one album AI review
- rendering compare/final reels uses `ffmpeg`, not another AI call
- the selected-frame gallery uses `ffmpeg`, not another AI call
- map generation is a separate lightweight AI call
- the first heavy-video processing job uses local FastAPI `BackgroundTasks` plus `ffmpeg`, not a durable queue yet
- heavy-processing outputs currently include a lower-resolution analysis proxy, extracted keyframes, and first-pass timeline windows
- completed server keyframes can be reused by the separate proxy/heavy AI review, which keeps the expensive video understanding path focused on representative stills instead of raw full-length footage
- after testing the 27m Pamilacan 1080p HEVC dive video, full proxy generation looks too expensive for the default FHD path: it produced a `505 MB` proxy and took around `10m`, while direct extraction of `12` keyframes from the original took about `6s`
- pricing/cost assumptions should treat full proxy generation as an optional/heavy operation, not the automatic first step for every long 1080p video
- the app now keeps standard analysis and proxy/heavy analysis as separate cached outputs so real albums can compare quality before deciding whether the heavier path is worth production cost
- `petar55` comparison suggests proxy processing may be valuable as a discovery/ranking aid rather than a separate paid default path: it found underwater details, but standard reels were still stronger as user-facing highlights
- `petar56` reinforced that direction: proxy understood underwater content better, but rendered proxy reels were still not clearly better enough to justify making heavy/proxy analysis the default product path
- the latest product shape is hybrid: keep standard analysis as the default story reel, then use proxy/keyframe work to inject a small number of high-confidence detail beats into separate `Proxy Hybrid` comparison variants
- first proxy-quality tuning is intentionally cheap: use more server keyframes, simple complexity/diversity ranking, and a hybrid reel cap before spending on richer semantic scoring
- current heavy processing now follows a keyframe-first rule: FHD long videos extract server keyframes directly, while full proxy generation is reserved for 4K, high-bitrate, less portable, or downstream-heavy sources
- proxy hybrid beats should be treated as discovered detail inserts, not as a blind replacement for the standard story structure
- processing jobs now record first-pass telemetry for proxy time/size, keyframe time, total processing time, generated output bytes, and temporary original GB-days
- production pricing should not assume proxy analysis is a premium default until telemetry and more real albums show that the heavier lane improves saved/exported reels often enough
- `petar1` after the keyframe-first change supports the current product thesis: standard remains the default taste/story read, while proxy/keyframe work is most valuable as a scout that injects discovered details into selected beats
- heavy classification should use a combined threshold, not duration alone: `>10m`, `>500 MB`, 4K, high bitrate, or expensive/incompatible codecs should move media out of the normal short interactive path
- likely monetization surface is heavy indexing plus extra variants/exports, detail-discovery packs, 4K/high-bitrate processing, credits, and optional original archive retention; durable storage of heavy originals should be opt-in
- local cleanup is part of the heavy-video product safety story: generated render folders can be cleared independently from uploaded originals, and album deletion must remove rendered variants as well as final reels
- `AI Best Pick` should be a pick layer before it becomes a remix layer: compare existing rendered standard/proxy variants, name the best story pick and IG-safe pick, and only recommend a best-of remix later if the winner still has obvious gaps

## Telemetry Before Final Pricing

Before committing to production pricing, add usage telemetry per album/job/user:

- uploaded bytes by media kind
- source video duration, resolution, codec, and size
- original retention class: permanent, temporary, archived
- proxy generation time and output size
- frame extraction count and processing time
- compare variant count and render time
- final render count, duration, output size, and render time
- AI call count by feature: description, album review, map, future premium analysis
- model/provider used
- input/output tokens when available
- number of visual inputs sent to AI
- cache hits/misses for renders and galleries
- queue wait time, worker time, retry count, and failure reason
- storage GB-days and egress bytes

Use telemetry to turn pricing into a measured business decision instead of guessing.
