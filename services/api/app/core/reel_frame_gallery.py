from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from services.api.app.core.settings import get_settings


logger = logging.getLogger(__name__)


class ReelFrameGalleryError(RuntimeError):
    pass


class ReelFrameGalleryService:
    def __init__(self) -> None:
        settings = get_settings()
        self.storage_root = Path(settings.local_storage_root).expanduser().resolve()
        self.ffmpeg_binary = shutil.which("ffmpeg")

    def build_gallery(
        self,
        album: dict[str, Any],
        reel_draft: dict[str, Any],
        *,
        source_variant_id: str | None = None,
        frame_count: int = 10,
    ) -> dict[str, Any]:
        if not self.ffmpeg_binary:
            raise ReelFrameGalleryError("ffmpeg is not installed on this machine yet.")

        album_id = str(album.get("id") or "").strip()
        if not album_id:
            raise ReelFrameGalleryError("Album id is required to extract reel frames.")

        frame_specs = self._build_frame_specs(album, reel_draft, frame_count=frame_count)
        if not frame_specs:
            raise ReelFrameGalleryError("No long-video reel beats are available for frame extraction yet.")

        gallery_prefix = self._build_gallery_prefix(
            source_variant_id=source_variant_id,
            draft_name=str(reel_draft.get("draft_name") or ""),
        )
        gallery_hash = hashlib.sha256(
            json.dumps(
                {
                    "source_variant_id": source_variant_id,
                    "draft_name": reel_draft.get("draft_name"),
                    "frame_specs": frame_specs,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]
        gallery_id = f"{gallery_prefix}-{gallery_hash}"
        gallery_dir = self._gallery_dir(album_id, gallery_id)
        manifest_path = gallery_dir / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if self._gallery_manifest_is_complete(manifest):
                return manifest
            shutil.rmtree(gallery_dir, ignore_errors=True)

        self._clear_stale_galleries(album_id, gallery_prefix, keep_gallery_id=gallery_id)
        gallery_dir.mkdir(parents=True, exist_ok=True)

        frames: list[dict[str, Any]] = []
        for frame_number, spec in enumerate(frame_specs, start=1):
            frame_id = f"frame-{frame_number:02d}"
            frame_path = gallery_dir / f"{frame_id}.jpg"
            self._extract_frame(
                source_relative_path=str(spec["relative_path"]),
                timestamp_seconds=float(spec["source_timestamp_seconds"]),
                output_path=frame_path,
            )
            frames.append(
                {
                    "frame_id": frame_id,
                    "frame_number": frame_number,
                    "media_id": str(spec["media_id"]),
                    "original_filename": str(spec["original_filename"]),
                    "role": str(spec["role"]),
                    "source_timestamp_seconds": round(float(spec["source_timestamp_seconds"]), 3),
                    "clip_start_seconds": self._round_optional(spec.get("clip_start_seconds")),
                    "clip_end_seconds": self._round_optional(spec.get("clip_end_seconds")),
                    "content_type": "image/jpeg",
                    "relative_path": str(frame_path.relative_to(self.storage_root)),
                }
            )

        zip_filename = f"{gallery_id}.zip"
        zip_path = gallery_dir / zip_filename
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for frame in frames:
                relative_path = str(frame["relative_path"])
                archive.write(
                    self._resolve_relative_path(relative_path),
                    arcname=Path(relative_path).name,
                )

        manifest = {
            "gallery_id": gallery_id,
            "source_variant_id": source_variant_id,
            "source_draft_name": str(reel_draft.get("draft_name") or gallery_prefix),
            "frame_count": len(frames),
            "download_relative_path": str(zip_path.relative_to(self.storage_root)),
            "frames": frames,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
        return manifest

    def get_gallery_manifest(self, album_id: str, gallery_id: str) -> dict[str, Any]:
        manifest_path = self._gallery_dir(album_id, gallery_id) / "manifest.json"
        if not manifest_path.exists():
            raise ReelFrameGalleryError("Frame gallery not found.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not self._gallery_manifest_is_complete(manifest):
            raise ReelFrameGalleryError("Frame gallery is incomplete and should be rebuilt.")
        return manifest

    def get_gallery_frame_path(self, album_id: str, gallery_id: str, frame_id: str) -> tuple[dict[str, Any], Path]:
        manifest = self.get_gallery_manifest(album_id, gallery_id)
        frame = next(
            (
                item
                for item in manifest.get("frames") or []
                if isinstance(item, dict) and str(item.get("frame_id") or "") == frame_id
            ),
            None,
        )
        if not isinstance(frame, dict):
            raise ReelFrameGalleryError("Frame not found in this gallery.")

        frame_path = self._resolve_relative_path(str(frame.get("relative_path") or ""))
        if not frame_path.exists():
            raise ReelFrameGalleryError("Frame file is missing from disk.")
        return frame, frame_path

    def get_gallery_download_path(self, album_id: str, gallery_id: str) -> Path:
        manifest = self.get_gallery_manifest(album_id, gallery_id)
        download_path = self._resolve_relative_path(str(manifest.get("download_relative_path") or ""))
        if not download_path.exists():
            raise ReelFrameGalleryError("Frame gallery archive is missing from disk.")
        return download_path

    def _build_frame_specs(
        self,
        album: dict[str, Any],
        reel_draft: dict[str, Any],
        *,
        frame_count: int,
    ) -> list[dict[str, Any]]:
        media_by_id = {
            str(item.get("id") or ""): item
            for item in album.get("media_items", [])
            if isinstance(item, dict)
        }
        video_steps: list[dict[str, Any]] = []
        for step in reel_draft.get("steps") or []:
            if not isinstance(step, dict) or str(step.get("media_kind") or "") != "video":
                continue

            media_id = str(step.get("media_id") or "")
            media_item = media_by_id.get(media_id)
            if not isinstance(media_item, dict):
                continue

            source_relative_path = str(step.get("relative_path") or media_item.get("relative_path") or "").strip()
            if not source_relative_path:
                continue

            media_duration = self._to_float(media_item.get("duration_seconds")) or 0.0
            if media_duration <= 60.0:
                continue

            clip_start_seconds = max(0.0, self._to_float(step.get("clip_start_seconds")) or 0.0)
            clip_end_seconds = self._to_float(step.get("clip_end_seconds"))
            suggested_duration_seconds = max(0.3, self._to_float(step.get("suggested_duration_seconds")) or 0.0)
            if clip_end_seconds is None or clip_end_seconds <= clip_start_seconds:
                clip_end_seconds = min(media_duration, clip_start_seconds + suggested_duration_seconds)
            clip_end_seconds = min(media_duration, clip_end_seconds)
            if clip_end_seconds <= clip_start_seconds:
                continue

            video_steps.append(
                {
                    "media_id": media_id,
                    "original_filename": str(media_item.get("original_filename") or media_id),
                    "relative_path": source_relative_path,
                    "role": str(step.get("role") or "Beat"),
                    "clip_start_seconds": clip_start_seconds,
                    "clip_end_seconds": clip_end_seconds,
                    "clip_duration_seconds": clip_end_seconds - clip_start_seconds,
                }
            )

        if not video_steps:
            return []

        if len(video_steps) >= frame_count:
            selected_steps = sorted(
                video_steps,
                key=lambda step: float(step["clip_duration_seconds"]),
                reverse=True,
            )[:frame_count]
            return [
                {
                    **step,
                    "source_timestamp_seconds": self._pick_timestamp_for_step(step, sample_index=0, sample_count=1),
                }
                for step in selected_steps
            ]

        allocations = [1 for _ in video_steps]
        remaining = frame_count - len(video_steps)
        while remaining > 0:
            next_index = max(
                range(len(video_steps)),
                key=lambda index: float(video_steps[index]["clip_duration_seconds"]) / (allocations[index] + 0.65),
            )
            allocations[next_index] += 1
            remaining -= 1

        frame_specs: list[dict[str, Any]] = []
        for step, allocation in zip(video_steps, allocations, strict=False):
            for sample_index in range(allocation):
                frame_specs.append(
                    {
                        **step,
                        "source_timestamp_seconds": self._pick_timestamp_for_step(
                            step,
                            sample_index=sample_index,
                            sample_count=allocation,
                        ),
                    }
                )
        return frame_specs[:frame_count]

    @staticmethod
    def _pick_timestamp_for_step(step: dict[str, Any], *, sample_index: int, sample_count: int) -> float:
        clip_start_seconds = float(step["clip_start_seconds"])
        clip_end_seconds = float(step["clip_end_seconds"])
        clip_duration_seconds = max(0.3, clip_end_seconds - clip_start_seconds)
        padding = min(0.6, clip_duration_seconds * 0.12)
        effective_start = clip_start_seconds + padding
        effective_end = clip_end_seconds - padding
        if effective_end <= effective_start:
            effective_start = clip_start_seconds
            effective_end = clip_end_seconds

        if sample_count <= 1:
            return round((effective_start + effective_end) / 2, 3)

        ratio = (sample_index + 1) / (sample_count + 1)
        return round(effective_start + ((effective_end - effective_start) * ratio), 3)

    def _extract_frame(
        self,
        *,
        source_relative_path: str,
        timestamp_seconds: float,
        output_path: Path,
    ) -> None:
        if not source_relative_path.strip():
            raise ReelFrameGalleryError("A reel frame source video path is missing from this gallery request.")
        source_path = self._resolve_relative_path(source_relative_path)
        if not source_path.exists():
            raise ReelFrameGalleryError(f"Source video not found: {source_relative_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [
                    str(self.ffmpeg_binary),
                    "-y",
                    "-ss",
                    f"{timestamp_seconds:.3f}",
                    "-i",
                    str(source_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ReelFrameGalleryError("Could not run ffmpeg while extracting reel frames.") from exc

        if result.returncode != 0 or not output_path.exists():
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            raise ReelFrameGalleryError(stderr or stdout or "ffmpeg did not create the requested reel frame.")

    def _gallery_dir(self, album_id: str, gallery_id: str) -> Path:
        safe_gallery_id = re.sub(r"[^a-z0-9-]+", "-", gallery_id.lower()).strip("-") or "gallery"
        return self.storage_root / "albums" / album_id / "reel-frame-galleries" / safe_gallery_id

    def _clear_stale_galleries(self, album_id: str, gallery_prefix: str, *, keep_gallery_id: str) -> None:
        gallery_root = self.storage_root / "albums" / album_id / "reel-frame-galleries"
        if not gallery_root.exists():
            return
        prefix = f"{gallery_prefix}-"
        for candidate in gallery_root.iterdir():
            if not candidate.is_dir():
                continue
            if candidate.name == keep_gallery_id:
                continue
            if candidate.name.startswith(prefix):
                shutil.rmtree(candidate, ignore_errors=True)

    def _gallery_manifest_is_complete(self, manifest: dict[str, Any]) -> bool:
        frames = manifest.get("frames")
        if not isinstance(frames, list) or not frames:
            return False
        for frame in frames:
            if not isinstance(frame, dict):
                return False
            relative_path = str(frame.get("relative_path") or "")
            if not relative_path or not self._resolve_relative_path(relative_path).exists():
                return False
        download_relative_path = str(manifest.get("download_relative_path") or "")
        if not download_relative_path:
            return False
        return self._resolve_relative_path(download_relative_path).exists()

    def _resolve_relative_path(self, relative_path: str) -> Path:
        resolved = (self.storage_root / relative_path).resolve()
        if self.storage_root not in resolved.parents and resolved != self.storage_root:
            raise ReelFrameGalleryError(f"Unsafe frame-gallery path: {relative_path}")
        return resolved

    @staticmethod
    def _build_gallery_prefix(*, source_variant_id: str | None, draft_name: str) -> str:
        base_value = source_variant_id or draft_name or "reel-frames"
        normalized = re.sub(r"[^a-z0-9]+", "-", base_value.lower()).strip("-")
        return normalized or "reel-frames"

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _round_optional(value: Any) -> float | None:
        numeric = ReelFrameGalleryService._to_float(value)
        if numeric is None:
            return None
        return round(numeric, 3)
