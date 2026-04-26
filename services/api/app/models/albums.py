from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReelDraftFilterSettingsInput(BaseModel):
    brightness: float = Field(default=0.0, ge=-0.3, le=0.3)
    contrast: float = Field(default=1.0, ge=0.5, le=1.8)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)


class UpdateMapEntryRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    location_label: str | None = Field(default=None, max_length=200)
    group_key: str | None = Field(default=None, max_length=60)
    icon_key: str | None = Field(default=None, max_length=60)
    summary: str | None = Field(default=None, max_length=1000)
    selected_media_ids: list[str] | None = Field(default=None, max_length=8)
    selected_reel_draft_name: str | None = Field(default=None, max_length=160)
    selected_reel_variant_id: str | None = Field(default=None, max_length=120)
    generation_prompt: str | None = Field(default=None, max_length=400)


class GenerateMapEntryRequest(BaseModel):
    user_prompt: str | None = Field(default=None, max_length=400)
    generation_mode: Literal["chosen_reel", "map_only"] = "chosen_reel"
    selected_media_ids: list[str] | None = Field(default=None, max_length=12)
    selected_reel_draft_name: str | None = Field(default=None, max_length=160)
    selected_reel_variant_id: str | None = Field(default=None, max_length=120)
    selected_reel_title: str | None = Field(default=None, max_length=200)
    selected_reel_caption: str | None = Field(default=None, max_length=2200)
    selected_reel_video_strategy: str | None = Field(default=None, max_length=80)


class CreateAlbumRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class UpdateAlbumRequest(BaseModel):
    description: str | None = Field(default=None, max_length=1000)


class RenderCacheCleanupResponse(BaseModel):
    deleted_render_directories: int
    deleted_render_files: int
    deleted_bytes: int
    album_records_updated: int


class AnalysisFrameInput(BaseModel):
    timestamp_seconds: float = Field(ge=0)
    data_url: str = Field(min_length=32)


class UploadAnalysisFramesRequest(BaseModel):
    frames: list[AnalysisFrameInput] = Field(min_length=1, max_length=6)


class ReelDraftEditStepInput(BaseModel):
    role: str = Field(min_length=1, max_length=60)
    media_id: str = Field(min_length=1, max_length=120)
    source_role: str | None = Field(default=None, max_length=60)
    suggested_duration_seconds: float = Field(gt=0)
    clip_start_seconds: float | None = Field(default=None, ge=0)
    clip_end_seconds: float | None = Field(default=None, ge=0)
    frame_mode: str | None = Field(default=None, max_length=32)
    focus_x_percent: float | None = Field(default=None, ge=0, le=100)
    focus_y_percent: float | None = Field(default=None, ge=0, le=100)
    edit_instruction: str | None = Field(default=None, max_length=300)
    why: str | None = Field(default=None, max_length=500)


