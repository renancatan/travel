from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from services.api.app.core.album_suggestions import AlbumSuggestionService
from services.api.app.core.file_repository import FileRepository
from services.api.app.core.media_metadata import build_media_metadata, enrich_saved_media_metadata
from services.api.app.models.albums import (
    AlbumResponse,
    CreateAlbumRequest,
    GenerateAlbumDescriptionResponse,
    UpdateAlbumRequest,
    UploadMediaResponse,
)
from services.api.app.models.suggestions import AlbumSuggestionResponse

router = APIRouter(prefix="/albums", tags=["albums"])
repository = FileRepository()
suggestion_service = AlbumSuggestionService()


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

    return suggestion_service.generate(album)


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
