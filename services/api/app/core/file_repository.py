from __future__ import annotations

import json
import mimetypes
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.api.app.core.map_place_normalizer import normalize_map_place_fields
from services.api.app.core.settings import get_settings
from services.api.app.core.media_metadata import enrich_saved_media_metadata
from services.api.app.core.media_processing_policy import classify_media_processing


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
            "description_meta": None,
            "cached_suggestion": None,
            "map_entry": None,
            "rendered_reel": None,
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
        album["description_meta"] = None
        album["cached_suggestion"] = None
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def save_description_meta(self, album_id: str, description_meta: dict[str, Any] | None) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        album["description_meta"] = description_meta
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def save_cached_suggestion(
        self,
        album_id: str,
        cached_suggestion: dict[str, Any] | None,
        *,
        invalidate_rendered_reel: bool = False,
    ) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        current_cached_suggestion = album.get("cached_suggestion")
        current_rendered_variants = []
        if isinstance(current_cached_suggestion, dict):
            current_rendered_variants = current_cached_suggestion.get("rendered_variant_renders") or []
        next_rendered_variants = cached_suggestion.get("rendered_variant_renders") if isinstance(cached_suggestion, dict) else []
        if current_rendered_variants and not next_rendered_variants:
            self._clear_rendered_variant_files(album)
        if invalidate_rendered_reel:
            self._clear_rendered_reel_files(album)
        album["cached_suggestion"] = cached_suggestion
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def save_map_entry(self, album_id: str, map_entry: dict[str, Any] | None) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        album["map_entry"] = self._normalize_map_entry(map_entry)
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def save_rendered_variant_renders(
        self,
        album_id: str,
        rendered_variant_renders: list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        cached_suggestion = album.get("cached_suggestion")
        if not isinstance(cached_suggestion, dict):
            return None

        self._clear_rendered_variant_files(album)
        if rendered_variant_renders:
            cached_suggestion["rendered_variant_renders"] = rendered_variant_renders
        else:
            cached_suggestion.pop("rendered_variant_renders", None)
        album["cached_suggestion"] = cached_suggestion
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def save_rendered_reel(self, album_id: str, rendered_reel: dict[str, Any] | None) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        current_rendered_reel = album.get("rendered_reel")
        current_relative_path = ""
        if isinstance(current_rendered_reel, dict):
            current_relative_path = str(current_rendered_reel.get("relative_path") or "").strip()

        next_relative_path = ""
        if isinstance(rendered_reel, dict):
            next_relative_path = str(rendered_reel.get("relative_path") or "").strip()

        should_clear_existing_files = rendered_reel is None or (
            bool(current_relative_path) and current_relative_path != next_relative_path
        )
        if should_clear_existing_files:
            self._clear_rendered_reel_files(album)
        album["rendered_reel"] = rendered_reel
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

    def save_media_analysis_frames(
        self,
        album_id: str,
        media_id: str,
        *,
        frames: list[dict[str, Any]],
        content_type: str,
    ) -> dict[str, Any] | None:
        album = self.get_album(album_id)
        if album is None:
            return None

        media_items = album.get("media_items", [])
        media_index = next((index for index, item in enumerate(media_items) if item.get("id") == media_id), None)
        if media_index is None:
            return None

        media_item = media_items[media_index]
        self._remove_relative_paths(media_item.get("analysis_frame_relative_paths") or [])

        analysis_dir = self._album_dir(album_id) / "analysis" / media_id
        analysis_dir.mkdir(parents=True, exist_ok=True)
        extension = self._extension_for_content_type(content_type)

        relative_paths: list[str] = []
        timestamps: list[float] = []
        for index, frame in enumerate(frames, start=1):
            frame_filename = f"{media_id}-analysis-{index:02d}{extension}"
            frame_path = analysis_dir / frame_filename
            frame_path.write_bytes(frame["payload"])
            relative_paths.append(str(frame_path.relative_to(self.storage_root)))
            timestamps.append(round(float(frame["timestamp_seconds"]), 3))

        updates = {
            "analysis_frame_relative_paths": relative_paths,
            "analysis_frame_timestamps_seconds": timestamps,
            "analysis_frame_count": len(relative_paths),
        }
        if relative_paths and not media_item.get("thumbnail_relative_path"):
            updates["thumbnail_relative_path"] = relative_paths[0]
            updates["thumbnail_content_type"] = content_type

        updated_media_item = self._normalize_media_item({**media_item, **updates})
        album["media_items"][media_index] = updated_media_item
        self._invalidate_cached_ai(album, clear_description_meta=True)
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return updated_media_item

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
        storage_target = self.reserve_media_storage(album_id=album_id, original_filename=original_filename)
        stored_path = storage_target["stored_path"]
        stored_path.write_bytes(payload)

        return self.save_media_record(
            album_id=album_id,
            media_id=str(storage_target["media_id"]),
            original_filename=original_filename,
            stored_filename=str(storage_target["stored_filename"]),
            stored_path=stored_path,
            content_type=content_type,
            metadata=metadata,
        )

    def reserve_media_storage(self, *, album_id: str, original_filename: str) -> dict[str, Any]:
        album = self.get_album(album_id)
        if album is None:
            raise FileNotFoundError(f"Album {album_id} was not found.")

        media_id = str(uuid4())
        safe_name = self._sanitize_filename(original_filename)
        stored_filename = f"{media_id}-{safe_name}"

        media_dir = self._album_dir(album_id) / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        stored_path = media_dir / stored_filename

        return {
            "media_id": media_id,
            "stored_filename": stored_filename,
            "stored_path": stored_path,
            "relative_path": str(stored_path.relative_to(self.storage_root)),
        }

    def save_media_record(
        self,
        *,
        album_id: str,
        media_id: str,
        original_filename: str,
        stored_filename: str,
        stored_path: Path,
        content_type: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        album = self.get_album(album_id)
        if album is None:
            raise FileNotFoundError(f"Album {album_id} was not found.")

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
        self._invalidate_cached_ai(album, clear_description_meta=True)
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

        self._remove_relative_paths(media_item.get("analysis_frame_relative_paths") or [])

        album["media_items"] = [item for item in media_items if item.get("id") != media_id]
        self._invalidate_cached_ai(album, clear_description_meta=True)
        album["updated_at"] = _utc_now()
        self._write_album_file(album)
        return album

    def delete_album(self, album_id: str) -> bool:
        album = self.get_album(album_id)
        album_dir = self._album_dir(album_id)
        if not album_dir.exists():
            return False

        if album is not None:
            self._clear_rendered_reel_files(album)
        shutil.rmtree(album_dir)
        return True

    def _album_dir(self, album_id: str) -> Path:
        return self.albums_root / album_id

    def _album_file(self, album_id: str) -> Path:
        return self._album_dir(album_id) / "album.json"

    def list_map_entries(self) -> list[dict[str, Any]]:
        map_entries: list[dict[str, Any]] = []
        for album in self.list_albums():
            map_entry = album.get("map_entry")
            if isinstance(map_entry, dict):
                map_entries.append(map_entry)
        return map_entries

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

    def _remove_relative_paths(self, relative_paths: list[str]) -> None:
        for relative_path in relative_paths:
            target_path = self.resolve_relative_path(str(relative_path))
            if target_path.exists():
                target_path.unlink()

    @staticmethod
    def _extension_for_content_type(content_type: str) -> str:
        extension = mimetypes.guess_extension(content_type, strict=False)
        if extension == ".jpe":
            return ".jpg"
        return extension or ".bin"

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
            "description_meta": album.get("description_meta"),
            "cached_suggestion": album.get("cached_suggestion"),
            "map_entry": self._normalize_map_entry(album.get("map_entry")),
            "rendered_reel": album.get("rendered_reel"),
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
            "has_audio": None,
            "gps": None,
            "metadata_source": None,
            "thumbnail_relative_path": None,
            "thumbnail_content_type": None,
            "analysis_frame_relative_paths": [],
            "analysis_frame_timestamps_seconds": [],
            "analysis_frame_count": 0,
            "media_score": None,
            "media_score_label": None,
            "processing_profile": None,
            "processing_profile_label": None,
            "processing_recommendation": None,
            "analysis_strategy": None,
            "is_heavy_video": False,
            "video_duration_tier": None,
            "video_resolution_tier": None,
            "detected_at": _utc_now(),
        }
        normalized = {**defaults, **media_item}
        normalized.update(classify_media_processing(normalized))
        return normalized

    @staticmethod
    def _normalize_map_entry(map_entry: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(map_entry, dict):
            return None

        latitude = map_entry.get("latitude")
        longitude = map_entry.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return None

        title = str(map_entry.get("title") or "").strip()
        group_key = str(map_entry.get("group_key") or "").strip()
        icon_key = str(map_entry.get("icon_key") or "").strip()
        album_id = str(map_entry.get("album_id") or "").strip()
        album_name = str(map_entry.get("album_name") or "").strip()
        if not title or not group_key or not icon_key or not album_id or not album_name:
            return None

        normalized_place_fields = normalize_map_place_fields(
            title=title,
            country=map_entry.get("country"),
            state=map_entry.get("state"),
            city=map_entry.get("city"),
            region=map_entry.get("region"),
            location_label=map_entry.get("location_label"),
            group_key=group_key,
        )

        selected_media_ids = [
            str(media_id).strip()
            for media_id in map_entry.get("selected_media_ids") or []
            if str(media_id).strip()
        ][:8]

        return {
            "album_id": album_id,
            "album_name": album_name,
            "title": normalized_place_fields["title"],
            "latitude": float(latitude),
            "longitude": float(longitude),
            "country": normalized_place_fields["country"],
            "state": normalized_place_fields["state"],
            "city": normalized_place_fields["city"],
            "region": normalized_place_fields["region"],
            "location_label": normalized_place_fields["location_label"],
            "country_slug": normalized_place_fields["country_slug"],
            "state_slug": normalized_place_fields["state_slug"],
            "city_slug": normalized_place_fields["city_slug"],
            "region_slug": normalized_place_fields["region_slug"],
            "location_slug": normalized_place_fields["location_slug"],
            "title_slug": normalized_place_fields["title_slug"],
            "storage_path": normalized_place_fields["storage_path"],
            "group_key": group_key,
            "icon_key": icon_key,
            "summary": str(map_entry.get("summary") or "").strip() or None,
            "selected_media_ids": selected_media_ids,
            "selected_reel_draft_name": str(map_entry.get("selected_reel_draft_name") or "").strip() or None,
            "selected_reel_variant_id": str(map_entry.get("selected_reel_variant_id") or "").strip() or None,
            "generation_prompt": str(map_entry.get("generation_prompt") or "").strip() or None,
            "gps_point_count": int(map_entry.get("gps_point_count") or 0),
            "source": str(map_entry.get("source") or "album_auto").strip() or "album_auto",
            "created_at": map_entry.get("created_at", _utc_now()),
            "updated_at": map_entry.get("updated_at", map_entry.get("created_at", _utc_now())),
        }

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
                or media_item.get("has_audio") is None
                or media_item.get("media_score") is None
            )

        return media_item.get("media_score") is None

    def _clear_rendered_reel_files(self, album: dict[str, Any]) -> None:
        rendered_reel = album.get("rendered_reel")
        if not isinstance(rendered_reel, dict):
            album["rendered_reel"] = None
            return

        relative_path = str(rendered_reel.get("relative_path") or "").strip()
        if not relative_path:
            album["rendered_reel"] = None
            return

        render_path = self.resolve_relative_path(relative_path)
        render_dir = render_path.parent
        if render_dir.exists() and self.storage_root == render_dir.parent.parent:
            shutil.rmtree(render_dir, ignore_errors=True)

        album["rendered_reel"] = None

    def _clear_rendered_variant_files(self, album: dict[str, Any]) -> None:
        cached_suggestion = album.get("cached_suggestion")
        if not isinstance(cached_suggestion, dict):
            return

        rendered_variant_renders = cached_suggestion.get("rendered_variant_renders")
        if not isinstance(rendered_variant_renders, list):
            cached_suggestion.pop("rendered_variant_renders", None)
            album["cached_suggestion"] = cached_suggestion
            return

        for rendered_variant in rendered_variant_renders:
            if not isinstance(rendered_variant, dict):
                continue
            relative_path = str(rendered_variant.get("relative_path") or "").strip()
            if not relative_path:
                continue
            render_path = self.resolve_relative_path(relative_path)
            render_dir = render_path.parent
            if render_dir.exists() and self.storage_root == render_dir.parent.parent:
                shutil.rmtree(render_dir, ignore_errors=True)

        cached_suggestion.pop("rendered_variant_renders", None)
        album["cached_suggestion"] = cached_suggestion

    def _invalidate_cached_ai(self, album: dict[str, Any], *, clear_description_meta: bool) -> None:
        self._clear_rendered_variant_files(album)
        album["cached_suggestion"] = None
        self._clear_rendered_reel_files(album)
        if clear_description_meta:
            album["description_meta"] = None
