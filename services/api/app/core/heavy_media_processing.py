from __future__ import annotations

import logging
import re
import shutil
import subprocess
from time import perf_counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.api.app.core.settings import get_settings


logger = logging.getLogger(__name__)


class HeavyMediaProcessingError(RuntimeError):
    pass


class HeavyMediaProcessingService:
    def __init__(self) -> None:
        settings = get_settings()
        self.storage_root = Path(settings.local_storage_root).expanduser().resolve()
        self.ffmpeg_binary = shutil.which("ffmpeg")

    def start_job(
        self,
        repository: Any,
        *,
        album_id: str,
        media_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        media_item = repository.get_media_item(album_id, media_id)
        if media_item is None:
            raise HeavyMediaProcessingError("Media item not found.")
        if str(media_item.get("media_kind") or "") != "video":
            raise HeavyMediaProcessingError("Heavy processing only applies to videos.")
        if not self.ffmpeg_binary:
            raise HeavyMediaProcessingError("ffmpeg is not installed on this machine yet.")

        existing_status = str(media_item.get("heavy_processing_job_status") or "").strip()
        if not force and existing_status in {"pending", "running"}:
            return media_item
        if not force and existing_status == "completed" and int(_to_float(media_item.get("heavy_processing_keyframe_count")) or 0) > 0:
            return media_item

        if force:
            self._clear_previous_outputs(repository, media_item)

        job_id = str(uuid4())
        now = _utc_now()
        updated_media_item = repository.update_media_item(
            album_id,
            media_id,
            updates={
                "heavy_processing_job_id": job_id,
                "heavy_processing_job_status": "pending",
                "heavy_processing_job_stage": "queued",
                "heavy_processing_job_progress_percent": 1,
                "heavy_processing_job_error": None,
                "heavy_processing_job_created_at": now,
                "heavy_processing_job_started_at": None,
                "heavy_processing_job_completed_at": None,
                "heavy_processing_proxy_relative_path": None,
                "heavy_processing_proxy_content_type": None,
                "heavy_processing_proxy_file_size_bytes": None,
                "heavy_processing_strategy": None,
                "heavy_processing_proxy_reason": None,
                "heavy_processing_proxy_duration_seconds": None,
                "heavy_processing_keyframe_duration_seconds": None,
                "heavy_processing_total_duration_seconds": None,
                "heavy_processing_output_file_size_bytes": None,
                "heavy_processing_keyframe_relative_paths": [],
                "heavy_processing_keyframe_timestamps_seconds": [],
                "heavy_processing_keyframe_count": 0,
                "heavy_processing_timeline_windows": [],
                **self._build_source_retention_fields(media_item),
            },
        )
        if updated_media_item is None:
            raise HeavyMediaProcessingError("Media item not found.")
        repository.invalidate_proxy_suggestion(album_id)
        return updated_media_item

    def run_job(self, repository: Any, *, album_id: str, media_id: str, job_id: str) -> None:
        try:
            media_item = repository.get_media_item(album_id, media_id)
            if media_item is None:
                return
            if str(media_item.get("heavy_processing_job_id") or "") != job_id:
                return

            self._update_job(
                repository,
                album_id=album_id,
                media_id=media_id,
                job_id=job_id,
                status="running",
                stage="probing",
                progress=8,
                extra={"heavy_processing_job_started_at": _utc_now()},
            )

            source_path = Path(str(media_item.get("stored_path") or ""))
            if not source_path.exists():
                raise HeavyMediaProcessingError("Source video file is missing from disk.")

            duration_seconds = _to_float(media_item.get("duration_seconds")) or 0.0
            processing_dir = self._processing_dir(album_id, media_id, job_id)
            processing_dir.mkdir(parents=True, exist_ok=True)
            job_started_at = perf_counter()
            proxy_decision = self._choose_proxy_strategy(media_item, duration_seconds=duration_seconds)
            proxy_path: Path | None = None
            proxy_duration_seconds: float | None = None
            keyframe_source_path = source_path

            if proxy_decision["generate_proxy"]:
                self._update_job(
                    repository,
                    album_id=album_id,
                    media_id=media_id,
                    job_id=job_id,
                    status="running",
                    stage="proxy",
                    progress=18,
                    extra={
                        "heavy_processing_strategy": "proxy_keyframes",
                        "heavy_processing_proxy_reason": proxy_decision["reason"],
                    },
                )
                proxy_started_at = perf_counter()
                proxy_path = self._build_proxy(source_path, processing_dir, duration_seconds=duration_seconds)
                proxy_duration_seconds = round(perf_counter() - proxy_started_at, 3)
                keyframe_source_path = proxy_path

            self._update_job(
                repository,
                album_id=album_id,
                media_id=media_id,
                job_id=job_id,
                status="running",
                stage="keyframes",
                progress=62 if proxy_decision["generate_proxy"] else 24,
                extra={
                    "heavy_processing_strategy": "proxy_keyframes" if proxy_decision["generate_proxy"] else "direct_keyframes",
                    "heavy_processing_proxy_reason": proxy_decision["reason"],
                    "heavy_processing_proxy_duration_seconds": proxy_duration_seconds,
                    **(
                        {
                            "heavy_processing_proxy_relative_path": str(proxy_path.relative_to(self.storage_root)),
                            "heavy_processing_proxy_content_type": "video/mp4",
                            "heavy_processing_proxy_file_size_bytes": proxy_path.stat().st_size,
                        }
                        if proxy_path is not None
                        else {}
                    ),
                },
            )
            keyframe_started_at = perf_counter()
            keyframe_payload = self._extract_keyframes(
                keyframe_source_path,
                processing_dir,
                duration_seconds=duration_seconds,
            )
            keyframe_duration_seconds = round(perf_counter() - keyframe_started_at, 3)

            self._update_job(
                repository,
                album_id=album_id,
                media_id=media_id,
                job_id=job_id,
                status="running",
                stage="timeline",
                progress=88,
            )
            timeline_windows = self._build_timeline_windows(
                keyframe_payload["timestamps"],
                duration_seconds=duration_seconds,
            )
            output_file_size_bytes = sum(
                self._resolve_relative_path(str(relative_path)).stat().st_size
                for relative_path in keyframe_payload["relative_paths"]
                if str(relative_path).strip() and self._resolve_relative_path(str(relative_path)).exists()
            )
            if proxy_path is not None and proxy_path.exists():
                output_file_size_bytes += proxy_path.stat().st_size

            completed_media_item = repository.update_media_item(
                album_id,
                media_id,
                updates={
                    "heavy_processing_job_status": "completed",
                    "heavy_processing_job_stage": "complete",
                    "heavy_processing_job_progress_percent": 100,
                    "heavy_processing_job_error": None,
                    "heavy_processing_job_completed_at": _utc_now(),
                    "heavy_processing_keyframe_relative_paths": keyframe_payload["relative_paths"],
                    "heavy_processing_keyframe_timestamps_seconds": keyframe_payload["timestamps"],
                    "heavy_processing_keyframe_count": len(keyframe_payload["relative_paths"]),
                    "heavy_processing_timeline_windows": timeline_windows,
                    "heavy_processing_strategy": "proxy_keyframes" if proxy_decision["generate_proxy"] else "direct_keyframes",
                    "heavy_processing_proxy_reason": proxy_decision["reason"],
                    "heavy_processing_proxy_duration_seconds": proxy_duration_seconds,
                    "heavy_processing_keyframe_duration_seconds": keyframe_duration_seconds,
                    "heavy_processing_total_duration_seconds": round(perf_counter() - job_started_at, 3),
                    "heavy_processing_output_file_size_bytes": output_file_size_bytes,
                },
            )
            if completed_media_item is not None:
                repository.invalidate_proxy_suggestion(album_id)

            logger.info(
                "Heavy media processing completed album_id=%s media_id=%s job_id=%s",
                album_id,
                media_id,
                job_id,
            )
        except Exception as exc:
            logger.warning(
                "Heavy media processing failed album_id=%s media_id=%s job_id=%s reason=%s",
                album_id,
                media_id,
                job_id,
                str(exc),
            )
            self._update_job(
                repository,
                album_id=album_id,
                media_id=media_id,
                job_id=job_id,
                status="failed",
                stage="failed",
                progress=100,
                extra={
                    "heavy_processing_job_error": str(exc),
                    "heavy_processing_job_completed_at": _utc_now(),
                },
            )

    def get_proxy_path(self, media_item: dict[str, Any]) -> Path:
        relative_path = str(media_item.get("heavy_processing_proxy_relative_path") or "").strip()
        if not relative_path:
            raise HeavyMediaProcessingError("Processing proxy is not ready yet.")
        proxy_path = self._resolve_relative_path(relative_path)
        if not proxy_path.exists():
            raise HeavyMediaProcessingError("Processing proxy file is missing from disk.")
        return proxy_path

    def get_keyframe_path(self, media_item: dict[str, Any], frame_number: int) -> Path:
        relative_paths = media_item.get("heavy_processing_keyframe_relative_paths") or []
        if not isinstance(relative_paths, list) or not relative_paths:
            raise HeavyMediaProcessingError("Processing keyframes are not ready yet.")
        if frame_number < 1 or frame_number > len(relative_paths):
            raise HeavyMediaProcessingError("Processing keyframe not found.")
        keyframe_path = self._resolve_relative_path(str(relative_paths[frame_number - 1]))
        if not keyframe_path.exists():
            raise HeavyMediaProcessingError("Processing keyframe file is missing from disk.")
        return keyframe_path

    def _build_proxy(self, source_path: Path, processing_dir: Path, *, duration_seconds: float) -> Path:
        proxy_path = processing_dir / "analysis-proxy.mp4"
        if proxy_path.exists() and proxy_path.stat().st_size > 0:
            return proxy_path

        command = [
            str(self.ffmpeg_binary),
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-sn",
            "-dn",
            "-vf",
            "scale=1280:1280:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2,setsar=1",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(proxy_path),
        ]
        self._run_ffmpeg(command, timeout_seconds=self._processing_timeout(duration_seconds))
        if not proxy_path.exists() or proxy_path.stat().st_size <= 0:
            raise HeavyMediaProcessingError("ffmpeg did not create the analysis proxy.")
        return proxy_path

    def _choose_proxy_strategy(self, media_item: dict[str, Any], *, duration_seconds: float) -> dict[str, Any]:
        width = int(_to_float(media_item.get("width")) or 0)
        height = int(_to_float(media_item.get("height")) or 0)
        file_size_bytes = int(_to_float(media_item.get("file_size_bytes")) or 0)
        codec = str(media_item.get("video_codec") or "").strip().lower()
        resolution_tier = str(media_item.get("video_resolution_tier") or "")
        long_edge = max(width, height)
        short_edge = min(width, height)
        estimated_bitrate = (file_size_bytes * 8 / duration_seconds) if duration_seconds > 0 else 0.0

        if resolution_tier == "uhd_4k" or (long_edge >= 3840 and short_edge >= 2160):
            return {
                "generate_proxy": True,
                "reason": "4K/heavy source: generate a lower-resolution proxy so repeated analysis and renders avoid the original.",
            }

        if estimated_bitrate >= 40_000_000:
            return {
                "generate_proxy": True,
                "reason": "High-bitrate source: generate a proxy to reduce repeated decode and storage/egress pressure.",
            }

        if codec in {"av1", "vp9", "prores", "dnxhd", "dnxhr", "rawvideo"}:
            return {
                "generate_proxy": True,
                "reason": "Codec is expensive or less portable for downstream render/playback, so a proxy is useful.",
            }

        if duration_seconds >= 60.0 and long_edge <= 1920 and short_edge <= 1080:
            return {
                "generate_proxy": False,
                "reason": "FHD long video: extract keyframes directly first; skip full proxy unless later renders or compatibility need it.",
            }

        if file_size_bytes >= 2 * 1024 * 1024 * 1024 and (width <= 0 or height <= 0):
            return {
                "generate_proxy": True,
                "reason": "Very large source with incomplete metadata: generate a proxy to make downstream analysis predictable.",
            }

        return {
            "generate_proxy": False,
            "reason": "Keyframe-first processing is enough for this source; defer proxy generation until a later step proves it is needed.",
        }

    def _extract_keyframes(
        self,
        source_path: Path,
        processing_dir: Path,
        *,
        duration_seconds: float,
        frame_count: int = 12,
    ) -> dict[str, list[Any]]:
        keyframe_dir = processing_dir / "keyframes"
        if keyframe_dir.exists():
            shutil.rmtree(keyframe_dir)
        keyframe_dir.mkdir(parents=True, exist_ok=True)

        timestamps = self._build_keyframe_timestamps(duration_seconds, frame_count=frame_count)
        relative_paths: list[str] = []
        saved_timestamps: list[float] = []
        for index, timestamp in enumerate(timestamps, start=1):
            frame_path = keyframe_dir / f"keyframe-{index:02d}.jpg"
            command = [
                str(self.ffmpeg_binary),
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(source_path),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(frame_path),
            ]
            self._run_ffmpeg(command, timeout_seconds=90)
            if frame_path.exists() and frame_path.stat().st_size > 0:
                relative_paths.append(str(frame_path.relative_to(self.storage_root)))
                saved_timestamps.append(round(timestamp, 3))

        if not relative_paths:
            raise HeavyMediaProcessingError("No keyframes could be extracted from this video.")
        return {
            "relative_paths": relative_paths,
            "timestamps": saved_timestamps,
        }

    @staticmethod
    def _build_keyframe_timestamps(duration_seconds: float, *, frame_count: int) -> list[float]:
        if duration_seconds <= 0:
            return [0.0]
        return [
            round(max(0.0, min(duration_seconds - 0.1, duration_seconds * ((index + 1) / (frame_count + 1)))), 3)
            for index in range(frame_count)
        ]

    @staticmethod
    def _build_timeline_windows(timestamps: list[float], *, duration_seconds: float) -> list[dict[str, Any]]:
        if not timestamps:
            return []

        base_window_seconds = 10.0
        if duration_seconds >= 600.0:
            base_window_seconds = 24.0
        if duration_seconds >= 1800.0:
            base_window_seconds = 36.0

        windows: list[dict[str, Any]] = []
        for index, timestamp in enumerate(timestamps, start=1):
            start = max(0.0, timestamp - (base_window_seconds / 2))
            end = timestamp + (base_window_seconds / 2)
            if duration_seconds > 0:
                end = min(duration_seconds, end)
                start = max(0.0, min(start, max(0.0, duration_seconds - max(1.0, end - start))))
            if end <= start:
                end = start + 1.0
            windows.append(
                {
                    "window_id": f"window-{index:02d}",
                    "start_seconds": round(start, 3),
                    "end_seconds": round(end, 3),
                    "anchor_timestamp_seconds": round(timestamp, 3),
                    "source": "server_keyframe_spacing",
                    "why": "First-pass long-video candidate window around an extracted keyframe.",
                }
            )
        return windows

    def _update_job(
        self,
        repository: Any,
        *,
        album_id: str,
        media_id: str,
        job_id: str,
        status: str,
        stage: str,
        progress: int,
        extra: dict[str, Any] | None = None,
    ) -> None:
        media_item = repository.get_media_item(album_id, media_id)
        if media_item is None or str(media_item.get("heavy_processing_job_id") or "") != job_id:
            return
        repository.update_media_item(
            album_id,
            media_id,
            updates={
                "heavy_processing_job_status": status,
                "heavy_processing_job_stage": stage,
                "heavy_processing_job_progress_percent": max(0, min(100, int(progress))),
                **(extra or {}),
            },
        )

    def _clear_previous_outputs(self, repository: Any, media_item: dict[str, Any]) -> None:
        relative_paths = []
        proxy_relative_path = str(media_item.get("heavy_processing_proxy_relative_path") or "").strip()
        if proxy_relative_path:
            relative_paths.append(proxy_relative_path)
        for relative_path in media_item.get("heavy_processing_keyframe_relative_paths") or []:
            relative_paths.append(str(relative_path))
        for relative_path in relative_paths:
            target_path = repository.resolve_relative_path(relative_path)
            if target_path.exists():
                target_path.unlink()

        album_id = str(media_item.get("album_id") or "")
        media_id = str(media_item.get("id") or "")
        processing_root = self.storage_root / "albums" / album_id / "processing" / media_id
        if processing_root.exists():
            shutil.rmtree(processing_root, ignore_errors=True)

    def _processing_dir(self, album_id: str, media_id: str, job_id: str) -> Path:
        safe_job_id = re.sub(r"[^a-z0-9-]+", "-", job_id.lower()).strip("-") or "job"
        return self.storage_root / "albums" / album_id / "processing" / media_id / safe_job_id

    def _resolve_relative_path(self, relative_path: str) -> Path:
        resolved = (self.storage_root / relative_path).resolve()
        if self.storage_root not in resolved.parents and resolved != self.storage_root:
            raise HeavyMediaProcessingError(f"Unsafe heavy-processing path: {relative_path}")
        return resolved

    def _run_ffmpeg(self, command: list[str], *, timeout_seconds: int) -> None:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise HeavyMediaProcessingError("ffmpeg processing timed out.") from exc
        except (OSError, subprocess.SubprocessError) as exc:
            raise HeavyMediaProcessingError("Could not run ffmpeg for heavy media processing.") from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            raise HeavyMediaProcessingError(stderr or stdout or "ffmpeg failed during heavy media processing.")

    @staticmethod
    def _processing_timeout(duration_seconds: float) -> int:
        if duration_seconds <= 0:
            return 600
        return int(max(600, min(7200, duration_seconds * 3)))

    @staticmethod
    def _build_source_retention_fields(media_item: dict[str, Any]) -> dict[str, Any]:
        duration_seconds = _to_float(media_item.get("duration_seconds")) or 0.0
        file_size_bytes = int(_to_float(media_item.get("file_size_bytes")) or 0)
        processing_profile = str(media_item.get("processing_profile") or "")
        resolution_tier = str(media_item.get("video_resolution_tier") or "")

        if duration_seconds <= 60.0 and file_size_bytes < 500 * 1024 * 1024:
            return {
                "source_retention_policy": "keep_original",
                "source_retention_recommendation": "Short source video can be retained with the normal album assets.",
                "source_original_temporary_until": None,
                "source_retention_estimated_gb_days": 0.0,
            }

        temporary_until = datetime.now(UTC) + timedelta(days=14)
        estimated_gb_days = round((file_size_bytes / (1024**3)) * 14, 3)
        reason = "Long source video should be temporary by default; preserve generated outputs and archive the original only if paid retention is enabled."
        if processing_profile == "heavy_async" or resolution_tier == "uhd_4k" or file_size_bytes >= 500 * 1024 * 1024:
            reason = "Heavy/4K source video should be temporary by default; keep proxy, reels, frames, and metadata as durable assets."

        return {
            "source_retention_policy": "temporary_original_recommended",
            "source_retention_recommendation": reason,
            "source_original_temporary_until": temporary_until.isoformat(),
            "source_retention_estimated_gb_days": estimated_gb_days,
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
