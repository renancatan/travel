from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.api.app.core.settings import get_settings


VF_CHAIN = (
    "scale=1080:1920:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    "fps=30"
)

logger = logging.getLogger(__name__)


class ReelRenderError(RuntimeError):
    pass


class ReelRenderer:
    def __init__(self) -> None:
        settings = get_settings()
        self.storage_root = Path(settings.local_storage_root).expanduser().resolve()
        self.ffmpeg_binary = shutil.which("ffmpeg")

    def render_draft(self, reel_draft: dict[str, Any]) -> dict[str, Any]:
        if not self.ffmpeg_binary:
            raise ReelRenderError("ffmpeg is not installed on this machine yet.")

        render_spec = reel_draft.get("render_spec")
        if not isinstance(render_spec, dict):
            raise ReelRenderError("This reel draft does not include a render spec.")

        clips = render_spec.get("clips") or []
        if not isinstance(clips, list) or not clips:
            raise ReelRenderError("This reel draft does not include any render clips.")

        output_relative_path = str(render_spec.get("output_relative_path") or "").strip()
        concat_relative_path = str(render_spec.get("concat_relative_path") or "").strip()
        if not output_relative_path or not concat_relative_path:
            raise ReelRenderError("This reel draft is missing output paths.")

        logger.info(
            "Starting reel render draft=%s strategy=%s backend=%s",
            reel_draft.get("draft_name"),
            reel_draft.get("video_strategy"),
            self.ffmpeg_binary,
        )

        output_path = self._resolve_output_path(output_relative_path)
        concat_path = self._resolve_output_path(concat_relative_path)
        render_dir = output_path.parent
        if render_dir.exists():
            shutil.rmtree(render_dir)
        render_dir.mkdir(parents=True, exist_ok=True)

        rendered_clip_paths: list[Path] = []
        for clip in clips:
            rendered_clip_paths.append(self._render_clip(clip))

        concat_path.write_text(
            "".join(f"file '{clip_path.as_posix()}'\n" for clip_path in rendered_clip_paths),
            encoding="utf-8",
        )

        self._run_ffmpeg(
            [
                self.ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )

        if not output_path.exists():
            raise ReelRenderError("Render finished without producing an output file.")

        logger.info(
            "Finished reel render draft=%s output=%s size_bytes=%s",
            reel_draft.get("draft_name"),
            output_relative_path,
            output_path.stat().st_size,
        )

        return {
            "draft_name": str(reel_draft.get("draft_name") or output_path.stem),
            "relative_path": output_relative_path,
            "content_type": "video/mp4",
            "file_size_bytes": output_path.stat().st_size,
            "rendered_at": datetime.now(UTC).isoformat(),
            "output_width": int(reel_draft.get("output_width") or 1080),
            "output_height": int(reel_draft.get("output_height") or 1920),
            "fps": int(reel_draft.get("fps") or 30),
            "estimated_total_duration_seconds": float(reel_draft.get("estimated_total_duration_seconds") or 0.0),
            "video_strategy": str(reel_draft.get("video_strategy") or "still_sequence"),
        }

    def _render_clip(self, clip: dict[str, Any]) -> Path:
        source_relative_path = str(clip.get("source_relative_path") or "").strip()
        output_relative_path = str(clip.get("output_relative_path") or "").strip()
        media_kind = str(clip.get("media_kind") or "unknown")
        output_duration_seconds = float(clip.get("output_duration_seconds") or 0.0)
        clip_start_seconds = self._to_float(clip.get("clip_start_seconds"))
        clip_end_seconds = self._to_float(clip.get("clip_end_seconds"))

        if not source_relative_path or not output_relative_path:
            raise ReelRenderError("A render clip is missing its source or output path.")

        source_path = self._resolve_source_path(source_relative_path)
        output_path = self._resolve_output_path(output_relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Rendering reel clip step=%s role=%s media=%s mode=%s output=%s",
            clip.get("step_number"),
            clip.get("role"),
            clip.get("original_filename"),
            media_kind,
            output_relative_path,
        )

        command = [self.ffmpeg_binary, "-y"]
        if media_kind == "video":
            if clip_start_seconds is not None:
                command.extend(["-ss", f"{clip_start_seconds:.2f}"])
            if clip_end_seconds is not None:
                command.extend(["-to", f"{clip_end_seconds:.2f}"])
            command.extend(
                [
                    "-i",
                    str(source_path),
                    "-vf",
                    VF_CHAIN,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ]
            )
        else:
            if output_duration_seconds <= 0:
                raise ReelRenderError("An image render clip is missing its output duration.")
            command.extend(
                [
                    "-loop",
                    "1",
                    "-t",
                    f"{output_duration_seconds:.1f}",
                    "-i",
                    str(source_path),
                    "-vf",
                    VF_CHAIN,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ]
            )

        self._run_ffmpeg(command)
        if not output_path.exists():
            raise ReelRenderError(f"Clip render did not create {output_path.name}.")
        return output_path

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - integration path
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            message = stderr or stdout or f"{command[0]} exited with code {exc.returncode}."
            raise ReelRenderError(message) from exc

    def _resolve_source_path(self, relative_path: str) -> Path:
        path = self._resolve_output_path(relative_path)
        if not path.exists():
            raise ReelRenderError(f"Source asset not found: {relative_path}")
        return path

    def _resolve_output_path(self, relative_path: str) -> Path:
        resolved = (self.storage_root / relative_path).resolve()
        if self.storage_root not in resolved.parents and resolved != self.storage_root:
            raise ReelRenderError(f"Unsafe render path: {relative_path}")
        return resolved

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
