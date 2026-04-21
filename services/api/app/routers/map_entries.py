from __future__ import annotations

from fastapi import APIRouter

from services.api.app.core.file_repository import FileRepository
from services.api.app.models.albums import MapEntryResponse

router = APIRouter(tags=["map"])
repository = FileRepository()


@router.get("/map-entries", response_model=list[MapEntryResponse])
def list_map_entries() -> list[dict]:
    return repository.list_map_entries()
