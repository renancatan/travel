from __future__ import annotations

import base64
import hashlib
import logging
import re
from copy import deepcopy
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Body, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from services.api.app.core.album_suggestions import AlbumSuggestionService
from services.api.app.core.file_repository import FileRepository
from services.api.app.core.heavy_media_processing import HeavyMediaProcessingError, HeavyMediaProcessingService
from services.api.app.core.map_entries import MapEntrySuggestionService, build_auto_map_entry, merge_map_entry
from services.api.app.core.media_metadata import (
    build_media_metadata_from_file,
    enrich_saved_media_metadata,
)
from services.api.app.core.reel_frame_gallery import ReelFrameGalleryError, ReelFrameGalleryService
from services.api.app.core.reel_renderer import ReelRenderError, ReelRenderer
from services.api.app.models.albums import (
    AlbumResponse,
    MediaItemResponse,
    UploadAnalysisFramesRequest,
    CreateAlbumRequest,
    GenerateReelFrameGalleryRequest,
    ReelFrameGalleryResponse,
    GenerateAlbumDescriptionResponse,
    GenerateMapEntryRequest,
    UpdateMapEntryRequest,
    RenderCacheCleanupResponse,
    RenderReelResponse,
    SaveReelDraftVersionRequest,
    StartMediaProcessingJobRequest,
    UpdateReelDraftRequest,
    UpdateAlbumRequest,
    UploadMediaResponse,
)
from services.api.app.models.suggestions import AlbumSuggestionResponse, GenerateAlbumSuggestionsRequest

router = APIRouter(prefix="/albums", tags=["albums"])
repository = FileRepository()
suggestion_service = AlbumSuggestionService()
map_entry_service = MapEntrySuggestionService()
reel_renderer = ReelRenderer()
reel_frame_gallery_service = ReelFrameGalleryService()
heavy_media_processing_service = HeavyMediaProcessingService()
logger = logging.getLogger(__name__)

STANDARD_SUGGESTION_KEY = "cached_suggestion"
PROXY_SUGGESTION_KEY = "proxy_cached_suggestion"


@router.get("", response_model=list[AlbumResponse])
def list_albums() -> list[dict]:
    return repository.list_albums()


@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(request: CreateAlbumRequest) -> dict:
    existing_album = repository.find_album_by_name(request.name)
    if existing_album is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f'Album "{existing_album["name"]}" already exists.',
                "album_id": existing_album["id"],
            },
        )
    return repository.create_album(name=request.name, description=request.description)


