from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class ReelVariantRequestInput(BaseModel):
    mode: Literal["auto", "preset", "custom_range"] = "auto"
    preset_variant_id: str | None = Field(default=None, max_length=80)
    min_duration_seconds: float | None = Field(default=None, gt=0)
    max_duration_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_request(self) -> "ReelVariantRequestInput":
        if self.mode == "preset" and not self.preset_variant_id:
            raise ValueError("preset_variant_id is required when mode is preset.")

        if self.mode == "custom_range":
            if self.min_duration_seconds is None or self.max_duration_seconds is None:
                raise ValueError("min_duration_seconds and max_duration_seconds are required for custom_range.")
            if self.min_duration_seconds > self.max_duration_seconds:
                raise ValueError("min_duration_seconds must be less than or equal to max_duration_seconds.")

        return self


class GenerateAlbumSuggestionsRequest(BaseModel):
    reel_variant_request: ReelVariantRequestInput | None = None


class ReelVariantRequestSummaryResponse(BaseModel):
    mode: Literal["auto", "preset", "custom_range"]
    label: str
    preset_variant_id: str | None = None
    target_duration_seconds: float | None = None
    min_duration_seconds: float | None = None
    max_duration_seconds: float | None = None


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
    frame_mode: str | None = None
    focus_x_percent: float | None = None
    focus_y_percent: float | None = None
    relative_path: str
    suggested_duration_seconds: float
    edit_instruction: str
    why: str


class ReelFilterSettingsResponse(BaseModel):
    brightness: float
    contrast: float
    saturation: float


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
    filter_settings: ReelFilterSettingsResponse
    steps: list[ReelDraftStepResponse]
    assets: list[ReelDraftAssetResponse]
    render_spec: "ReelRenderSpecResponse | None"


class ReelDraftVersionResponse(BaseModel):
    version_id: str
    label: str
    created_at: str
    updated_at: str
    reel_draft: ReelDraftResponse


class ReelDraftVariantResponse(BaseModel):
    variant_id: str
    label: str
    target_duration_seconds: float
    creative_angle: str
    reel_plan: ReelPlanResponse | None
    reel_draft: ReelDraftResponse


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
    frame_mode: str | None = None
    focus_x_percent: float | None = None
    focus_y_percent: float | None = None
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
    reel_draft_variants: list[ReelDraftVariantResponse] = []
    reel_draft_versions: list[ReelDraftVersionResponse] = []
    reel_variant_request_summary: ReelVariantRequestSummaryResponse | None = None
    shot_groups: list[ShotGroupResponse]
    analysis_mode: str
    route: dict | None
