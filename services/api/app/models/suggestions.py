from __future__ import annotations

from pydantic import BaseModel


class MediaInsightResponse(BaseModel):
    media_id: str | None
    scene_guess: str
    why_it_matters: str
    use_case: str


class AlbumSuggestionResponse(BaseModel):
    album_summary: str
    visual_trip_story: str
    likely_categories: list[str]
    caption_ideas: list[str]
    cover_image_media_id: str | None
    media_insights: list[MediaInsightResponse]
    analysis_mode: str
    route: dict | None

