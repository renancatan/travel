from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.api.app.core.settings import get_settings
from services.api.app.core.media_metadata import enrich_saved_media_metadata


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class FileRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self.storage_root = Path(settings.local_storage_root).expanduser().resolve()
        self.albums_root = self.storage_root / "albums"
        self.albums_root.mkdir(parents=True, exist_ok=True)

    def list_albums(self) -> list[dict[str, Any]]:
        albums: list[dict[str, Any]] = []
        for album_dir in sorted(self.albums_root.iterdir()):
            if not album_dir.is_dir():
                continue
            album = self._read_album_file(album_dir)
            if album:
                albums.append(album)
        return albums

    def create_album(self, *, name: str, description: str | None = None) -> dict[str, Any]:
        album_id = str(uuid4())
        album_dir = self._album_dir(album_id)
        media_dir = album_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        album = {
            "id": album_id,
            "name": name,
            "description": description,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "media_items": [],
        }
        self._write_album_file(album)
        return album

    def find_album_by_name(self, name: str) -> dict[str, Any] | None:
        target = self._normalize_album_name(name)
        for album in self.list_albums():
            if self._normalize_album_name(album.get("name", "")) == target:
                return album
        return None

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        album = self._read_album_file(self._album_dir(album_id))
        if not album:
            return None
        return album

    def get_media_item(self, album_id: str, media_id: str) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        for media_item in album.get("media_items", []):
            if media_item.get("id") == media_id:
                return media_item
        return None

    def update_album(
        self,
        album_id: str,
        *,
        description: str | None = None,
    ) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        album["description"] = description.strip() if isinstance(description, str) and description.strip() else None
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def update_media_item(
        self,
        album_id: str,
        media_id: str,
        *,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        for index, media_item in enumerate(album.get("media_items", [])):
            if media_item.get("id") != media_id:
                continue

            updated_media_item = self._normalize_media_item({**media_item, **updates})
            album["media_items"][index] = updated_media_item
            album["updated_at"] = _utc_now()
            self._write_album_file(album)
            return updated_media_item

        return None

    def refresh_album_media_metadata(self, album_id: str) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        changed = False
        refreshed_media_items: list[dict[str, Any]] = []

        for media_item in album.get("media_items", []):
            if not self._needs_media_refresh(media_item):
                refreshed_media_items.append(media_item)
                continue

            updates = enrich_saved_media_metadata(media_item)
            if updates:
                refreshed_media_items.append(self._normalize_media_item({**media_item, **updates}))
                changed = True
            else:
                refreshed_media_items.append(media_item)

        if changed:
            album["media_items"] = refreshed_media_items
            album["updated_at"] = _utc_now()
            self._write_album_file(album)

        return album

    def save_media(
        self,
        *,
        album_id: str,
        original_filename: str,
        content_type: str | None,
        payload: bytes,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        album = self.get_album(album_id)
        if album is None:
            raise FileNotFoundError(f"Album {album_id} was not found.")

        media_id = str(uuid4())
        safe_name = self._sanitize_filename(original_filename)
        stored_filename = f"{media_id}-{safe_name}"

        media_dir = self._album_dir(album_id) / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        stored_path = media_dir / stored_filename
        stored_path.write_bytes(payload)

        media_item = self._normalize_media_item(
            {
                "id": media_id,
                "album_id": album_id,
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "stored_path": str(stored_path),
                "relative_path": str(stored_path.relative_to(self.storage_root)),
                "content_type": content_type or "application/octet-stream",
                "created_at": _utc_now(),
                **metadata,
            }
        )

        album["media_items"].append(media_item)
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return media_item

    def delete_media_item(self, album_id: str, media_id: str) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        media_items = album.get("media_items", [])
        media_item = next((item for item in media_items if item.get("id") == media_id), None)
        if media_item is None:
            return None

        stored_path = Path(media_item.get("stored_path", ""))
        if stored_path.exists():
            stored_path.unlink()

        thumbnail_relative_path = media_item.get("thumbnail_relative_path")
        if thumbnail_relative_path:
            thumbnail_path = self.resolve_relative_path(str(thumbnail_relative_path))
            if thumbnail_path.exists():
                thumbnail_path.unlink()

        album["media_items"] = [item for item in media_items if item.get("id") != media_id]
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def delete_album(self, album_id: str) -> bool:
        album_dir = self._album_dir(album_id)
        if not album_dir.exists():
            return False

        shutil.rmtree(album_dir)
        return True

    def _album_dir(self, album_id: str) -> Path:
        return self.albums_root / album_id

    def _album_file(self, album_id: str) -> Path:
        return self._album_dir(album_id) / "album.json"

    def _read_album_file(self, album_dir: Path) -> dict[str, Any] | None:
        album_file = album_dir / "album.json"
        if not album_file.exists():
            return None
        raw_album = json.loads(album_file.read_text(encoding="utf-8"))
        return self._normalize_album(raw_album)

    def _write_album_file(self, album: dict[str, Any]) -> None:
        album_dir = self._album_dir(album["id"])
        album_dir.mkdir(parents=True, exist_ok=True)
        album_file = self._album_file(album["id"])
        album_file.write_text(json.dumps(album, indent=2, ensure_ascii=True), encoding="utf-8")

    def resolve_relative_path(self, relative_path: str) -> Path:
        return (self.storage_root / relative_path).resolve()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
        return cleaned or "file"

    @staticmethod
    def _normalize_album_name(name: str) -> str:
        return re.sub(r"\s+", " ", name).strip().lower()

    def _normalize_album(self, album: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": album.get("id"),
            "name": album.get("name", "Untitled album"),
            "description": album.get("description"),
            "created_at": album.get("created_at", _utc_now()),
            "updated_at": album.get("updated_at", album.get("created_at", _utc_now())),
            "media_items": [self._normalize_media_item(item) for item in album.get("media_items", [])],
        }

    @staticmethod
    def _normalize_media_item(media_item: dict[str, Any]) -> dict[str, Any]:
        defaults = {
            "content_type": "application/octet-stream",
            "media_kind": "unknown",
            "file_size_bytes": 0,
            "sha256": "",
            "file_extension": "",
            "captured_at": None,
            "source_device": None,
            "width": None,
            "height": None,
            "duration_seconds": None,
            "frame_rate": None,
            "video_codec": None,
            "gps": None,
            "metadata_source": None,
            "thumbnail_relative_path": None,
            "thumbnail_content_type": None,
            "media_score": None,
            "media_score_label": None,
            "detected_at": _utc_now(),
        }
        return {**defaults, **media_item}

    @staticmethod
    def _needs_media_refresh(media_item: dict[str, Any]) -> bool:
        media_kind = str(media_item.get("media_kind") or "unknown")
        file_extension = str(media_item.get("file_extension") or "").lower()
        metadata_source = str(media_item.get("metadata_source") or "")
        has_missing_dimensions = media_item.get("width") is None or media_item.get("height") is None

        if media_kind == "image":
            if file_extension in {".jpg", ".jpeg"} and (
                media_item.get("captured_at") is None
                or media_item.get("source_device") is None
                or media_item.get("gps") is None
                or "image_exif" not in metadata_source
            ):
                return True
            return has_missing_dimensions or media_item.get("media_score") is None

        if media_kind == "video":
            return (
                has_missing_dimensions
                or media_item.get("duration_seconds") is None
                or media_item.get("frame_rate") is None
                or media_item.get("video_codec") is None
                or media_item.get("media_score") is None
            )

        return media_item.get("media_score") is None
