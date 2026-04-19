from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Body, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from services.api.app.core.album_suggestions import AlbumSuggestionService
from services.api.app.core.file_repository import FileRepository
from services.api.app.core.media_metadata import build_media_metadata, enrich_saved_media_metadata
from services.api.app.core.reel_renderer import ReelRenderError, ReelRenderer
from services.api.app.models.albums import (
    AlbumResponse,
    MediaItemResponse,
    UploadAnalysisFramesRequest,
    CreateAlbumRequest,
    GenerateAlbumDescriptionResponse,
    RenderReelResponse,
    UpdateReelDraftRequest,
    UpdateAlbumRequest,
    UploadMediaResponse,
)
from services.api.app.models.suggestions import AlbumSuggestionResponse

router = APIRouter(prefix="/albums", tags=["albums"])
repository = FileRepository()
suggestion_service = AlbumSuggestionService()
reel_renderer = ReelRenderer()
logger = logging.getLogger(__name__)


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
def generate_album_suggestions(album_id: str) -> dict:
    album = repository.refresh_album_media_metadata(album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    if not album.get("media_items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Album has no media items yet.")

    suggestion = suggestion_service.generate(album)
    repository.save_cached_suggestion(album_id, suggestion)
    return suggestion


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

    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body.")

    if repository.get_album(album_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not found.")

    metadata = build_media_metadata(filename=x_filename, content_type=content_type, payload=payload)
    media_item = repository.save_media(
        album_id=album_id,
        original_filename=x_filename,
        content_type=content_type,
        payload=payload,
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


def _get_renderable_cached_suggestion(album_id: str, album: dict) -> dict:
    cached_suggestion = album.get("cached_suggestion")
    if not isinstance(cached_suggestion, dict):
        logger.warning("Render reel blocked album_id=%s reason=no_cached_suggestion", album_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run AI review before rendering a reel.")

    reel_draft = cached_suggestion.get("reel_draft")
    render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None
    if not isinstance(render_spec, dict):
        logger.info("Upgrading cached suggestion before render album_id=%s", album_id)
        cached_suggestion = suggestion_service.upgrade_cached_suggestion(album, cached_suggestion)
        repository.save_cached_suggestion(album_id, cached_suggestion)

    reel_draft = cached_suggestion.get("reel_draft")
    render_spec = reel_draft.get("render_spec") if isinstance(reel_draft, dict) else None
    if not isinstance(reel_draft, dict) or not isinstance(render_spec, dict):
        logger.warning("Render reel blocked album_id=%s reason=no_renderable_draft", album_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This album does not have a renderable reel draft yet.")

    return cached_suggestion
