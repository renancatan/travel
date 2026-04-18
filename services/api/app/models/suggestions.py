from __future__ import annotations

from pydantic import BaseModel


class MediaInsightResponse(BaseModel):
    media_id: str | None
    scene_guess: str
    why_it_matters: str
    use_case: str


class CurationCandidateResponse(BaseModel):
    media_id: str
    media_kind: str
    score: float
    reason: str
    group_id: str | None


class ShotGroupResponse(BaseModel):
    group_id: str
    label: str
    representative_media_id: str
    picked_media_id: str
    media_ids: list[str]
    item_count: int


class ReelPlanStepResponse(BaseModel):
    step_number: int
    role: str
    media_id: str
    media_kind: str
    source_role: str
    selection_mode: str
    clip_start_seconds: float | None
    clip_end_seconds: float | None
    suggested_duration_seconds: float
    edit_instruction: str
    why: str


class ReelPlanResponse(BaseModel):
    cover_media_id: str | None
    video_strategy: str
    estimated_total_duration_seconds: float
    steps: list[ReelPlanStepResponse]


class ReelDraftAssetResponse(BaseModel):
    media_id: str
    original_filename: str
    media_kind: str
    content_type: str
    relative_path: str
    thumbnail_relative_path: str | None


class ReelDraftStepResponse(BaseModel):
    step_number: int
    role: str
    media_id: str
    original_filename: str
    media_kind: str
    source_role: str
    selection_mode: str
    clip_start_seconds: float | None
    clip_end_seconds: float | None
    relative_path: str
    suggested_duration_seconds: float
    edit_instruction: str
    why: str


class ReelDraftResponse(BaseModel):
    draft_name: str
    title: str
    caption: str
    cover_media_id: str | None
    video_strategy: str
    estimated_total_duration_seconds: float
    output_width: int
    output_height: int
    fps: int
    audio_strategy: str
    steps: list[ReelDraftStepResponse]
    assets: list[ReelDraftAssetResponse]
    render_spec: "ReelRenderSpecResponse | None"


class ReelRenderClipResponse(BaseModel):
    step_number: int
    role: str
    media_id: str
    original_filename: str
    media_kind: str
    render_mode: str
    source_relative_path: str
    output_relative_path: str
    clip_start_seconds: float | None
    clip_end_seconds: float | None
    output_duration_seconds: float


class ReelRenderSpecResponse(BaseModel):
    backend: str
    backend_available: bool
    working_directory: str
    output_relative_path: str
    concat_relative_path: str
    shell_commands: list[str]
    notes: list[str]
    clips: list[ReelRenderClipResponse]


class AlbumSuggestionResponse(BaseModel):
    album_summary: str
    visual_trip_story: str
    likely_categories: list[str]
    caption_ideas: list[str]
    cover_image_media_id: str | None
    media_insights: list[MediaInsightResponse]
    cover_candidates: list[CurationCandidateResponse]
    carousel_candidates: list[CurationCandidateResponse]
    reel_candidates: list[CurationCandidateResponse]
    reel_plan: ReelPlanResponse | None
    reel_draft: ReelDraftResponse | None
    shot_groups: list[ShotGroupResponse]
    analysis_mode: str
    route: dict | None
