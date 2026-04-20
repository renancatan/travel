from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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
        self.ffprobe_binary = shutil.which("ffprobe")

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
        staging_render_dir = render_dir.parent / f".{render_dir.name}-staging-{uuid4().hex[:8]}"
        if staging_render_dir.exists():
            shutil.rmtree(staging_render_dir, ignore_errors=True)
        staging_render_dir.mkdir(parents=True, exist_ok=True)

        render_root_relative = render_dir.relative_to(self.storage_root).as_posix()
        staging_root_relative = staging_render_dir.relative_to(self.storage_root).as_posix()
        staging_output_relative_path = self._swap_render_root(
            output_relative_path,
            render_root_relative,
            staging_root_relative,
        )
        staging_concat_relative_path = self._swap_render_root(
            concat_relative_path,
            render_root_relative,
            staging_root_relative,
        )
        staging_output_path = self._resolve_output_path(staging_output_relative_path)
        staging_concat_path = self._resolve_output_path(staging_concat_relative_path)

        try:
            rendered_clip_paths: list[Path] = []
            for clip in clips:
                staged_clip = {
                    **clip,
                    "audio_strategy": reel_draft.get("audio_strategy"),
                    "output_relative_path": self._swap_render_root(
                        str(clip.get("output_relative_path") or "").strip(),
                        render_root_relative,
                        staging_root_relative,
                    ),
                }
                rendered_clip_paths.append(self._render_clip(staged_clip))

            staging_concat_path.write_text(
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
                    str(staging_concat_path),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-movflags",
                    "+faststart",
                    str(staging_output_path),
                ]
            )

            if not staging_output_path.exists():
                raise ReelRenderError("Render finished without producing an output file.")

            if render_dir.exists():
                shutil.rmtree(render_dir, ignore_errors=True)
            staging_render_dir.replace(render_dir)
        except Exception:
            shutil.rmtree(staging_render_dir, ignore_errors=True)
            raise

        if not output_path.exists():
            raise ReelRenderError("Render finished without producing a final output file.")

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
        audio_strategy = self._normalize_audio_strategy(clip.get("audio_strategy"))
        frame_mode = self._normalize_frame_mode(clip.get("frame_mode"))
        focus_x_percent = self._normalize_focus_percent(clip.get("focus_x_percent"))
        focus_y_percent = self._normalize_focus_percent(clip.get("focus_y_percent"))

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
            has_audio = self._video_has_audio(source_path)
            if clip_start_seconds is not None:
                command.extend(["-ss", f"{clip_start_seconds:.2f}"])
            if clip_end_seconds is not None:
                command.extend(["-to", f"{clip_end_seconds:.2f}"])
            if has_audio and audio_strategy == "preserve_source_audio":
                command.extend(
                    [
                        "-i",
                        str(source_path),
                        "-vf",
                        VF_CHAIN,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-shortest",
                        str(output_path),
                    ]
                )
            else:
                command.extend(
                    [
                        "-i",
                        str(source_path),
                        "-f",
                        "lavfi",
                        "-t",
                        f"{output_duration_seconds:.1f}",
                        "-i",
                        "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-vf",
                        VF_CHAIN,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-shortest",
                        str(output_path),
                    ]
                )
        else:
            if output_duration_seconds <= 0:
                raise ReelRenderError("An image render clip is missing its output duration.")
            image_vf_chain = self._build_image_vf_chain(
                frame_mode=frame_mode,
                focus_x_percent=focus_x_percent,
                focus_y_percent=focus_y_percent,
            )
            command.extend(
                [
                    "-loop",
                    "1",
                    "-t",
                    f"{output_duration_seconds:.1f}",
                    "-i",
                    str(source_path),
                    "-f",
                    "lavfi",
                    "-t",
                    f"{output_duration_seconds:.1f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-vf",
                    image_vf_chain,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-shortest",
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
    def _swap_render_root(relative_path: str, current_root: str, next_root: str) -> str:
        if not relative_path:
            raise ReelRenderError("Missing render path while preparing staging output.")
        if relative_path == current_root:
            return next_root

        expected_prefix = f"{current_root}/"
        if not relative_path.startswith(expected_prefix):
            raise ReelRenderError(f"Render path does not match expected root: {relative_path}")
        return f"{next_root}/{relative_path[len(expected_prefix):]}"

    def _video_has_audio(self, source_path: Path) -> bool:
        if not self.ffprobe_binary:
            return False

        try:
            result = subprocess.run(
                [
                    self.ffprobe_binary,
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(source_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        return result.returncode == 0 and bool(result.stdout.strip())

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_audio_strategy(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"mute_all_audio", "mute", "remove_audio", "silent"}:
            return "mute_all_audio"
        return "preserve_source_audio"

    @staticmethod
    def _normalize_frame_mode(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"cover", "fill"}:
            return "cover"
        return "contain"

    @staticmethod
    def _normalize_focus_percent(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 50.0
        return round(min(100.0, max(0.0, numeric)), 1)

    def _build_image_vf_chain(
        self,
        *,
        frame_mode: str,
        focus_x_percent: float,
        focus_y_percent: float,
    ) -> str:
        if frame_mode != "cover":
            return VF_CHAIN

        x_ratio = focus_x_percent / 100
        y_ratio = focus_y_percent / 100
        return (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(iw-1080)*{x_ratio:.3f}:(ih-1920)*{y_ratio:.3f},"
            "fps=30"
        )
