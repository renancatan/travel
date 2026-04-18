from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency path
    genai = None
    types = None

from services.api.app.core.llm_router import MultiProviderRouter
from services.api.app.core.settings import get_settings

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
SUPPORTED_FRAME_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


class AlbumSuggestionService:
    def __init__(self) -> None:
        settings = get_settings()
        self.router = MultiProviderRouter()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.gemini_model = os.getenv("GEMINI_REASONING_MODEL") or os.getenv("GEMINI_FAST_MODEL") or "gemini-2.5-flash"
        self.gemini_client = genai.Client(api_key=self.gemini_api_key) if self.gemini_api_key and genai else None
        self.local_storage_root = settings.local_storage_root
        self.storage_root = Path(settings.local_storage_root).expanduser().resolve()

    def generate(self, album: dict[str, Any]) -> dict[str, Any]:
        multimodal_parts = self._build_multimodal_parts(album) if self.gemini_client and types else []
        if self.gemini_client and multimodal_parts:
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=types.Content(role="user", parts=multimodal_parts),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                data = self._normalize_suggestion_payload(self._parse_json(response.text or "{}"), album)
                curation_payload = self._build_curation_payload(
                    album,
                    media_insights=data["media_insights"],
                    caption_ideas=data["caption_ideas"],
                )
                return {
                    **data,
                    **curation_payload,
                    "analysis_mode": "multimodal",
                    "route": {
                        "provider_mode": "gemini",
                        "model_used": self.gemini_model,
                        "fallback_used": False,
                    },
                }
            except Exception:
                pass

        prompt = self._build_text_prompt(album)
        data = self.router.ask_json(prompt, model_alias="ggl2")
        normalized_data = self._normalize_suggestion_payload(data, album)
        curation_payload = self._build_curation_payload(
            album,
            media_insights=normalized_data["media_insights"],
            caption_ideas=normalized_data["caption_ideas"],
        )
        return {
            **normalized_data,
            **curation_payload,
            "analysis_mode": "metadata_fallback",
            "route": self.router.get_last_resolution(),
        }

    def generate_description(self, album: dict[str, Any]) -> dict[str, Any]:
        multimodal_parts = self._build_multimodal_description_parts(album) if self.gemini_client and types else []
        if self.gemini_client and multimodal_parts:
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=types.Content(role="user", parts=multimodal_parts),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                data = self._normalize_description_payload(self._parse_json(response.text or "{}"))
                return {
                    **data,
                    "analysis_mode": "multimodal",
                    "route": {
                        "provider_mode": "gemini",
                        "model_used": self.gemini_model,
                        "fallback_used": False,
                    },
                }
            except Exception:
                pass

        prompt = self._build_description_text_prompt(album)
        data = self.router.ask_json(prompt, model_alias="ggl2")
        return {
            **self._normalize_description_payload(data),
            "analysis_mode": "metadata_fallback",
            "route": self.router.get_last_resolution(),
        }

    def upgrade_cached_suggestion(self, album: dict[str, Any], cached_suggestion: dict[str, Any]) -> dict[str, Any]:
        normalized_data = self._normalize_suggestion_payload(cached_suggestion, album)
        curation_payload = self._build_curation_payload(
            album,
            media_insights=normalized_data["media_insights"],
            caption_ideas=normalized_data["caption_ideas"],
        )
        return {
            **normalized_data,
            **curation_payload,
            "analysis_mode": str(cached_suggestion.get("analysis_mode") or "cached"),
            "route": cached_suggestion.get("route"),
        }

    def _build_multimodal_parts(self, album: dict[str, Any]) -> list[types.Part]:
        parts: list[types.Part] = [types.Part.from_text(text=self._build_multimodal_prompt(album))]
        visual_count = 0
        for media_item in album.get("media_items", []):
            if visual_count >= 6:
                break

            content_type = media_item.get("content_type") or ""
            if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
                visual_count += self._append_video_frame_parts(parts, media_item, remaining=6 - visual_count)
                continue

            stored_path = Path(media_item.get("stored_path", ""))
            if not stored_path.exists():
                continue

            payload = stored_path.read_bytes()
            if len(payload) > 8_000_000:
                continue

            parts.append(
                types.Part.from_text(
                    text=(
                        f"Media item {media_item['id']} | filename={media_item['original_filename']} | "
                        f"content_type={content_type} | width={media_item.get('width')} | "
                        f"height={media_item.get('height')} | duration_seconds={media_item.get('duration_seconds')} | "
                        f"frame_rate={media_item.get('frame_rate')} | video_codec={media_item.get('video_codec')} | "
                        f"media_score={media_item.get('media_score')} | captured_at={media_item.get('captured_at')} | "
                        f"source_device={media_item.get('source_device')} | gps={media_item.get('gps')}"
                    )
                )
            )
            parts.append(types.Part.from_bytes(data=payload, mime_type=content_type))
            visual_count += 1

        return parts if visual_count > 0 else []

    def _build_multimodal_description_parts(self, album: dict[str, Any]) -> list[types.Part]:
        parts: list[types.Part] = [types.Part.from_text(text=self._build_description_multimodal_prompt(album))]
        visual_count = 0
        for media_item in album.get("media_items", []):
            if visual_count >= 6:
                break

            content_type = media_item.get("content_type") or ""
            if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
                visual_count += self._append_video_frame_parts(parts, media_item, remaining=6 - visual_count)
                continue

            stored_path = Path(media_item.get("stored_path", ""))
            if not stored_path.exists():
                continue

            payload = stored_path.read_bytes()
            if len(payload) > 8_000_000:
                continue

            parts.append(
                types.Part.from_text(
                    text=(
                        f"Media item {media_item['id']} | filename={media_item['original_filename']} | "
                        f"content_type={content_type} | width={media_item.get('width')} | "
                        f"height={media_item.get('height')} | duration_seconds={media_item.get('duration_seconds')} | "
                        f"frame_rate={media_item.get('frame_rate')} | video_codec={media_item.get('video_codec')} | "
                        f"media_score={media_item.get('media_score')} | captured_at={media_item.get('captured_at')} | "
                        f"source_device={media_item.get('source_device')} | gps={media_item.get('gps')}"
                    )
                )
            )
            parts.append(types.Part.from_bytes(data=payload, mime_type=content_type))
            visual_count += 1

        return parts if visual_count > 0 else []

    def _build_multimodal_prompt(self, album: dict[str, Any]) -> str:
        return (
            "You are helping a travel-media app understand an uploaded album.\n"
            "Use the album description, filenames, metadata, attached images, and attached video frame samples.\n"
            "Return strict JSON with keys:\n"
            "album_summary, visual_trip_story, likely_categories, caption_ideas, cover_image_media_id, media_insights.\n"
            "Rules:\n"
            "- likely_categories must be an array of short lowercase strings like cave, beach, bar, boat, food, city, nature, people, travel, general.\n"
            "- caption_ideas must contain exactly 3 concise captions.\n"
            "- media_insights must be an array with items containing media_id, scene_guess, why_it_matters, use_case.\n"
            "- use_case should be one of cover, detail, people, supporting, skip.\n"
            "- Do not invent grouping or ranking lists; those are computed separately by the app.\n"
            "- If the album description and the actual images disagree, trust the images and mention the mismatch in album_summary.\n"
            f"Album name: {album.get('name')}\n"
            f"Album description: {album.get('description') or 'No description provided.'}\n"
            f"Media count: {len(album.get('media_items', []))}\n"
        )

    def _build_description_multimodal_prompt(self, album: dict[str, Any]) -> str:
        return (
            "You are helping a travel-media app create a concise album description from uploaded media.\n"
            "Use the attached images, attached video frame samples, filenames, and metadata. Return strict JSON with keys:\n"
            "description, likely_categories.\n"
            "Rules:\n"
            "- description must be 1 or 2 sentences, natural, concrete, and suitable as a saved album description.\n"
            "- likely_categories must be an array of short lowercase strings like cave, beach, bar, food, people, city, nature, travel, general.\n"
            "- If the uploaded media does not look travel-related, say that clearly instead of inventing a trip.\n"
            f"Album name: {album.get('name')}\n"
            f"Existing description: {album.get('description') or 'None yet.'}\n"
            f"Media count: {len(album.get('media_items', []))}\n"
        )

    def _build_text_prompt(self, album: dict[str, Any]) -> str:
        media_lines = []
        for media_item in album.get("media_items", []):
            media_lines.append(
                json.dumps(
                    {
                        "media_id": media_item["id"],
                        "filename": media_item["original_filename"],
                        "content_type": media_item["content_type"],
                        "width": media_item.get("width"),
                        "height": media_item.get("height"),
                        "duration_seconds": media_item.get("duration_seconds"),
                        "frame_rate": media_item.get("frame_rate"),
                        "video_codec": media_item.get("video_codec"),
                        "media_score": media_item.get("media_score"),
                        "metadata_source": media_item.get("metadata_source"),
                        "captured_at": media_item.get("captured_at"),
                        "source_device": media_item.get("source_device"),
                        "gps": media_item.get("gps"),
                        "analysis_frame_count": media_item.get("analysis_frame_count"),
                        "analysis_frame_timestamps_seconds": media_item.get("analysis_frame_timestamps_seconds"),
                        "file_size_bytes": media_item.get("file_size_bytes"),
                    },
                    ensure_ascii=True,
                )
            )

        return (
            "You are helping a travel-media app understand an uploaded album.\n"
            "No actual images are attached in this fallback mode, so rely on album description, filenames, and metadata only.\n"
            "Return strict JSON with keys:\n"
            "album_summary, visual_trip_story, likely_categories, caption_ideas, cover_image_media_id, media_insights.\n"
            "Rules:\n"
            "- likely_categories must be an array of short lowercase strings.\n"
            "- caption_ideas must contain exactly 3 concise captions.\n"
            "- media_insights must be an array with items containing media_id, scene_guess, why_it_matters, use_case.\n"
            "- use_case should be one of cover, detail, people, supporting, skip.\n"
            "- Do not invent grouping or ranking lists; those are computed separately by the app.\n"
            f"Album name: {album.get('name')}\n"
            f"Album description: {album.get('description') or 'No description provided.'}\n"
            "Media items:\n"
            + "\n".join(media_lines)
        )

    def _build_description_text_prompt(self, album: dict[str, Any]) -> str:
        media_lines = []
        for media_item in album.get("media_items", []):
            media_lines.append(
                json.dumps(
                    {
                        "media_id": media_item["id"],
                        "filename": media_item["original_filename"],
                        "content_type": media_item["content_type"],
                        "width": media_item.get("width"),
                        "height": media_item.get("height"),
                        "duration_seconds": media_item.get("duration_seconds"),
                        "frame_rate": media_item.get("frame_rate"),
                        "video_codec": media_item.get("video_codec"),
                        "media_score": media_item.get("media_score"),
                        "metadata_source": media_item.get("metadata_source"),
                        "captured_at": media_item.get("captured_at"),
                        "source_device": media_item.get("source_device"),
                        "gps": media_item.get("gps"),
                        "analysis_frame_count": media_item.get("analysis_frame_count"),
                        "analysis_frame_timestamps_seconds": media_item.get("analysis_frame_timestamps_seconds"),
                        "file_size_bytes": media_item.get("file_size_bytes"),
                    },
                    ensure_ascii=True,
                )
            )

        return (
            "You are helping a travel-media app create a concise album description from uploaded media metadata.\n"
            "No actual images are attached in this fallback mode, so rely on filenames and metadata only.\n"
            "Return strict JSON with keys: description, likely_categories.\n"
            "Rules:\n"
            "- description must be 1 or 2 sentences suitable as a saved album description.\n"
            "- likely_categories must be an array of short lowercase strings.\n"
            "- If the media does not clearly look travel-related, say so plainly.\n"
            f"Album name: {album.get('name')}\n"
            f"Existing description: {album.get('description') or 'None yet.'}\n"
            "Media items:\n"
            + "\n".join(media_lines)
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            candidate = MultiProviderRouter._extract_first_json_object(text)
            if candidate is None:
                raise
            return json.loads(candidate)

    @staticmethod
    def _normalize_suggestion_payload(payload: dict[str, Any], album: dict[str, Any]) -> dict[str, Any]:
        media_ids = {item["id"] for item in album.get("media_items", [])}
        raw_insights = payload.get("media_insights") or []
        media_insights: list[dict[str, Any]] = []

        for insight in raw_insights:
            if not isinstance(insight, dict):
                continue
            media_id = str(insight.get("media_id", "")).strip()
            if media_id and media_id not in media_ids:
                continue
            media_insights.append(
                {
                    "media_id": media_id or None,
                    "scene_guess": str(insight.get("scene_guess", "")).strip() or "unknown",
                    "why_it_matters": str(insight.get("why_it_matters", "")).strip() or "No note provided.",
                    "use_case": str(insight.get("use_case", "")).strip() or "supporting",
                }
            )

        caption_ideas = payload.get("caption_ideas") or []
        likely_categories = payload.get("likely_categories") or []

        return {
            "album_summary": str(payload.get("album_summary", "")).strip() or "No album summary returned.",
            "visual_trip_story": str(payload.get("visual_trip_story", "")).strip() or "No trip story returned.",
            "likely_categories": [str(item).strip() for item in likely_categories if str(item).strip()],
            "caption_ideas": [str(item).strip() for item in caption_ideas if str(item).strip()][:3],
            "cover_image_media_id": (
                str(payload.get("cover_image_media_id")).strip()
                if str(payload.get("cover_image_media_id", "")).strip() in media_ids
                else None
            ),
            "media_insights": media_insights,
        }

    @staticmethod
    def _normalize_description_payload(payload: dict[str, Any]) -> dict[str, Any]:
        description = (
            str(payload.get("description", "")).strip()
            or str(payload.get("album_description", "")).strip()
            or "No album description could be generated yet."
        )
        likely_categories = payload.get("likely_categories") or []
        return {
            "description": description,
            "likely_categories": [str(item).strip() for item in likely_categories if str(item).strip()][:6],
        }

    def _build_curation_payload(
        self,
        album: dict[str, Any],
        *,
        media_insights: list[dict[str, Any]],
        caption_ideas: list[str],
    ) -> dict[str, Any]:
        media_items = album.get("media_items", [])
        group_map = self._build_group_map(media_items)
        shot_groups = self._build_shot_groups(media_items, group_map)
        cover_candidates = self._select_candidates(media_items, group_map, target="cover", limit=3)
        carousel_candidates = self._select_candidates(media_items, group_map, target="carousel", limit=5)
        reel_candidates = self._select_candidates(media_items, group_map, target="reel", limit=4)
        reel_plan = self._build_reel_plan(
            album,
            cover_candidates=cover_candidates,
            carousel_candidates=carousel_candidates,
            reel_candidates=reel_candidates,
            media_insights=media_insights,
        )

        return {
            "cover_candidates": cover_candidates,
            "carousel_candidates": carousel_candidates,
            "reel_candidates": reel_candidates,
            "reel_plan": reel_plan,
            "reel_draft": self._build_reel_draft(
                album,
                reel_plan=reel_plan,
                caption_ideas=caption_ideas,
            ),
            "shot_groups": shot_groups,
        }

    def _append_video_frame_parts(
        self,
        parts: list[types.Part],
        media_item: dict[str, Any],
        *,
        remaining: int,
    ) -> int:
        if remaining <= 0:
            return 0

        relative_paths = media_item.get("analysis_frame_relative_paths") or []
        timestamps = media_item.get("analysis_frame_timestamps_seconds") or []
        mime_type = media_item.get("thumbnail_content_type") or "image/jpeg"
        if mime_type not in SUPPORTED_FRAME_MIME_TYPES:
            mime_type = "image/jpeg"

        added = 0
        for index, relative_path in enumerate(relative_paths):
            if added >= remaining:
                break

            frame_path = self.storage_root / str(relative_path)
            if not frame_path.exists():
                continue

            payload = frame_path.read_bytes()
            if len(payload) > 8_000_000:
                continue

            timestamp = timestamps[index] if index < len(timestamps) else None
            timestamp_text = f"{timestamp}s" if timestamp is not None else "unknown time"
            parts.append(
                types.Part.from_text(
                    text=(
                        f"Video frame sample for media item {media_item['id']} | "
                        f"filename={media_item['original_filename']} | sample_time={timestamp_text} | "
                        f"duration_seconds={media_item.get('duration_seconds')} | frame_rate={media_item.get('frame_rate')} | "
                        f"video_codec={media_item.get('video_codec')} | media_score={media_item.get('media_score')}"
                    )
                )
            )
            parts.append(types.Part.from_bytes(data=payload, mime_type=mime_type))
            added += 1

        return added

    def _build_group_map(self, media_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped_items: dict[str, list[dict[str, Any]]] = {}
        for media_item in media_items:
            group_key = self._build_group_key(media_item)
            grouped_items.setdefault(group_key, []).append(media_item)

        group_map: dict[str, dict[str, Any]] = {}
        for index, (group_key, items) in enumerate(grouped_items.items(), start=1):
            ranked_items = sorted(items, key=self._base_rank_score, reverse=True)
            group_id = f"group-{index}"
            label = self._build_group_label(group_key, ranked_items)
            for item in items:
                group_map[item["id"]] = {
                    "group_id": group_id,
                    "group_key": group_key,
                    "label": label,
                    "item_count": len(items),
                    "picked_media_id": ranked_items[0]["id"],
                    "representative_media_id": ranked_items[0]["id"],
                    "media_ids": [ranked_item["id"] for ranked_item in ranked_items],
                }

        return group_map

    def _build_shot_groups(
        self,
        media_items: list[dict[str, Any]],
        group_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unique_groups: dict[str, dict[str, Any]] = {}
        for media_item in media_items:
            group = group_map.get(media_item["id"])
            if not group or group["item_count"] < 2:
                continue
            unique_groups[group["group_id"]] = {
                "group_id": group["group_id"],
                "label": group["label"],
                "representative_media_id": group["representative_media_id"],
                "picked_media_id": group["picked_media_id"],
                "media_ids": group["media_ids"],
                "item_count": group["item_count"],
            }

        return sorted(unique_groups.values(), key=lambda item: (-item["item_count"], item["label"]))

    def _select_candidates(
        self,
        media_items: list[dict[str, Any]],
        group_map: dict[str, dict[str, Any]],
        *,
        target: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        candidate_rows: list[dict[str, Any]] = []
        for media_item in media_items:
            score, reason = self._target_score(media_item, target=target)
            if score <= 0:
                continue
            group = group_map.get(media_item["id"])
            candidate_rows.append(
                {
                    "media_id": media_item["id"],
                    "media_kind": media_item.get("media_kind", "unknown"),
                    "score": round(score, 1),
                    "reason": reason,
                    "group_id": group["group_id"] if group else None,
                }
            )

        candidate_rows.sort(
            key=lambda item: (
                -item["score"],
                item["media_kind"] != "video",
                item["media_id"],
            )
        )

        selected: list[dict[str, Any]] = []
        used_groups: set[str] = set()
        for candidate in candidate_rows:
            group_id = candidate.get("group_id")
            if group_id and group_id in used_groups:
                continue
            selected.append(candidate)
            if group_id:
                used_groups.add(group_id)
            if len(selected) >= limit:
                break

        return selected

    def _target_score(self, media_item: dict[str, Any], *, target: str) -> tuple[float, str]:
        score = self._base_rank_score(media_item)
        reasons: list[str] = []

        media_kind = str(media_item.get("media_kind") or "unknown")
        width = self._to_int(media_item.get("width"))
        height = self._to_int(media_item.get("height"))
        gps = media_item.get("gps")
        has_gps = isinstance(gps, dict) and gps.get("latitude") is not None and gps.get("longitude") is not None
        has_capture = bool(media_item.get("captured_at"))
        analysis_frame_count = self._to_int(media_item.get("analysis_frame_count")) or 0
        aspect_ratio = (width / height) if width and height and height > 0 else None
        duration = self._to_float(media_item.get("duration_seconds"))

        if media_kind == "image":
            reasons.append("strong photo candidate")
        elif media_kind == "video":
            reasons.append("strong motion candidate")
        else:
            reasons.append("metadata candidate")

        if has_gps:
            score += 3
            reasons.append("has GPS")
        if has_capture:
            score += 1.5
            reasons.append("has capture time")

        if target == "cover":
            if media_kind == "image":
                score += 6
                if aspect_ratio and 0.8 <= aspect_ratio <= 1.8:
                    score += 4
                    reasons.append("balanced framing")
                if width and height and max(width, height) >= 2000:
                    score += 3
                    reasons.append("high resolution")
            elif media_kind == "video":
                score += 2
                reasons.append("usable as motion cover")

        elif target == "carousel":
            if media_kind != "image":
                return 0, "not a carousel image"
            score += 8
            reasons.append("image works for carousel")
            if aspect_ratio and 0.75 <= aspect_ratio <= 1.35:
                score += 4
                reasons.append("friendly crop shape")
            if width and height and width * height >= 3_000_000:
                score += 2
                reasons.append("detailed enough for post")

        elif target == "reel":
            if media_kind == "video":
                score += 12
                reasons.append("video is preferred for reels")
                if analysis_frame_count > 0:
                    score += 6
                    reasons.append("AI frame samples ready")
                if duration is not None:
                    if 5 <= duration <= 25:
                        score += 8
                        reasons.append("good short-reel length")
                    elif duration <= 60:
                        score += 4
                        reasons.append("usable clip length")
            elif media_kind == "image":
                score += 3
                reasons.append("can support a reel sequence")
                if aspect_ratio and aspect_ratio < 0.9:
                    score += 3
                    reasons.append("portrait-friendly framing")

        return score, ", ".join(dict.fromkeys(reasons))

    def _build_reel_plan(
        self,
        album: dict[str, Any],
        *,
        cover_candidates: list[dict[str, Any]],
        carousel_candidates: list[dict[str, Any]],
        reel_candidates: list[dict[str, Any]],
        media_insights: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        media_by_id = {item["id"]: item for item in album.get("media_items", [])}
        insight_by_id = {
            str(insight.get("media_id")): insight
            for insight in media_insights
            if isinstance(insight, dict) and insight.get("media_id")
        }
        ordered_candidates = self._merge_plan_candidates(reel_candidates, cover_candidates, carousel_candidates)
        if not ordered_candidates:
            return None
        video_strategy, primary_video_id, secondary_video_id = self._decide_video_strategy(
            reel_candidates,
            media_by_id=media_by_id,
        )

        role_specs = [
            {
                "role": "Hook",
                "preferred_kinds": {"video"},
                "preferred_use_cases": {"cover", "people"},
                "scene_keywords": {"motion", "entrance", "opening", "people", "water", "street"},
            },
            {
                "role": "Establish",
                "preferred_kinds": {"image"},
                "preferred_use_cases": {"cover", "supporting"},
                "scene_keywords": {"entrance", "forest", "beach", "city", "view", "landscape", "outside"},
            },
            {
                "role": "Detail",
                "preferred_kinds": {"image"},
                "preferred_use_cases": {"detail"},
                "scene_keywords": {"detail", "close", "texture", "formation", "food", "face", "hands"},
            },
            {
                "role": "Closer",
                "preferred_kinds": {"image", "video"},
                "preferred_use_cases": {"cover", "supporting", "people"},
                "scene_keywords": {"exit", "outside", "view", "people", "closing", "light"},
            },
        ]

        used_still_media_ids: set[str] = set()
        video_use_counts: dict[str, int] = {}
        steps: list[dict[str, Any]] = []
        for spec in role_specs:
            candidate, source_role = self._pick_candidate_for_reel_role(
                ordered_candidates,
                media_by_id=media_by_id,
                insight_by_id=insight_by_id,
                used_still_media_ids=used_still_media_ids,
                primary_video_id=primary_video_id,
                secondary_video_id=secondary_video_id,
                video_strategy=video_strategy,
                role=spec["role"],
                preferred_kinds=spec["preferred_kinds"],
                preferred_use_cases=spec["preferred_use_cases"],
                scene_keywords=spec["scene_keywords"],
            )
            if candidate is None:
                continue

            media_item = media_by_id.get(candidate["media_id"])
            if media_item is None:
                continue

            insight = insight_by_id.get(candidate["media_id"])
            media_kind = str(media_item.get("media_kind") or "unknown")
            selection_mode = "full_frame"
            clip_start_seconds = None
            clip_end_seconds = None
            if media_kind == "video":
                usage_index = video_use_counts.get(candidate["media_id"], 0)
                clip_start_seconds, clip_end_seconds = self._select_video_clip_window(
                    media_item,
                    role=spec["role"],
                    usage_index=usage_index,
                )
                video_use_counts[candidate["media_id"]] = usage_index + 1
                selection_mode = "video_clip"
            else:
                used_still_media_ids.add(candidate["media_id"])

            steps.append(
                {
                    "step_number": len(steps) + 1,
                    "role": spec["role"],
                    "media_id": candidate["media_id"],
                    "media_kind": media_kind,
                    "source_role": source_role,
                    "selection_mode": selection_mode,
                    "clip_start_seconds": clip_start_seconds,
                    "clip_end_seconds": clip_end_seconds,
                    "suggested_duration_seconds": round(
                        self._suggest_reel_step_duration(media_item, role=spec["role"]),
                        1,
                    ),
                    "edit_instruction": self._build_reel_step_instruction(media_item, role=spec["role"]),
                    "why": self._build_reel_step_reason(candidate, insight),
                }
            )

        if not steps:
            return None

        cover_media_id = cover_candidates[0]["media_id"] if cover_candidates else steps[0]["media_id"]
        estimated_total_duration_seconds = round(
            sum(step["suggested_duration_seconds"] for step in steps),
            1,
        )
        return {
            "cover_media_id": cover_media_id,
            "video_strategy": video_strategy,
            "estimated_total_duration_seconds": estimated_total_duration_seconds,
            "steps": steps,
        }

    def _build_reel_draft(
        self,
        album: dict[str, Any],
        *,
        reel_plan: dict[str, Any] | None,
        caption_ideas: list[str],
    ) -> dict[str, Any] | None:
        if not reel_plan or not reel_plan.get("steps"):
            return None

        media_by_id = {item["id"]: item for item in album.get("media_items", [])}
        asset_ids: list[str] = []
        cover_media_id = reel_plan.get("cover_media_id")
        if isinstance(cover_media_id, str) and cover_media_id:
            asset_ids.append(cover_media_id)
        for step in reel_plan.get("steps", []):
            media_id = str(step.get("media_id") or "").strip()
            if media_id and media_id not in asset_ids:
                asset_ids.append(media_id)

        assets: list[dict[str, Any]] = []
        for media_id in asset_ids:
            media_item = media_by_id.get(media_id)
            if media_item is None:
                continue
            assets.append(
                {
                    "media_id": media_id,
                    "original_filename": media_item.get("original_filename") or media_id,
                    "media_kind": media_item.get("media_kind", "unknown"),
                    "content_type": media_item.get("content_type", "application/octet-stream"),
                    "relative_path": media_item.get("relative_path", ""),
                    "thumbnail_relative_path": media_item.get("thumbnail_relative_path"),
                }
            )

        draft_steps: list[dict[str, Any]] = []
        for step in reel_plan.get("steps", []):
            media_id = str(step.get("media_id") or "").strip()
            media_item = media_by_id.get(media_id)
            if media_item is None:
                continue
            draft_steps.append(
                {
                    "step_number": int(step.get("step_number") or len(draft_steps) + 1),
                    "role": str(step.get("role") or "Beat"),
                    "media_id": media_id,
                    "original_filename": media_item.get("original_filename") or media_id,
                    "media_kind": media_item.get("media_kind", "unknown"),
                    "source_role": str(step.get("source_role") or "still_image"),
                    "selection_mode": str(step.get("selection_mode") or "full_frame"),
                    "clip_start_seconds": self._to_float(step.get("clip_start_seconds")),
                    "clip_end_seconds": self._to_float(step.get("clip_end_seconds")),
                    "relative_path": media_item.get("relative_path", ""),
                    "suggested_duration_seconds": round(float(step.get("suggested_duration_seconds") or 0.0), 1),
                    "edit_instruction": str(step.get("edit_instruction") or "").strip() or "Use this asset in the reel sequence.",
                    "why": str(step.get("why") or "").strip() or "Selected for the reel sequence.",
                }
            )

        if not draft_steps:
            return None

        title = self._build_reel_title(album, caption_ideas=caption_ideas)
        draft_name = f"{self._slugify(str(album.get('name') or title))}-reel-draft"
        caption = caption_ideas[0] if caption_ideas else (album.get("description") or title)
        reel_draft = {
            "draft_name": draft_name,
            "title": title,
            "caption": caption,
            "cover_media_id": cover_media_id if isinstance(cover_media_id, str) else None,
            "video_strategy": str(reel_plan.get("video_strategy") or "still_sequence"),
            "estimated_total_duration_seconds": round(float(reel_plan.get("estimated_total_duration_seconds") or 0.0), 1),
            "output_width": 1080,
            "output_height": 1920,
            "fps": 30,
            "audio_strategy": "silent preview render for now; soundtrack and source-audio mixing come next",
            "steps": draft_steps,
            "assets": assets,
        }
        reel_draft["render_spec"] = self._build_reel_render_spec(reel_draft)
        return reel_draft

    @staticmethod
    def _merge_plan_candidates(*candidate_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_media_ids: set[str] = set()
        for candidate_set in candidate_sets:
            for candidate in candidate_set:
                media_id = str(candidate.get("media_id") or "").strip()
                if not media_id or media_id in seen_media_ids:
                    continue
                merged.append(candidate)
                seen_media_ids.add(media_id)
        return merged

    def _build_reel_render_spec(self, reel_draft: dict[str, Any]) -> dict[str, Any]:
        backend_available = shutil.which("ffmpeg") is not None
        render_dir = f"renders/{reel_draft['draft_name']}"
        concat_relative_path = f"{render_dir}/concat.txt"
        output_relative_path = f"{render_dir}/{reel_draft['draft_name']}.mp4"

        clips: list[dict[str, Any]] = []
        shell_commands: list[str] = [f"mkdir -p {self._shell_quote(render_dir)}"]
        concat_entries: list[str] = []

        for step in reel_draft.get("steps", []):
            step_number = int(step.get("step_number") or len(clips) + 1)
            original_filename = str(step.get("original_filename") or f"step-{step_number}")
            sanitized_stem = self._slugify(Path(original_filename).stem) or f"step-{step_number:02d}"
            output_relative = f"{render_dir}/step-{step_number:02d}-{sanitized_stem}.mp4"
            source_relative = str(step.get("relative_path") or "")
            media_kind = str(step.get("media_kind") or "unknown")
            clip_start_seconds = self._to_float(step.get("clip_start_seconds"))
            clip_end_seconds = self._to_float(step.get("clip_end_seconds"))
            output_duration_seconds = round(float(step.get("suggested_duration_seconds") or 0.0), 1)
            render_mode = "video_trim" if media_kind == "video" else "image_hold"

            clips.append(
                {
                    "step_number": step_number,
                    "role": str(step.get("role") or "Beat"),
                    "media_id": str(step.get("media_id") or ""),
                    "original_filename": original_filename,
                    "media_kind": media_kind,
                    "render_mode": render_mode,
                    "source_relative_path": source_relative,
                    "output_relative_path": output_relative,
                    "clip_start_seconds": clip_start_seconds,
                    "clip_end_seconds": clip_end_seconds,
                    "output_duration_seconds": output_duration_seconds,
                }
            )

            shell_commands.append(
                self._build_ffmpeg_clip_command(
                    source_relative_path=source_relative,
                    output_relative_path=output_relative,
                    media_kind=media_kind,
                    output_duration_seconds=output_duration_seconds,
                    clip_start_seconds=clip_start_seconds,
                    clip_end_seconds=clip_end_seconds,
                )
            )
            concat_entries.append(f"file '{Path(output_relative).name}'")

        concat_args = " ".join(self._shell_quote(entry) for entry in concat_entries)
        shell_commands.append(
            f"printf '%s\\n' {concat_args} > {self._shell_quote(concat_relative_path)}"
        )
        shell_commands.append(
            "ffmpeg -y "
            f"-f concat -safe 0 -i {self._shell_quote(concat_relative_path)} "
            "-an -c:v libx264 -pix_fmt yuv420p -movflags +faststart "
            f"{self._shell_quote(output_relative_path)}"
        )

        notes = [
            "This is a render-ready spec for the future reel worker.",
            "Each step first becomes a normalized 1080x1920 clip, then the clips are concatenated.",
            "The current render path produces a silent preview reel; audio mixing has not been implemented yet.",
        ]
        if not backend_available:
            notes.append("ffmpeg is not installed on this machine right now, so these commands are generated but not executed locally.")

        return {
            "backend": "ffmpeg",
            "backend_available": backend_available,
            "working_directory": self.local_storage_root,
            "output_relative_path": output_relative_path,
            "concat_relative_path": concat_relative_path,
            "shell_commands": shell_commands,
            "notes": notes,
            "clips": clips,
        }

    def _build_ffmpeg_clip_command(
        self,
        *,
        source_relative_path: str,
        output_relative_path: str,
        media_kind: str,
        output_duration_seconds: float,
        clip_start_seconds: float | None,
        clip_end_seconds: float | None,
    ) -> str:
        vf_chain = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            "fps=30"
        )
        if media_kind == "video":
            timing_prefix = ""
            if clip_start_seconds is not None:
                timing_prefix += f"-ss {clip_start_seconds:.2f} "
            if clip_end_seconds is not None:
                timing_prefix += f"-to {clip_end_seconds:.2f} "
            return (
                "ffmpeg -y "
                f"{timing_prefix}-i {self._shell_quote(source_relative_path)} "
                f"-vf {self._shell_quote(vf_chain)} "
                "-an -c:v libx264 -pix_fmt yuv420p "
                f"{self._shell_quote(output_relative_path)}"
            )

        return (
            "ffmpeg -y "
            f"-loop 1 -t {output_duration_seconds:.1f} -i {self._shell_quote(source_relative_path)} "
            f"-vf {self._shell_quote(vf_chain)} "
            "-an -c:v libx264 -pix_fmt yuv420p "
            f"{self._shell_quote(output_relative_path)}"
        )

    @staticmethod
    def _shell_quote(value: str) -> str:
        return "'" + value.replace("'", "'\"'\"'") + "'"

    def _decide_video_strategy(
        self,
        reel_candidates: list[dict[str, Any]],
        *,
        media_by_id: dict[str, dict[str, Any]],
    ) -> tuple[str, str | None, str | None]:
        video_candidates = [
            candidate
            for candidate in reel_candidates
            if str(media_by_id.get(str(candidate.get("media_id") or ""), {}).get("media_kind") or "") == "video"
        ]
        if not video_candidates:
            return "still_sequence", None, None

        primary_video_id = str(video_candidates[0].get("media_id") or "")
        if len(video_candidates) == 1 or not primary_video_id:
            return "hero_video", primary_video_id or None, None

        secondary_video_id = str(video_candidates[1].get("media_id") or "")
        primary_score = float(video_candidates[0].get("score") or 0.0)
        secondary_score = float(video_candidates[1].get("score") or 0.0)
        if secondary_video_id and secondary_score >= 55 and abs(primary_score - secondary_score) <= 10:
            return "multi_clip_sequence", primary_video_id, secondary_video_id
        return "hero_video", primary_video_id, None

    def _pick_candidate_for_reel_role(
        self,
        ordered_candidates: list[dict[str, Any]],
        *,
        media_by_id: dict[str, dict[str, Any]],
        insight_by_id: dict[str, dict[str, Any]],
        used_still_media_ids: set[str],
        primary_video_id: str | None,
        secondary_video_id: str | None,
        video_strategy: str,
        role: str,
        preferred_kinds: set[str],
        preferred_use_cases: set[str],
        scene_keywords: set[str],
    ) -> tuple[dict[str, Any] | None, str]:
        if role == "Hook" and primary_video_id:
            candidate = self._find_candidate_by_media_id(ordered_candidates, primary_video_id)
            if candidate is not None:
                return candidate, "hero_video"

        if role == "Establish":
            if video_strategy == "multi_clip_sequence" and secondary_video_id:
                candidate = self._find_candidate_by_media_id(ordered_candidates, secondary_video_id)
                if candidate is not None:
                    return candidate, "supporting_video"
            if video_strategy == "hero_video" and primary_video_id:
                candidate = self._find_candidate_by_media_id(ordered_candidates, primary_video_id)
                if candidate is not None:
                    return candidate, "hero_video"

        if role in {"Detail", "Closer"}:
            still_candidate = self._pick_still_candidate_for_role(
                ordered_candidates,
                media_by_id=media_by_id,
                insight_by_id=insight_by_id,
                used_still_media_ids=used_still_media_ids,
                preferred_use_cases=preferred_use_cases,
                scene_keywords=scene_keywords,
                role=role,
            )
            if still_candidate is not None:
                return still_candidate, "still_image"

        candidate = self._pick_reel_plan_candidate(
            ordered_candidates,
            media_by_id,
            insight_by_id,
            used_still_media_ids,
            preferred_kinds=preferred_kinds,
            preferred_use_cases=preferred_use_cases,
            scene_keywords=scene_keywords,
            role=role,
        )
        if candidate is None:
            return None, "still_image"

        media_id = str(candidate.get("media_id") or "")
        if media_id and media_id == primary_video_id:
            return candidate, "hero_video"
        if media_id and media_id == secondary_video_id:
            return candidate, "supporting_video"
        if str(media_by_id.get(media_id, {}).get("media_kind") or "") == "video":
            return candidate, "supporting_video"
        return candidate, "still_image"

    @staticmethod
    def _find_candidate_by_media_id(
        ordered_candidates: list[dict[str, Any]],
        media_id: str,
    ) -> dict[str, Any] | None:
        for candidate in ordered_candidates:
            if str(candidate.get("media_id") or "") == media_id:
                return candidate
        return None

    def _pick_still_candidate_for_role(
        self,
        ordered_candidates: list[dict[str, Any]],
        *,
        media_by_id: dict[str, dict[str, Any]],
        insight_by_id: dict[str, dict[str, Any]],
        used_still_media_ids: set[str],
        preferred_use_cases: set[str],
        scene_keywords: set[str],
        role: str,
    ) -> dict[str, Any] | None:
        best_candidate: dict[str, Any] | None = None
        best_rank: tuple[float, int] | None = None

        for index, candidate in enumerate(ordered_candidates):
            media_id = str(candidate.get("media_id") or "").strip()
            if not media_id or media_id in used_still_media_ids:
                continue

            media_item = media_by_id.get(media_id)
            if media_item is None or str(media_item.get("media_kind") or "") != "image":
                continue

            insight = insight_by_id.get(media_id)
            scene_guess = str((insight or {}).get("scene_guess") or "").lower()
            use_case = str((insight or {}).get("use_case") or "").lower()
            rank = float(candidate.get("score") or 0.0) + 18

            if use_case in preferred_use_cases:
                rank += 8
            if any(keyword in scene_guess for keyword in scene_keywords):
                rank += 5
            if role == "Closer":
                rank += 2
            if role == "Detail":
                aspect_ratio = self._aspect_ratio(media_item)
                if aspect_ratio and aspect_ratio < 1.0:
                    rank += 1.5

            rank_tuple = (rank, -index)
            if best_rank is None or rank_tuple > best_rank:
                best_rank = rank_tuple
                best_candidate = candidate

        return best_candidate

    def _pick_reel_plan_candidate(
        self,
        ordered_candidates: list[dict[str, Any]],
        media_by_id: dict[str, dict[str, Any]],
        insight_by_id: dict[str, dict[str, Any]],
        used_media_ids: set[str],
        *,
        preferred_kinds: set[str],
        preferred_use_cases: set[str],
        scene_keywords: set[str],
        role: str,
    ) -> dict[str, Any] | None:
        best_candidate: dict[str, Any] | None = None
        best_rank: tuple[float, int] | None = None

        for index, candidate in enumerate(ordered_candidates):
            media_id = str(candidate.get("media_id") or "").strip()
            if not media_id or media_id in used_media_ids:
                continue

            media_item = media_by_id.get(media_id)
            if media_item is None:
                continue

            media_kind = str(media_item.get("media_kind") or "unknown")
            insight = insight_by_id.get(media_id)
            scene_guess = str((insight or {}).get("scene_guess") or "").lower()
            use_case = str((insight or {}).get("use_case") or "").lower()
            rank = float(candidate.get("score") or 0.0)

            if media_kind in preferred_kinds:
                rank += 20
            if use_case in preferred_use_cases:
                rank += 8
            if any(keyword in scene_guess for keyword in scene_keywords):
                rank += 5

            if role == "Hook" and media_kind == "video":
                rank += 4
                if self._to_int(media_item.get("analysis_frame_count")):
                    rank += 3
            if role == "Closer" and media_kind == "image":
                rank += 2
            if role == "Detail" and media_kind == "image":
                aspect_ratio = self._aspect_ratio(media_item)
                if aspect_ratio and aspect_ratio < 1.0:
                    rank += 1.5

            rank_tuple = (rank, -index)
            if best_rank is None or rank_tuple > best_rank:
                best_rank = rank_tuple
                best_candidate = candidate

        return best_candidate

    def _select_video_clip_window(
        self,
        media_item: dict[str, Any],
        *,
        role: str,
        usage_index: int,
    ) -> tuple[float | None, float | None]:
        duration = self._to_float(media_item.get("duration_seconds"))
        if duration is None or duration <= 0:
            return None, None

        suggested_duration = self._suggest_reel_step_duration(media_item, role=role)
        timestamps = [
            round(float(timestamp), 2)
            for timestamp in (media_item.get("analysis_frame_timestamps_seconds") or [])
            if self._to_float(timestamp) is not None and 0 <= float(timestamp) <= duration
        ]
        if not timestamps:
            timestamps = [round(duration * anchor, 2) for anchor in (0.18, 0.5, 0.82)]

        role_index = {
            "Hook": 0,
            "Establish": 1,
            "Detail": 1,
            "Closer": 2,
        }.get(role, 1)
        chosen_index = min(role_index + usage_index, len(timestamps) - 1)
        anchor_timestamp = timestamps[max(chosen_index, 0)]

        start = max(0.0, anchor_timestamp - (suggested_duration / 2))
        if start + suggested_duration > duration:
            start = max(0.0, duration - suggested_duration)
        end = min(duration, start + suggested_duration)
        return round(start, 2), round(end, 2)

    def _suggest_reel_step_duration(self, media_item: dict[str, Any], *, role: str) -> float:
        media_kind = str(media_item.get("media_kind") or "unknown")
        if media_kind == "video":
            duration = self._to_float(media_item.get("duration_seconds")) or 4.0
            clipped = min(max(duration * 0.45, 2.2), 5.0)
            if role == "Hook":
                return min(clipped, 3.6)
            if role == "Closer":
                return min(max(clipped, 2.8), 4.8)
            return clipped

        base_duration = {
            "Hook": 1.8,
            "Establish": 2.2,
            "Detail": 1.7,
            "Closer": 2.1,
        }.get(role, 1.9)
        aspect_ratio = self._aspect_ratio(media_item)
        if aspect_ratio and aspect_ratio < 0.9 and role in {"Hook", "Detail"}:
            base_duration += 0.2
        return base_duration

    @staticmethod
    def _build_reel_step_instruction(media_item: dict[str, Any], *, role: str) -> str:
        media_kind = str(media_item.get("media_kind") or "unknown")
        if media_kind == "video":
            instructions = {
                "Hook": "Open on the strongest motion beat and trim in fast.",
                "Establish": "Keep only the clearest movement that places the viewer in the scene.",
                "Detail": "Trim to the most textured or informative moment from the clip.",
                "Closer": "Let this clip breathe slightly longer before the ending caption.",
            }
            return instructions.get(role, "Trim this clip to the cleanest visual beat.")

        instructions = {
            "Hook": "Start with a quick punch-in or subtle zoom for immediate impact.",
            "Establish": "Hold long enough to place the viewer in the location.",
            "Detail": "Use a gentle zoom or crop to emphasize the texture and shape.",
            "Closer": "Hold this frame as the final visual beat before the post ends.",
        }
        return instructions.get(role, "Use this frame as a supporting still in the sequence.")

    @staticmethod
    def _build_reel_step_reason(candidate: dict[str, Any], insight: dict[str, Any] | None) -> str:
        base_reason = str(candidate.get("reason") or "Useful reel beat.").strip()
        scene_guess = str((insight or {}).get("scene_guess") or "").strip()
        if not scene_guess:
            return base_reason
        return f"{base_reason}. AI read: {scene_guess}."

    @staticmethod
    def _build_reel_title(album: dict[str, Any], *, caption_ideas: list[str]) -> str:
        if caption_ideas:
            caption_title = str(caption_ideas[0]).strip()
            if caption_title:
                return caption_title[:72]
        name = str(album.get("name") or "").strip()
        if name:
            return name[:72]
        description = str(album.get("description") or "").strip()
        if description:
            compact = description.split(".")[0].strip()
            if compact:
                return compact[:72]
        return "travel reel draft"

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized[:80] or "travel-reel"

    @staticmethod
    def _aspect_ratio(media_item: dict[str, Any]) -> float | None:
        width = AlbumSuggestionService._to_float(media_item.get("width"))
        height = AlbumSuggestionService._to_float(media_item.get("height"))
        if width is None or height in {None, 0}:
            return None
        return width / height

    @staticmethod
    def _base_rank_score(media_item: dict[str, Any]) -> float:
        score = AlbumSuggestionService._to_float(media_item.get("media_score")) or 0.0
        if media_item.get("gps"):
            score += 1.5
        if media_item.get("captured_at"):
            score += 1
        return round(score, 3)

    @staticmethod
    def _build_group_key(media_item: dict[str, Any]) -> str:
        stem = Path(str(media_item.get("original_filename") or media_item.get("stored_filename") or "")).stem.lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", stem)
        tokens = [token for token in normalized.split() if token and token not in {"img", "image", "photo", "video", "mov", "copy", "edited", "edit", "final"}]
        while tokens and tokens[-1].isdigit():
            tokens.pop()
        compact = " ".join(token for token in tokens if not token.isdigit()).strip()
        if not compact:
            compact = normalized.strip() or str(media_item.get("id"))
        return f"{media_item.get('media_kind', 'unknown')}::{compact}"

    @staticmethod
    def _build_group_label(group_key: str, ranked_items: list[dict[str, Any]]) -> str:
        _, _, raw_label = group_key.partition("::")
        label = raw_label.replace("_", " ").strip()
        if not label:
            label = ranked_items[0].get("media_kind", "media")
        return label[:64]

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value in {None, ""}:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            if value in {None, ""}:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
