from __future__ import annotations

from pydantic import BaseModel, Field


class CreateAlbumRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class UpdateAlbumRequest(BaseModel):
    description: str | None = Field(default=None, max_length=1000)


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
    media_score: float | None = None
    media_score_label: str | None = None
    detected_at: str
    created_at: str


class AlbumResponse(BaseModel):
    id: str
    name: str
    description: str | None
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