class ReelDraftEditInput(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    caption: str | None = Field(default=None, max_length=2200)
    cover_media_id: str | None = Field(default=None, max_length=120)
    audio_strategy: str | None = Field(default=None, max_length=80)
    filter_settings: ReelDraftFilterSettingsInput | None = None
    steps: list[ReelDraftEditStepInput] = Field(min_length=1, max_length=12)


class UpdateReelDraftRequest(BaseModel):
    reel_draft: ReelDraftEditInput


class SaveReelDraftVersionRequest(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    reel_draft: ReelDraftEditInput


class GenerateReelFrameGalleryRequest(BaseModel):
    source_variant_id: str | None = Field(default=None, max_length=120)
    frame_count: int = Field(default=10, ge=4, le=20)
    reel_draft: ReelDraftEditInput | None = None


class StartMediaProcessingJobRequest(BaseModel):
    force: bool = False


class MediaItemResponse(BaseModel):
    id: str
    album_id: str
    original_filename: str
    stored_filename: str
    stored_path: str
    relative_path: str
    content_type: str
    media_kind: str
    file_size_bytes: int
    sha256: str
    file_extension: str
    captured_at: str | None
    source_device: str | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    frame_rate: float | None = None
    video_codec: str | None = None
    gps: dict | None
    metadata_source: str | None = None
    thumbnail_relative_path: str | None = None
    thumbnail_content_type: str | None = None
    analysis_frame_count: int = 0
    analysis_frame_timestamps_seconds: list[float] = Field(default_factory=list)
    media_score: float | None = None
    media_score_label: str | None = None
    processing_profile: str | None = None
    processing_profile_label: str | None = None
    processing_recommendation: str | None = None
    analysis_strategy: str | None = None
    is_heavy_video: bool = False
    video_duration_tier: str | None = None
    video_resolution_tier: str | None = None
    heavy_processing_job_id: str | None = None
    heavy_processing_job_status: str | None = None
    heavy_processing_job_stage: str | None = None
    heavy_processing_job_progress_percent: int | None = None
    heavy_processing_job_error: str | None = None
    heavy_processing_job_created_at: str | None = None
    heavy_processing_job_started_at: str | None = None
    heavy_processing_job_completed_at: str | None = None
    heavy_processing_proxy_relative_path: str | None = None
    heavy_processing_proxy_content_type: str | None = None
    heavy_processing_proxy_file_size_bytes: int | None = None
    heavy_processing_strategy: str | None = None
    heavy_processing_proxy_reason: str | None = None
    heavy_processing_proxy_duration_seconds: float | None = None
    heavy_processing_keyframe_duration_seconds: float | None = None
    heavy_processing_total_duration_seconds: float | None = None
    heavy_processing_output_file_size_bytes: int | None = None
    heavy_processing_keyframe_relative_paths: list[str] = Field(default_factory=list)
    heavy_processing_keyframe_timestamps_seconds: list[float] = Field(default_factory=list)
    heavy_processing_keyframe_count: int = 0
    heavy_processing_timeline_windows: list[dict] = Field(default_factory=list)
    source_retention_policy: str | None = None
    source_retention_recommendation: str | None = None
    source_original_temporary_until: str | None = None
    source_retention_estimated_gb_days: float | None = None
    detected_at: str
    created_at: str


class RenderedReelResponse(BaseModel):
    draft_name: str
    relative_path: str
    content_type: str
    file_size_bytes: int
    rendered_at: str
    render_duration_seconds: float | None = None
    output_width: int
    output_height: int
    fps: int
    estimated_total_duration_seconds: float
    video_strategy: str


class ReelFrameGalleryFrameResponse(BaseModel):
    frame_id: str
    frame_number: int
    media_id: str
    original_filename: str
    role: str
    source_timestamp_seconds: float
    clip_start_seconds: float | None = None
    clip_end_seconds: float | None = None
    content_type: str = "image/jpeg"
    relative_path: str


class ReelFrameGalleryResponse(BaseModel):
    gallery_id: str
    source_variant_id: str | None = None
    source_draft_name: str
    frame_count: int
    download_relative_path: str
    frames: list[ReelFrameGalleryFrameResponse]


class MapEntryResponse(BaseModel):
    album_id: str
    album_name: str
    title: str
    latitude: float
    longitude: float
    country: str | None = None
    country_slug: str | None = None
    state: str | None = None
    state_slug: str | None = None
    city: str | None = None
    city_slug: str | None = None
    region: str | None = None
    region_slug: str | None = None
    location_label: str | None = None
    location_slug: str | None = None
    title_slug: str | None = None
    storage_path: str | None = None
    group_key: str
    icon_key: str
    summary: str | None = None
    selected_media_ids: list[str] = Field(default_factory=list)
    selected_reel_draft_name: str | None = None
    selected_reel_variant_id: str | None = None
    generation_prompt: str | None = None
    gps_point_count: int = 0
    source: str = "album_auto"
    created_at: str
    updated_at: str


class AlbumResponse(BaseModel):
    id: str
    name: str
    description: str | None
    description_meta: dict | None = None
    cached_suggestion: dict | None = None
    proxy_cached_suggestion: dict | None = None
    best_reel_pick: dict | None = None
    map_entry: MapEntryResponse | None = None
    rendered_reel: RenderedReelResponse | None = None
    created_at: str
    updated_at: str
    media_items: list[MediaItemResponse]


class UploadMediaResponse(BaseModel):
    album: AlbumResponse
    media_item: MediaItemResponse


class GenerateAlbumDescriptionResponse(BaseModel):
    album: AlbumResponse
    description: str
    likely_categories: list[str]
    analysis_mode: str
    route: dict | None


class RenderReelResponse(BaseModel):
    album: AlbumResponse
    rendered_reel: RenderedReelResponse
