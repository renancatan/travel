from __future__ import annotations

from pydantic import BaseModel, Field

class CreateAlbumRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class UpdateAlbumRequest(BaseModel):
    description: str | None = Field(default=None, max_length=1000)


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
    steps: list[ReelDraftEditStepInput] = Field(min_length=1, max_length=12)


class UpdateReelDraftRequest(BaseModel):
    reel_draft: ReelDraftEditInput


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
    detected_at: str
    created_at: str


class RenderedReelResponse(BaseModel):
    draft_name: str
    relative_path: str
    content_type: str
    file_size_bytes: int
    rendered_at: str
    output_width: int
    output_height: int
    fps: int
    estimated_total_duration_seconds: float
    video_strategy: str


class AlbumResponse(BaseModel):
    id: str
    name: str
    description: str | None
    description_meta: dict | None = None
    cached_suggestion: dict | None = None
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