@router.delete("/render-cache", response_model=RenderCacheCleanupResponse)
def clear_render_cache() -> dict:
    return repository.clear_local_render_cache()


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: str) -> Response:
    deleted = repository.delete_album(album_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{album_id}", response_model=AlbumResponse)
def update_album(album_id: str, request: UpdateAlbumRequest) -> dict:
    album = repository.update_album(album_id, description=request.description)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return album


@router.post("/{album_id}/map-entry/auto", response_model=AlbumResponse)
def generate_album_map_entry(album_id: str) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    try:
        map_entry = build_auto_map_entry(album, album.get("map_entry"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updated_album = repository.save_map_entry(album_id, map_entry)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.post("/{album_id}/map-entry/ai", response_model=AlbumResponse)
def generate_album_map_entry_with_ai(album_id: str, request: GenerateMapEntryRequest) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    try:
        map_entry = map_entry_service.generate(
            album,
            user_prompt=request.user_prompt,
            generation_mode=request.generation_mode,
            selected_media_ids=request.selected_media_ids,
            selected_reel_draft_name=request.selected_reel_draft_name,
            selected_reel_variant_id=request.selected_reel_variant_id,
            selected_reel_title=request.selected_reel_title,
            selected_reel_caption=request.selected_reel_caption,
            selected_reel_video_strategy=request.selected_reel_video_strategy,
            existing_entry=album.get("map_entry"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updated_album = repository.save_map_entry(album_id, map_entry)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.patch("/{album_id}/map-entry", response_model=AlbumResponse)
def update_album_map_entry(album_id: str, request: UpdateMapEntryRequest) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    try:
        map_entry = merge_map_entry(
            album,
            existing_entry=album.get("map_entry"),
            updates=request.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updated_album = repository.save_map_entry(album_id, map_entry)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.get("/{album_id}", response_model=AlbumResponse)
def get_album(album_id: str) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return album


@router.get("/{album_id}/media/{media_id}/content")
def get_media_content(album_id: str, media_id: str) -> FileResponse:
    media_item = repository.get_media_item(album_id, media_id)
    if media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")

    return FileResponse(
        path=media_item["stored_path"],
        media_type=media_item["content_type"],
        filename=media_item["original_filename"],
    )


@router.get("/{album_id}/media/{media_id}/thumbnail")
def get_media_thumbnail(album_id: str, media_id: str) -> FileResponse:
    media_item = repository.get_media_item(album_id, media_id)
    if media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")

    thumbnail_relative_path = media_item.get("thumbnail_relative_path")
    if not thumbnail_relative_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available.")

    thumbnail_path = repository.resolve_relative_path(str(thumbnail_relative_path))
    if not thumbnail_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file not found.")

    return FileResponse(
        path=thumbnail_path,
        media_type=media_item.get("thumbnail_content_type") or "image/jpeg",
        filename=f"{media_item['original_filename']}.jpg",
    )


@router.post("/{album_id}/media/{media_id}/processing-job", response_model=MediaItemResponse)
def start_media_processing_job(
    album_id: str,
    media_id: str,
    background_tasks: BackgroundTasks,
    request: StartMediaProcessingJobRequest | None = Body(default=None),
) -> dict:
    if repository.get_album(album_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    try:
        media_item = heavy_media_processing_service.start_job(
            repository,
            album_id=album_id,
            media_id=media_id,
            force=bool(request.force if request else False),
        )
    except HeavyMediaProcessingError as exc:
        message = str(exc)
        status_code = status.HTTP_409_CONFLICT if "ffmpeg" in message.lower() else status.HTTP_400_BAD_REQUEST
        if "not found" in message.lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=message) from exc

    job_id = str(media_item.get("heavy_processing_job_id") or "").strip()
    job_status = str(media_item.get("heavy_processing_job_status") or "").strip()
    if job_id and job_status == "pending":
        background_tasks.add_task(
            heavy_media_processing_service.run_job,
            repository,
            album_id=album_id,
            media_id=media_id,
            job_id=job_id,
        )
    return media_item


@router.get("/{album_id}/media/{media_id}/processing-proxy")
def get_media_processing_proxy(album_id: str, media_id: str) -> FileResponse:
    media_item = repository.get_media_item(album_id, media_id)
    if media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")

    try:
        proxy_path = heavy_media_processing_service.get_proxy_path(media_item)
    except HeavyMediaProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    response = FileResponse(
        path=proxy_path,
        media_type=str(media_item.get("heavy_processing_proxy_content_type") or "video/mp4"),
        filename=f"{Path(str(media_item.get('stored_filename') or media_id)).stem}-analysis-proxy.mp4",
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@router.get("/{album_id}/media/{media_id}/processing-keyframes/{frame_number}")
def get_media_processing_keyframe(album_id: str, media_id: str, frame_number: int) -> FileResponse:
    media_item = repository.get_media_item(album_id, media_id)
    if media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")

    try:
        keyframe_path = heavy_media_processing_service.get_keyframe_path(media_item, frame_number)
    except HeavyMediaProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=keyframe_path,
        media_type="image/jpeg",
        filename=f"{Path(str(media_item.get('stored_filename') or media_id)).stem}-keyframe-{frame_number:02d}.jpg",
    )


@router.get("/{album_id}/rendered-reel/content")
def get_rendered_reel_content(album_id: str) -> FileResponse:
    album = repository.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    rendered_reel = album.get("rendered_reel")
    if not isinstance(rendered_reel, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered reel not found.")

    relative_path = str(rendered_reel.get("relative_path") or "").strip()
    if not relative_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered reel not found.")

    output_path = repository.resolve_relative_path(relative_path)
    if not output_path.exists():
        logger.warning(
            "Rendered reel file missing on disk album_id=%s relative_path=%s; clearing stale metadata",
            album_id,
            relative_path,
        )
        repository.save_rendered_reel(album_id, None)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered reel file not found.")

    response = FileResponse(
        path=output_path,
        media_type=rendered_reel.get("content_type") or "video/mp4",
        filename=output_path.name,
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/{album_id}/rendered-variants/{variant_id}/content")
def get_rendered_variant_content(album_id: str, variant_id: str) -> FileResponse:
    return _get_rendered_variant_content(
        album_id,
        variant_id,
        suggestion_key=STANDARD_SUGGESTION_KEY,
    )


@router.get("/{album_id}/proxy-rendered-variants/{variant_id}/content")
def get_proxy_rendered_variant_content(album_id: str, variant_id: str) -> FileResponse:
    return _get_rendered_variant_content(
        album_id,
        variant_id,
        suggestion_key=PROXY_SUGGESTION_KEY,
    )


def _get_rendered_variant_content(album_id: str, variant_id: str, *, suggestion_key: str) -> FileResponse:
    album = repository.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = album.get(suggestion_key)
    if not isinstance(cached_suggestion, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered variant not found.")

    rendered_variant_renders = cached_suggestion.get("rendered_variant_renders")
    if not isinstance(rendered_variant_renders, list):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered variant not found.")

    rendered_variant = next(
        (
            item
            for item in rendered_variant_renders
            if isinstance(item, dict) and str(item.get("variant_id") or "").strip() == variant_id
        ),
        None,
    )
    if not isinstance(rendered_variant, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered variant not found.")

    relative_path = str(rendered_variant.get("relative_path") or "").strip()
    if not relative_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered variant not found.")

    output_path = repository.resolve_relative_path(relative_path)
    if not output_path.exists():
        logger.warning(
            "Rendered reel variant missing on disk album_id=%s variant_id=%s relative_path=%s",
            album_id,
            variant_id,
            relative_path,
        )
        updated_renders = [
            item
            for item in rendered_variant_renders
            if not (isinstance(item, dict) and str(item.get("variant_id") or "").strip() == variant_id)
        ]
        repository.save_rendered_variant_renders(album_id, updated_renders, suggestion_key=suggestion_key)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendered variant file not found.")

    response = FileResponse(
        path=output_path,
        media_type=rendered_variant.get("content_type") or "video/mp4",
        filename=output_path.name,
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.post("/{album_id}/reel-frame-gallery", response_model=ReelFrameGalleryResponse)
def generate_reel_frame_gallery(
    album_id: str,
    request: GenerateReelFrameGalleryRequest | None = Body(default=None),
) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album)
    reel_draft = _resolve_reel_frame_gallery_draft(
        album,
        cached_suggestion,
        request=request,
    )

    try:
        return reel_frame_gallery_service.build_gallery(
            album,
            reel_draft,
            source_variant_id=request.source_variant_id if request else None,
            frame_count=request.frame_count if request else 10,
        )
    except ReelFrameGalleryError as exc:
        message = str(exc)
        status_code = status.HTTP_409_CONFLICT if "ffmpeg" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/{album_id}/reel-frame-galleries/{gallery_id}/frames/{frame_id}")
def get_reel_frame_gallery_frame(album_id: str, gallery_id: str, frame_id: str) -> FileResponse:
    try:
        frame, frame_path = reel_frame_gallery_service.get_gallery_frame_path(album_id, gallery_id, frame_id)
    except ReelFrameGalleryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    filename_stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        str(frame.get("original_filename") or frame_id),
    ).strip("._") or frame_id
    return FileResponse(
        path=frame_path,
        media_type=str(frame.get("content_type") or "image/jpeg"),
        filename=f"{filename_stem}-{frame_id}.jpg",
    )


@router.get("/{album_id}/reel-frame-galleries/{gallery_id}/download")
def download_reel_frame_gallery(album_id: str, gallery_id: str) -> FileResponse:
    try:
        download_path = reel_frame_gallery_service.get_gallery_download_path(album_id, gallery_id)
    except ReelFrameGalleryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=download_path,
        media_type="application/zip",
        filename=download_path.name,
    )


@router.post("/{album_id}/media/{media_id}/analysis-frames", response_model=MediaItemResponse)
def upload_media_analysis_frames(album_id: str, media_id: str, request: UploadAnalysisFramesRequest) -> dict:
    media_item = repository.get_media_item(album_id, media_id)
    if media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    if media_item.get("media_kind") != "video":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analysis frames only apply to video items.")

    decoded_frames: list[dict[str, object]] = []
    frame_content_type: str | None = None
    for frame in request.frames:
        content_type, payload = _decode_image_data_url(frame.data_url)
        if frame_content_type is None:
            frame_content_type = content_type
        decoded_frames.append(
            {
                "timestamp_seconds": frame.timestamp_seconds,
                "payload": payload,
            }
        )

    updated_media_item = repository.save_media_analysis_frames(
        album_id,
        media_id,
        frames=decoded_frames,
        content_type=frame_content_type or "image/jpeg",
    )
    if updated_media_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    return updated_media_item


@router.delete("/{album_id}/media/{media_id}", response_model=AlbumResponse)
def delete_media_item(album_id: str, media_id: str) -> dict:
    if repository.get_album(album_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    updated_album = repository.delete_media_item(album_id, media_id)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    return updated_album


@router.post("/{album_id}/suggestions", response_model=AlbumSuggestionResponse)
def generate_album_suggestions(
    album_id: str,
    request: GenerateAlbumSuggestionsRequest | None = Body(default=None),
) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    if not album.get("media_items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Album has no media items yet.")

    suggestion = suggestion_service.generate(
        album,
        reel_variant_request=(
            request.reel_variant_request.model_dump(exclude_none=True)
            if request and request.reel_variant_request
            else None
        ),
    )
    repository.save_cached_suggestion(album_id, suggestion)
    return suggestion


@router.post("/{album_id}/proxy-suggestions", response_model=AlbumSuggestionResponse)
def generate_album_proxy_suggestions(
    album_id: str,
    request: GenerateAlbumSuggestionsRequest | None = Body(default=None),
) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    if not album.get("media_items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Album has no media items yet.")

    if not _album_has_completed_heavy_processing_context(album):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run heavy video processing first so the proxy/keyframe comparison read has server keyframes.",
        )

    suggestion = suggestion_service.generate(
        album,
        reel_variant_request=(
            request.reel_variant_request.model_dump(exclude_none=True)
            if request and request.reel_variant_request
            else None
        ),
        analysis_profile="proxy",
    )
    repository.save_cached_suggestion(album_id, suggestion, suggestion_key=PROXY_SUGGESTION_KEY)
    return suggestion


@router.post("/{album_id}/best-pick", response_model=AlbumResponse)
def generate_album_best_reel_pick(album_id: str) -> dict:
    album = repository.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    try:
        best_pick = suggestion_service.generate_best_reel_pick(album)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updated_album = repository.save_best_reel_pick(album_id, best_pick)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.post("/{album_id}/reel-draft", response_model=AlbumResponse)
def update_album_reel_draft(album_id: str, request: UpdateReelDraftRequest) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album)
    reel_draft = suggestion_service.rebuild_reel_draft(
        album,
        request.reel_draft.model_dump(),
        existing_draft=cached_suggestion.get("reel_draft"),
    )
    cached_suggestion["reel_draft"] = reel_draft
    updated_album = repository.save_cached_suggestion(album_id, cached_suggestion)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.post("/{album_id}/reel-draft/versions", response_model=AlbumResponse)
def save_album_reel_draft_version(album_id: str, request: SaveReelDraftVersionRequest) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album)
    reel_draft = suggestion_service.rebuild_reel_draft(
        album,
        request.reel_draft.model_dump(),
        existing_draft=cached_suggestion.get("reel_draft"),
    )
    cached_suggestion["reel_draft_versions"] = suggestion_service.save_reel_draft_version(
        album,
        reel_draft,
        existing_versions=cached_suggestion.get("reel_draft_versions"),
        label=request.label,
    )
    updated_album = repository.save_cached_suggestion(album_id, cached_suggestion)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.delete("/{album_id}/reel-draft/versions/{version_id}", response_model=AlbumResponse)
def delete_album_reel_draft_version(album_id: str, version_id: str) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album)
    existing_versions = cached_suggestion.get("reel_draft_versions")
    next_versions = suggestion_service.delete_reel_draft_version(
        album,
        existing_versions,
        version_id=version_id,
    )
    existing_count = len(existing_versions) if isinstance(existing_versions, list) else 0
    if len(next_versions) == existing_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft version not found.")

    cached_suggestion["reel_draft_versions"] = next_versions
    updated_album = repository.save_cached_suggestion(album_id, cached_suggestion)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.post("/{album_id}/rendered-reel", response_model=RenderReelResponse)
def render_album_reel(album_id: str, request: UpdateReelDraftRequest | None = Body(default=None)) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    logger.info("Render reel requested album_id=%s album_name=%s", album_id, album.get("name"))

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album)
    reel_draft = cached_suggestion.get("reel_draft")
    render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None

    if request is not None:
        logger.info("Applying edited reel draft before render album_id=%s", album_id)
        reel_draft = suggestion_service.rebuild_reel_draft(
            album,
            request.reel_draft.model_dump(),
            existing_draft=reel_draft if isinstance(reel_draft, dict) else None,
        )
        cached_suggestion["reel_draft"] = reel_draft
        repository.save_cached_suggestion(album_id, cached_suggestion)
        album = repository.get_album(album_id) or album
        render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None

    if not isinstance(reel_draft, dict) or not isinstance(render_spec, dict):
        logger.warning("Render reel blocked album_id=%s reason=no_renderable_draft", album_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This album does not have a renderable reel draft yet.")

    try:
        rendered_reel = reel_renderer.render_draft(reel_draft)
    except ReelRenderError as exc:
        logger.warning("Render reel failed album_id=%s reason=%s", album_id, str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    updated_album = repository.save_rendered_reel(album_id, rendered_reel)
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    logger.info(
        "Render reel finished album_id=%s output=%s",
        album_id,
        rendered_reel.get("relative_path"),
    )

    return {
        "album": updated_album,
        "rendered_reel": rendered_reel,
    }


@router.post("/{album_id}/rendered-variants", response_model=AlbumResponse)
def render_album_reel_variants(album_id: str) -> dict:
    return _render_album_reel_variants(
        album_id,
        suggestion_key=STANDARD_SUGGESTION_KEY,
        missing_variants_detail="No AI reel variants are available to render.",
    )


@router.post("/{album_id}/proxy-rendered-variants", response_model=AlbumResponse)
def render_album_proxy_reel_variants(album_id: str) -> dict:
    return _render_album_reel_variants(
        album_id,
        suggestion_key=PROXY_SUGGESTION_KEY,
        missing_variants_detail="No proxy reel variants are available to render.",
    )


def _render_album_reel_variants(
    album_id: str,
    *,
    suggestion_key: str,
    missing_variants_detail: str,
) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    cached_suggestion = _get_renderable_cached_suggestion(album_id, album, suggestion_key=suggestion_key)
    reel_draft_variants = cached_suggestion.get("reel_draft_variants")
    if not isinstance(reel_draft_variants, list) or not reel_draft_variants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=missing_variants_detail)

    rendered_variants: list[dict] = []
    for variant in reel_draft_variants:
        if not isinstance(variant, dict):
            continue

        reel_draft = variant.get("reel_draft")
        if not isinstance(reel_draft, dict):
            continue

        variant_id = str(variant.get("variant_id") or "").strip() or f"variant-{len(rendered_variants) + 1}"
        unique_draft = deepcopy(reel_draft)
        unique_draft["draft_name"] = _build_variant_render_draft_name(album, variant_id)
        prepared_draft = suggestion_service.rebuild_reel_draft(
            album,
            _build_reel_draft_edit_payload(unique_draft),
            existing_draft=unique_draft,
        )

        try:
            rendered_reel = reel_renderer.render_draft(prepared_draft)
        except ReelRenderError as exc:
            logger.warning("Render reel variant failed album_id=%s variant_id=%s reason=%s", album_id, variant_id, str(exc))
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        rendered_variants.append(
            {
                "variant_id": variant_id,
                "label": str(variant.get("label") or variant_id),
                "creative_angle": str(variant.get("creative_angle") or ""),
                "target_duration_seconds": float(variant.get("target_duration_seconds") or 0.0),
                **rendered_reel,
            }
        )

    updated_album = repository.save_rendered_variant_renders(
        album_id,
        rendered_variants,
        suggestion_key=suggestion_key,
    )
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    return updated_album


@router.post("/{album_id}/description/auto", response_model=GenerateAlbumDescriptionResponse)
def generate_album_description(album_id: str) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    if not album.get("media_items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Album has no media items yet.")

    description_data = suggestion_service.generate_description(album)
    updated_album = repository.update_album(album_id, description=description_data["description"])
    if updated_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")
    updated_album = repository.save_description_meta(
        album_id,
        {
            "likely_categories": description_data["likely_categories"],
            "analysis_mode": description_data["analysis_mode"],
            "route": description_data["route"],
        },
    ) or updated_album

    return {
        "album": updated_album,
        "description": description_data["description"],
        "likely_categories": description_data["likely_categories"],
        "analysis_mode": description_data["analysis_mode"],
        "route": description_data["route"],
    }


@router.post("/{album_id}/upload", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    album_id: str,
    request: Request,
    response: Response,
    x_filename: str | None = Header(default=None, alias="X-Filename"),
    content_type: str | None = Header(default=None, alias="Content-Type"),
) -> dict:
    if not x_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Filename header.")

    if repository.get_album(album_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    storage_target = repository.reserve_media_storage(album_id=album_id, original_filename=x_filename)
    stored_path = storage_target["stored_path"]
    payload_hasher = hashlib.sha256()
    total_bytes = 0

    try:
        with stored_path.open("wb") as handle:
            async for chunk in request.stream():
                if not chunk:
                    continue
                handle.write(chunk)
                payload_hasher.update(chunk)
                total_bytes += len(chunk)
    except Exception:
        if stored_path.exists():
            stored_path.unlink()
        raise

    if total_bytes <= 0:
        if stored_path.exists():
            stored_path.unlink()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body.")

    metadata = build_media_metadata_from_file(
        filename=x_filename,
        content_type=content_type,
        stored_path=stored_path,
        file_size_bytes=total_bytes,
        sha256=payload_hasher.hexdigest(),
    )
    media_item = repository.save_media_record(
        album_id=album_id,
        media_id=str(storage_target["media_id"]),
        original_filename=x_filename,
        stored_filename=str(storage_target["stored_filename"]),
        stored_path=stored_path,
        content_type=content_type,
        metadata=metadata,
    )
    enriched_updates = enrich_saved_media_metadata(media_item)
    if enriched_updates:
        updated_media_item = repository.update_media_item(
            album_id,
            media_item["id"],
            updates=enriched_updates,
        )
        if updated_media_item is not None:
            media_item = updated_media_item
    album = repository.get_album(album_id)
    response.headers["Location"] = f"/albums/{album_id}"
    return {"album": album, "media_item": media_item}


def _decode_image_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data URL.")

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analysis frames must be base64-encoded.")

    content_type = header[5:].split(";", 1)[0].strip().lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported frame image type.")

    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid frame payload.") from exc

    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty frame payload.")

    return content_type, payload


def _get_renderable_cached_suggestion(
    album_id: str,
    album: dict,
    *,
    suggestion_key: str = STANDARD_SUGGESTION_KEY,
) -> dict:
    cached_suggestion = album.get(suggestion_key)
    if not isinstance(cached_suggestion, dict):
        logger.warning("Render reel blocked album_id=%s suggestion_key=%s reason=no_cached_suggestion", album_id, suggestion_key)
        detail = (
            "Run proxy AI review before rendering proxy reels."
            if suggestion_key == PROXY_SUGGESTION_KEY
            else "Run AI review before rendering a reel."
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    reel_draft = cached_suggestion.get("reel_draft")
    render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None
    if not isinstance(render_spec, dict):
        logger.info("Upgrading cached suggestion before render album_id=%s suggestion_key=%s", album_id, suggestion_key)
        cached_suggestion = suggestion_service.upgrade_cached_suggestion(album, cached_suggestion)
        repository.save_cached_suggestion(album_id, cached_suggestion, suggestion_key=suggestion_key)

    reel_draft = cached_suggestion.get("reel_draft")
    render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None
    if not isinstance(reel_draft, dict) or not isinstance(render_spec, dict):
        logger.warning("Render reel blocked album_id=%s reason=no_renderable_draft", album_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This album does not have a renderable reel draft yet.")

    return cached_suggestion


def _album_has_completed_heavy_processing_context(album: dict) -> bool:
    for media_item in album.get("media_items") or []:
        if not isinstance(media_item, dict):
            continue
        if str(media_item.get("media_kind") or "") != "video":
            continue
        if int(media_item.get("heavy_processing_keyframe_count") or 0) > 0:
            return True
    return False


def _build_reel_draft_edit_payload(reel_draft: dict) -> dict:
    return {
        "title": reel_draft.get("title"),
        "caption": reel_draft.get("caption"),
        "cover_media_id": reel_draft.get("cover_media_id"),
        "audio_strategy": reel_draft.get("audio_strategy"),
        "filter_settings": reel_draft.get("filter_settings"),
        "steps": [
            {
                "role": step.get("role"),
                "media_id": step.get("media_id"),
                "source_role": step.get("source_role"),
                "suggested_duration_seconds": step.get("suggested_duration_seconds"),
                "clip_start_seconds": step.get("clip_start_seconds"),
                "clip_end_seconds": step.get("clip_end_seconds"),
                "frame_mode": step.get("frame_mode"),
                "focus_x_percent": step.get("focus_x_percent"),
                "focus_y_percent": step.get("focus_y_percent"),
                "edit_instruction": step.get("edit_instruction"),
                "why": step.get("why"),
            }
            for step in reel_draft.get("steps") or []
            if isinstance(step, dict)
        ],
    }


def _build_variant_render_draft_name(album: dict, variant_id: str) -> str:
    album_slug = re.sub(r"[^a-z0-9]+", "-", str(album.get("name") or "album").lower()).strip("-") or "album"
    variant_slug = re.sub(r"[^a-z0-9]+", "-", variant_id.lower()).strip("-") or "variant"
    return f"{album_slug}-{variant_slug}-compare"


def _resolve_reel_frame_gallery_draft(
    album: dict,
    cached_suggestion: dict,
    *,
    request: GenerateReelFrameGalleryRequest | None,
) -> dict:
    existing_draft = _resolve_reel_frame_gallery_existing_draft(cached_suggestion, request=request)
    if request is not None and request.reel_draft is not None:
        return suggestion_service.rebuild_reel_draft(
            album,
            request.reel_draft.model_dump(),
            existing_draft=existing_draft,
        )

    if existing_draft is not None:
        return existing_draft

    reel_draft = cached_suggestion.get("reel_draft")
    if not isinstance(reel_draft, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This album does not have a reel draft yet.")
    return reel_draft


def _resolve_reel_frame_gallery_existing_draft(
    cached_suggestion: dict,
    *,
    request: GenerateReelFrameGalleryRequest | None,
) -> dict | None:
    source_variant_id = str(request.source_variant_id or "").strip() if request is not None else ""
    if source_variant_id:
        reel_draft_variants = cached_suggestion.get("reel_draft_variants")
        if not isinstance(reel_draft_variants, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No AI reel variants are available yet.")
        for variant in reel_draft_variants:
            if not isinstance(variant, dict):
                continue
            if str(variant.get("variant_id") or "").strip() != source_variant_id:
                continue
            reel_draft = variant.get("reel_draft")
            if isinstance(reel_draft, dict):
                return reel_draft
            break
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chosen reel variant was not found.")

    reel_draft = cached_suggestion.get("reel_draft")
    return reel_draft if isinstance(reel_draft, dict) else None
