from __future__ import annotations

from copy import deepcopy
import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency path
    genai = None
    types = None

from services.api.app.core.llm_router import MultiProviderRouter
from services.api.app.core.reel_variant_presets import (
    get_reel_creative_profiles,
    get_reel_variant_policy,
    get_reel_variant_presets,
)
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
        self.max_reel_clip_duration_seconds = float(settings.max_reel_clip_duration_seconds)
        self.max_reel_target_duration_seconds = float(settings.max_reel_target_duration_seconds)

    def generate(
        self,
        album: dict[str, Any],
        *,
        reel_variant_request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
                    reel_variant_request=reel_variant_request,
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
        try:
            data = self.router.ask_json(prompt, model_alias="ggl2")
            normalized_data = self._normalize_suggestion_payload(data, album)
            curation_payload = self._build_curation_payload(
                album,
                media_insights=normalized_data["media_insights"],
                caption_ideas=normalized_data["caption_ideas"],
                reel_variant_request=reel_variant_request,
            )
            return {
                **normalized_data,
                **curation_payload,
                "analysis_mode": "metadata_fallback",
                "route": self.router.get_last_resolution(),
            }
        except Exception as exc:
            normalized_data = self._normalize_suggestion_payload({}, album)
            curation_payload = self._build_curation_payload(
                album,
                media_insights=normalized_data["media_insights"],
                caption_ideas=normalized_data["caption_ideas"],
                reel_variant_request=reel_variant_request,
            )
            return {
                **normalized_data,
                **curation_payload,
                "analysis_mode": "metadata_fallback",
                "route": {
                    **(self.router.get_last_resolution() or {}),
                    "llm_failed": True,
                    "llm_error": str(exc),
                },
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
        try:
            data = self.router.ask_json(prompt, model_alias="ggl2")
            return {
                **self._normalize_description_payload(data),
                "analysis_mode": "metadata_fallback",
                "route": self.router.get_last_resolution(),
            }
        except Exception as exc:
            return {
                **self._normalize_description_payload({}),
                "analysis_mode": "metadata_fallback",
                "route": {
                    **(self.router.get_last_resolution() or {}),
                    "llm_failed": True,
                    "llm_error": str(exc),
                },
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
            "reel_draft_variants": self._normalize_reel_draft_variants(
                album,
                cached_suggestion.get("reel_draft_variants"),
            ) or curation_payload.get("reel_draft_variants", []),
            "reel_draft_versions": self._normalize_reel_draft_versions(
                album,
                cached_suggestion.get("reel_draft_versions"),
            ),
            "reel_variant_request_summary": self._normalize_reel_variant_request_summary(
                cached_suggestion.get("reel_variant_request_summary"),
            ) or curation_payload.get("reel_variant_request_summary"),
            "analysis_mode": str(cached_suggestion.get("analysis_mode") or "cached"),
            "route": cached_suggestion.get("route"),
        }

    def save_reel_draft_version(
        self,
        album: dict[str, Any],
        reel_draft: dict[str, Any],
        *,
        existing_versions: Any = None,
        label: str | None = None,
    ) -> list[dict[str, Any]]:
        versions = self._normalize_reel_draft_versions(album, existing_versions)
        now = datetime.now(UTC).isoformat()
        saved_label = (
            str(label or "").strip()
            or f"Version {len(versions) + 1}"
        )
        return [
            {
                "version_id": str(uuid4()),
                "label": saved_label,
                "created_at": now,
                "updated_at": now,
                "reel_draft": reel_draft,
            },
            *versions,
        ][:20]

    def delete_reel_draft_version(
        self,
        album: dict[str, Any],
        existing_versions: Any,
        *,
        version_id: str,
    ) -> list[dict[str, Any]]:
        versions = self._normalize_reel_draft_versions(album, existing_versions)
        return [version for version in versions if version.get("version_id") != version_id]

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
        return MultiProviderRouter._parse_json_text(text)

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
        reel_variant_request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        media_items = album.get("media_items", [])
        group_map = self._build_group_map(media_items)
        shot_groups = self._build_shot_groups(media_items, group_map)
        cover_candidates = self._select_candidates(media_items, group_map, target="cover", limit=3)
        carousel_candidates = self._select_candidates(media_items, group_map, target="carousel", limit=5)
        reel_candidates = self._select_candidates(media_items, group_map, target="reel", limit=4)
        reel_variants, reel_variant_request_summary = self._build_reel_draft_variants(
            album,
            cover_candidates=cover_candidates,
            carousel_candidates=carousel_candidates,
            reel_candidates=reel_candidates,
            media_insights=media_insights,
            caption_ideas=caption_ideas,
            reel_variant_request=reel_variant_request,
        )
        primary_variant = reel_variants[0] if reel_variants else None

        return {
            "cover_candidates": cover_candidates,
            "carousel_candidates": carousel_candidates,
            "reel_candidates": reel_candidates,
            "reel_plan": primary_variant.get("reel_plan") if primary_variant else None,
            "reel_draft": primary_variant.get("reel_draft") if primary_variant else None,
            "reel_draft_variants": reel_variants,
            "reel_draft_versions": [],
            "reel_variant_request_summary": reel_variant_request_summary,
            "shot_groups": shot_groups,
        }

    def _normalize_reel_variant_request_summary(self, raw_summary: Any) -> dict[str, Any] | None:
        if not isinstance(raw_summary, dict):
            return None

        mode = str(raw_summary.get("mode") or "").strip()
        if mode not in {"auto", "preset", "custom_range"}:
            return None

        normalized_summary: dict[str, Any] = {
            "mode": mode,
            "label": str(raw_summary.get("label") or mode).strip() or mode,
        }
        policy_id = str(raw_summary.get("policy_id") or "").strip()
        if policy_id:
            normalized_summary["policy_id"] = policy_id
        policy_label = str(raw_summary.get("policy_label") or "").strip()
        if policy_label:
            normalized_summary["policy_label"] = policy_label
        preset_variant_id = str(raw_summary.get("preset_variant_id") or "").strip()
        if preset_variant_id:
            normalized_summary["preset_variant_id"] = preset_variant_id

        for field_name in ("target_duration_seconds", "min_duration_seconds", "max_duration_seconds"):
            value = self._to_float(raw_summary.get(field_name))
            if value is not None:
                normalized_summary[field_name] = round(max(0.1, value), 1)

        return normalized_summary

    def _normalize_reel_draft_versions(self, album: dict[str, Any], raw_versions: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_versions, list):
            return []

        normalized_versions: list[dict[str, Any]] = []
        for index, raw_version in enumerate(raw_versions, start=1):
            if not isinstance(raw_version, dict):
                continue

            raw_reel_draft = raw_version.get("reel_draft")
            if not isinstance(raw_reel_draft, dict):
                continue

            try:
                normalized_reel_draft = self.rebuild_reel_draft(
                    album,
                    raw_reel_draft,
                    existing_draft=raw_reel_draft,
                )
            except ValueError:
                continue

            normalized_versions.append(
                {
                    "version_id": str(raw_version.get("version_id") or uuid4()),
                    "label": str(raw_version.get("label") or f"Version {index}").strip() or f"Version {index}",
                    "created_at": str(raw_version.get("created_at") or datetime.now(UTC).isoformat()),
                    "updated_at": str(raw_version.get("updated_at") or raw_version.get("created_at") or datetime.now(UTC).isoformat()),
                    "reel_draft": normalized_reel_draft,
                }
            )

        return normalized_versions

    def _normalize_reel_draft_variants(self, album: dict[str, Any], raw_variants: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_variants, list):
            return []

        normalized_variants: list[dict[str, Any]] = []
        for index, raw_variant in enumerate(raw_variants, start=1):
            if not isinstance(raw_variant, dict):
                continue

            raw_reel_plan = raw_variant.get("reel_plan")
            raw_reel_draft = raw_variant.get("reel_draft")
            if not isinstance(raw_reel_draft, dict):
                continue

            try:
                normalized_reel_draft = self.rebuild_reel_draft(
                    album,
                    raw_reel_draft,
                    existing_draft=raw_reel_draft,
                )
            except ValueError:
                continue

            normalized_variants.append(
                {
                    "variant_id": str(raw_variant.get("variant_id") or f"variant-{index}"),
                    "label": str(raw_variant.get("label") or f"Variant {index}").strip() or f"Variant {index}",
                    "target_duration_seconds": round(
                        float(raw_variant.get("target_duration_seconds") or normalized_reel_draft.get("estimated_total_duration_seconds") or 0.0),
                        1,
                    ),
                    "creative_angle": str(raw_variant.get("creative_angle") or "alternate cut").strip() or "alternate cut",
                    "reel_plan": raw_reel_plan if isinstance(raw_reel_plan, dict) else None,
                    "reel_draft": normalized_reel_draft,
                }
            )

        return normalized_variants

    def _build_reel_draft_variants(
        self,
        album: dict[str, Any],
        *,
        cover_candidates: list[dict[str, Any]],
        carousel_candidates: list[dict[str, Any]],
        reel_candidates: list[dict[str, Any]],
        media_insights: list[dict[str, Any]],
        caption_ideas: list[str],
        reel_variant_request: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        media_by_id = {item["id"]: item for item in album.get("media_items", [])}
        insight_by_id = {
            str(insight.get("media_id")): insight
            for insight in media_insights
            if isinstance(insight, dict) and insight.get("media_id")
        }
        ordered_candidates = self._build_extended_plan_candidates(
            album.get("media_items", []),
            reel_candidates,
            cover_candidates,
            carousel_candidates,
        )
        if not ordered_candidates:
            return [], None

        variant_specs, request_summary = self._resolve_reel_variant_specs(
            media_items=album.get("media_items", []),
            reel_candidates=reel_candidates,
            carousel_candidates=carousel_candidates,
            request=reel_variant_request,
        )
        if not variant_specs:
            return [], request_summary

        variants: list[dict[str, Any]] = []
        seen_variant_signatures: set[str] = set()
        for spec in variant_specs:
            candidate_pool = self._order_candidates_for_variant(
                ordered_candidates,
                media_by_id,
                candidate_mode=str(spec.get("candidate_mode") or "default"),
            )
            title_seed_index = int(spec.get("title_seed_index") or 0)
            title_seed = (
                caption_ideas[title_seed_index]
                if 0 <= title_seed_index < len(caption_ideas)
                else caption_ideas[0]
                if caption_ideas
                else ""
            )
            reel_plan = self._build_reel_plan_variant(
                album,
                ordered_candidates=candidate_pool,
                media_by_id=media_by_id,
                insight_by_id=insight_by_id,
                reel_candidates=reel_candidates,
                cover_candidates=cover_candidates,
                role_specs=spec["role_specs"],
                target_duration_seconds=float(spec["target_duration_seconds"]),
                max_video_steps=int(spec["max_video_steps"]) if spec.get("max_video_steps") is not None else None,
                window_selection_offset=int(spec.get("window_selection_offset") or 0),
            )
            if not reel_plan:
                continue

            reel_draft = self._build_reel_draft(
                album,
                reel_plan=reel_plan,
                caption_ideas=[str(title_seed).strip()] if str(title_seed).strip() else caption_ideas,
            )
            if not reel_draft:
                continue

            variant_signature = json.dumps(
                [
                    {
                        "media_id": step["media_id"],
                        "selection_mode": step["selection_mode"],
                        "clip_start_seconds": step.get("clip_start_seconds"),
                        "clip_end_seconds": step.get("clip_end_seconds"),
                    }
                    for step in reel_draft.get("steps", [])
                ],
                sort_keys=True,
            )
            if variant_signature in seen_variant_signatures:
                continue
            seen_variant_signatures.add(variant_signature)

            variants.append(
                {
                    "variant_id": str(spec["variant_id"]),
                    "label": str(spec["label"]),
                    "target_duration_seconds": round(float(spec["target_duration_seconds"]), 1),
                    "creative_angle": str(spec["creative_angle"]),
                    "reel_plan": reel_plan,
                    "reel_draft": reel_draft,
                }
            )

        return variants, request_summary

    def _resolve_reel_variant_specs(
        self,
        *,
        media_items: list[dict[str, Any]],
        reel_candidates: list[dict[str, Any]],
        carousel_candidates: list[dict[str, Any]],
        request: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        policy = get_reel_variant_policy(media_items)
        presets = get_reel_variant_presets(policy_id=str(policy.get("policy_id") or "short_form"))
        preset_by_id = {str(preset["variant_id"]): preset for preset in presets}
        mode = str((request or {}).get("mode") or "auto").strip() or "auto"

        if mode == "preset":
            preset_variant_id = str((request or {}).get("preset_variant_id") or "").strip()
            preset = preset_by_id.get(preset_variant_id) or (presets[0] if presets else None)
            if preset is None:
                return [], None
            return self._expand_variant_family(
                preset,
                target_duration_seconds=float(preset["target_duration_seconds"]),
                family_label=str(preset["label"]),
                request_mode="preset",
            ), {
                "mode": "preset",
                "label": str(preset["label"]),
                "policy_id": str(policy.get("policy_id") or ""),
                "policy_label": str(policy.get("label") or ""),
                "preset_variant_id": str(preset["variant_id"]),
                "target_duration_seconds": round(float(preset["target_duration_seconds"]), 1),
            }

        if mode == "custom_range":
            minimum = self._to_float((request or {}).get("min_duration_seconds"))
            maximum = self._to_float((request or {}).get("max_duration_seconds"))
            if minimum is None or maximum is None:
                return [], None
            minimum = round(min(max(max(1.0, minimum), 1.0), self.max_reel_target_duration_seconds), 1)
            maximum = round(
                min(
                    max(max(minimum, maximum), minimum),
                    self.max_reel_target_duration_seconds,
                ),
                1,
            )
            target_duration_seconds = self._estimate_reel_target_duration(
                media_items,
                reel_candidates=reel_candidates,
                carousel_candidates=carousel_candidates,
                minimum=minimum,
                maximum=maximum,
                policy=policy,
            )
            custom_variant = self._build_duration_variant_spec(
                presets=presets,
                target_duration_seconds=target_duration_seconds,
                variant_id=f"custom-{str(target_duration_seconds).replace('.', '-')}",
                label=f"Custom {target_duration_seconds:.1f}s",
                creative_angle=f"best cut within {minimum:.1f}s to {maximum:.1f}s",
            )
            return self._expand_variant_family(
                custom_variant,
                target_duration_seconds=target_duration_seconds,
                family_label="Custom range",
                request_mode="custom_range",
            ), {
                "mode": "custom_range",
                "label": f"Custom range {minimum:.1f}s to {maximum:.1f}s",
                "policy_id": str(policy.get("policy_id") or ""),
                "policy_label": str(policy.get("label") or ""),
                "target_duration_seconds": round(target_duration_seconds, 1),
                "min_duration_seconds": minimum,
                "max_duration_seconds": maximum,
            }

        if not presets:
            return [], None

        minimum = min(float(preset["target_duration_seconds"]) for preset in presets)
        maximum = max(float(preset["target_duration_seconds"]) for preset in presets)
        target_duration_seconds = self._estimate_reel_target_duration(
            media_items,
            reel_candidates=reel_candidates,
            carousel_candidates=carousel_candidates,
            minimum=minimum,
            maximum=maximum,
            policy=policy,
        )
        auto_variant = self._build_duration_variant_spec(
            presets=presets,
            target_duration_seconds=target_duration_seconds,
            variant_id=f"auto-{str(target_duration_seconds).replace('.', '-')}",
            label="Auto pick",
            creative_angle="AI-selected best length from this album",
        )
        return self._expand_variant_family(
            auto_variant,
            target_duration_seconds=target_duration_seconds,
            family_label="Auto pick",
            request_mode="auto",
        ), {
            "mode": "auto",
            "label": f"Auto • AI picked {target_duration_seconds:.1f}s",
            "policy_id": str(policy.get("policy_id") or ""),
            "policy_label": str(policy.get("label") or ""),
            "target_duration_seconds": round(target_duration_seconds, 1),
        }

    def _build_duration_variant_spec(
        self,
        *,
        presets: list[dict[str, Any]],
        target_duration_seconds: float,
        variant_id: str,
        label: str,
        creative_angle: str,
    ) -> dict[str, Any]:
        base_preset = min(
            presets,
            key=lambda preset: abs(float(preset.get("target_duration_seconds") or 0.0) - float(target_duration_seconds)),
        )
        return {
            **base_preset,
            "variant_id": variant_id,
            "label": label,
            "creative_angle": creative_angle,
            "target_duration_seconds": round(float(target_duration_seconds), 1),
        }

    def _estimate_reel_target_duration(
        self,
        media_items: list[dict[str, Any]],
        *,
        reel_candidates: list[dict[str, Any]],
        carousel_candidates: list[dict[str, Any]],
        minimum: float,
        maximum: float,
        policy: dict[str, Any] | None = None,
    ) -> float:
        video_items = [item for item in media_items if str(item.get("media_kind") or "") == "video"]
        image_items = [item for item in media_items if str(item.get("media_kind") or "") == "image"]
        total_video_duration = sum(max(0.0, float(item.get("duration_seconds") or 0.0)) for item in video_items)
        max_single_video_duration = max(
            (max(0.0, float(item.get("duration_seconds") or 0.0)) for item in video_items),
            default=0.0,
        )
        strong_video_candidates = sum(
            1
            for candidate in reel_candidates
            if str(candidate.get("media_kind") or "") == "video" and float(candidate.get("score") or 0.0) >= 55.0
        )
        strong_image_candidates = sum(
            1
            for candidate in carousel_candidates
            if str(candidate.get("media_kind") or "") == "image" and float(candidate.get("score") or 0.0) >= 45.0
        )

        richness_score = 0
        richness_score += min(len(media_items), 8)
        richness_score += strong_video_candidates * 2
        richness_score += strong_image_candidates
        richness_score += min(4, int(total_video_duration // 12))
        richness_score += min(2, len(image_items) // 3)

        policy_id = str((policy or {}).get("policy_id") or "short_form")
        preferred_targets = sorted(
            {
                round(float(value), 1)
                for value in ((policy or {}).get("preferred_auto_targets_seconds") or [10.0, 15.0, 30.0])
                if float(value) > 0.0
            }
        )
        targets_in_window = [value for value in preferred_targets if minimum <= value <= maximum]

        if policy_id == "long_form":
            if maximum >= 60.0 and (total_video_duration >= 1800.0 or max_single_video_duration >= 900.0):
                desired_duration_seconds = 60.0
            elif maximum >= 30.0 and (
                total_video_duration >= 300.0
                or max_single_video_duration >= 300.0
                or strong_video_candidates >= 4
                or richness_score >= 9
            ):
                desired_duration_seconds = 30.0
            else:
                desired_duration_seconds = 15.0
        else:
            should_choose_extended = (
                maximum >= 30.0
                and len(media_items) >= 8
                and strong_video_candidates >= 3
                and len(image_items) >= 3
                and total_video_duration >= 75.0
                and strong_image_candidates >= 1
            )

            if should_choose_extended:
                desired_duration_seconds = 30.0
            elif richness_score >= 7:
                desired_duration_seconds = 15.0
            else:
                desired_duration_seconds = 10.0

        if targets_in_window:
            return min(targets_in_window, key=lambda target: abs(target - desired_duration_seconds))

        if maximum > 30.0:
            extension_ratio = min(1.0, max(0.0, (richness_score - 4) / 10))
            desired_duration_seconds = max(
                desired_duration_seconds,
                minimum + ((maximum - minimum) * extension_ratio),
            )

        return round(min(max(desired_duration_seconds, minimum), maximum), 1)

    def _expand_variant_family(
        self,
        base_spec: dict[str, Any],
        *,
        target_duration_seconds: float,
        family_label: str,
        request_mode: str,
    ) -> list[dict[str, Any]]:
        creative_profiles = get_reel_creative_profiles()

        expanded_specs: list[dict[str, Any]] = []
        for profile in creative_profiles:
            base_max_video_steps = int(base_spec.get("max_video_steps") or 0)
            role_specs = self._build_creative_role_specs(base_spec.get("role_specs") or [], profile_id=str(profile["profile_id"]))
            variant_label = (
                f"{family_label} • {profile['label_suffix']}"
                if request_mode in {"auto", "custom_range"}
                else str(profile["label_suffix"])
            )
            expanded_specs.append(
                {
                    **deepcopy(base_spec),
                    "variant_id": f"{base_spec['variant_id']}-{profile['profile_id']}",
                    "label": variant_label,
                    "creative_angle": str(profile["creative_angle"]),
                    "target_duration_seconds": round(float(target_duration_seconds), 1),
                    "title_seed_index": int(base_spec.get("title_seed_index") or 0) + int(profile["title_seed_offset"]),
                    "max_video_steps": max(1, min(len(role_specs), base_max_video_steps + int(profile["max_video_steps_delta"]))),
                    "candidate_mode": str(profile["candidate_mode"]),
                    "window_selection_offset": int(profile.get("window_selection_offset") or 0),
                    "role_specs": role_specs,
                }
            )

        return expanded_specs

    def _build_creative_role_specs(
        self,
        base_role_specs: list[dict[str, Any]],
        *,
        profile_id: str,
    ) -> list[dict[str, Any]]:
        role_specs = deepcopy(base_role_specs)
        if profile_id == "motion":
            for spec in role_specs:
                role = str(spec.get("role") or "")
                scene_keywords = set(spec.get("scene_keywords") or [])
                preferred_use_cases = set(spec.get("preferred_use_cases") or [])
                preferred_kinds = set(spec.get("preferred_kinds") or [])
                if role in {"Hook", "Establish", "Journey", "Reveal", "Scale"}:
                    scene_keywords.update({"motion", "movement", "path", "people", "water"})
                    preferred_use_cases.update({"people", "supporting"})
                if role in {"Detail", "Closer"}:
                    preferred_kinds.update({"video"})
                    scene_keywords.update({"motion", "movement", "light", "path"})
                    preferred_use_cases.update({"supporting", "people"})
                spec["preferred_kinds"] = list(preferred_kinds)
                spec["scene_keywords"] = list(scene_keywords)
                spec["preferred_use_cases"] = list(preferred_use_cases)
            return role_specs

        if profile_id == "scenic":
            for spec in role_specs:
                role = str(spec.get("role") or "")
                scene_keywords = set(spec.get("scene_keywords") or [])
                preferred_use_cases = set(spec.get("preferred_use_cases") or [])
                preferred_kinds = set(spec.get("preferred_kinds") or [])
                if role in {"Establish", "Journey", "Texture", "Scale", "Reveal", "Closer"}:
                    preferred_kinds.update({"image"})
                    scene_keywords.update({"view", "light", "forest", "formation", "texture", "outside"})
                    preferred_use_cases.update({"detail", "cover"})
                spec["preferred_kinds"] = list(preferred_kinds)
                spec["scene_keywords"] = list(scene_keywords)
                spec["preferred_use_cases"] = list(preferred_use_cases)
            return role_specs

        return role_specs

    def _order_candidates_for_variant(
        self,
        ordered_candidates: list[dict[str, Any]],
        media_by_id: dict[str, dict[str, Any]],
        *,
        candidate_mode: str,
    ) -> list[dict[str, Any]]:
        if candidate_mode == "motion":
            return sorted(
                ordered_candidates,
                key=lambda candidate: (
                    0 if str(media_by_id.get(str(candidate.get("media_id") or ""), {}).get("media_kind") or "") == "video" else 1,
                    -float(candidate.get("score") or 0.0),
                ),
            )

        if candidate_mode == "scenic":
            return sorted(
                ordered_candidates,
                key=lambda candidate: (
                    0 if str(media_by_id.get(str(candidate.get("media_id") or ""), {}).get("media_kind") or "") == "image" else 1,
                    -float(candidate.get("score") or 0.0),
                ),
            )

        return ordered_candidates

    def _build_reel_plan_variant(
        self,
        album: dict[str, Any],
        *,
        ordered_candidates: list[dict[str, Any]],
        media_by_id: dict[str, dict[str, Any]],
        insight_by_id: dict[str, dict[str, Any]],
        reel_candidates: list[dict[str, Any]],
        cover_candidates: list[dict[str, Any]],
        role_specs: list[dict[str, Any]],
        target_duration_seconds: float,
        max_video_steps: int | None,
        window_selection_offset: int,
    ) -> dict[str, Any] | None:
        video_strategy, primary_video_id, secondary_video_id = self._decide_video_strategy(
            reel_candidates,
            media_by_id=media_by_id,
        )
        prioritize_video_story = self._should_prioritize_video_story(
            media_by_id,
            target_duration_seconds=target_duration_seconds,
        )
        effective_max_video_steps = max_video_steps
        if prioritize_video_story:
            effective_max_video_steps = (
                len(role_specs)
                if max_video_steps is None
                else max(int(max_video_steps), max(1, len(role_specs) - 1))
            )

        used_still_media_ids: set[str] = set()
        video_use_counts: dict[str, int] = {}
        selected_video_windows: dict[str, list[tuple[float, float]]] = {}
        video_steps_selected = 0
        steps: list[dict[str, Any]] = []
        for spec in role_specs:
            avoid_video = effective_max_video_steps is not None and video_steps_selected >= effective_max_video_steps
            candidate, source_role = self._pick_candidate_for_reel_role(
                ordered_candidates,
                media_by_id=media_by_id,
                insight_by_id=insight_by_id,
                used_still_media_ids=used_still_media_ids,
                primary_video_id=primary_video_id,
                secondary_video_id=secondary_video_id,
                video_strategy=video_strategy,
                role=str(spec["role"]),
                preferred_kinds=set(spec["preferred_kinds"]),
                preferred_use_cases=set(spec["preferred_use_cases"]),
                scene_keywords=set(spec["scene_keywords"]),
                avoid_video=avoid_video,
                prefer_video_story=prioritize_video_story,
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
                    role=str(spec["role"]),
                    usage_index=usage_index,
                    existing_windows=selected_video_windows.get(candidate["media_id"], []),
                    window_selection_offset=window_selection_offset,
                )
                video_use_counts[candidate["media_id"]] = usage_index + 1
                if clip_start_seconds is not None and clip_end_seconds is not None:
                    selected_video_windows.setdefault(candidate["media_id"], []).append(
                        (clip_start_seconds, clip_end_seconds)
                    )
                selection_mode = "video_clip"
                video_steps_selected += 1
            else:
                used_still_media_ids.add(candidate["media_id"])

            steps.append(
                {
                    "step_number": len(steps) + 1,
                    "role": str(spec["role"]),
                    "media_id": candidate["media_id"],
                    "media_kind": media_kind,
                    "source_role": source_role,
                    "selection_mode": selection_mode,
                    "clip_start_seconds": clip_start_seconds,
                    "clip_end_seconds": clip_end_seconds,
                    "suggested_duration_seconds": round(
                        self._suggest_reel_step_duration(media_item, role=str(spec["role"])),
                        1,
                    ),
                    "edit_instruction": self._build_reel_step_instruction(media_item, role=str(spec["role"])),
                    "why": self._build_reel_step_reason(candidate, insight),
                }
            )

        if not steps:
            return None

        steps = self._group_reel_steps_by_media_flow(steps)
        retimed_steps = self._retime_reel_plan_steps(
            steps,
            media_by_id=media_by_id,
            target_duration_seconds=target_duration_seconds,
            prioritize_video_story=prioritize_video_story,
        )
        estimated_total_duration_seconds = round(
            sum(float(step["suggested_duration_seconds"]) for step in retimed_steps),
            1,
        )
        cover_media_id = cover_candidates[0]["media_id"] if cover_candidates else retimed_steps[0]["media_id"]
        return {
            "cover_media_id": cover_media_id,
            "video_strategy": self._derive_video_strategy_from_steps(retimed_steps),
            "estimated_total_duration_seconds": estimated_total_duration_seconds,
            "steps": retimed_steps,
        }

    def _retime_reel_plan_steps(
        self,
        steps: list[dict[str, Any]],
        *,
        media_by_id: dict[str, dict[str, Any]],
        target_duration_seconds: float,
        prioritize_video_story: bool = False,
    ) -> list[dict[str, Any]]:
        if not steps:
            return []

        base_total = sum(float(step.get("suggested_duration_seconds") or 0.0) for step in steps)
        if base_total <= 0:
            return steps

        scale = target_duration_seconds / base_total
        timing_targets = self._build_video_first_timing_targets(
            steps,
            media_by_id=media_by_id,
            target_duration_seconds=target_duration_seconds,
            prioritize_video_story=prioritize_video_story,
        )
        base_video_total = sum(
            float(step.get("suggested_duration_seconds") or 0.0)
            for step in steps
            if str(step.get("media_kind") or "") == "video"
        )
        base_still_total = max(0.0, base_total - base_video_total)
        video_scale = scale
        still_scale = scale

        if timing_targets is not None and base_video_total > 0:
            desired_still_total = min(
                timing_targets["max_total_still_duration"],
                base_still_total * scale if base_still_total > 0 else 0.0,
            )
            desired_video_total = max(
                timing_targets["min_total_video_duration"],
                target_duration_seconds - desired_still_total,
            )
            remaining_target = max(0.0, target_duration_seconds - desired_video_total)
            desired_still_total = min(desired_still_total, remaining_target)
            video_scale = desired_video_total / base_video_total
            if base_still_total > 0:
                still_scale = desired_still_total / base_still_total
            else:
                still_scale = 1.0

        retimed_steps: list[dict[str, Any]] = []
        video_use_counts: dict[str, int] = {}

        for step in steps:
            media_id = str(step.get("media_id") or "")
            media_item = media_by_id.get(media_id)
            if media_item is None:
                retimed_steps.append(step)
                continue

            next_step = dict(step)
            media_kind = str(step.get("media_kind") or "")
            step_scale = video_scale if media_kind == "video" else still_scale
            scaled_duration = round(max(0.3, float(step.get("suggested_duration_seconds") or 0.0) * step_scale), 1)
            if media_kind == "video":
                usage_index = video_use_counts.get(media_id, 0)
                clip_start_seconds = self._to_float(step.get("clip_start_seconds"))
                normalized_start, normalized_end = self._normalize_video_window(
                    media_item,
                    role=str(step.get("role") or "Beat"),
                    clip_start_seconds=clip_start_seconds,
                    clip_end_seconds=(clip_start_seconds or 0.0) + scaled_duration if clip_start_seconds is not None else None,
                    usage_index=usage_index,
                )
                video_use_counts[media_id] = usage_index + 1
                next_step["clip_start_seconds"] = normalized_start
                next_step["clip_end_seconds"] = normalized_end
                next_step["suggested_duration_seconds"] = round(max(0.3, normalized_end - normalized_start), 1)
            else:
                still_step_cap = (
                    timing_targets["max_still_step_duration"]
                    if timing_targets is not None
                    else self.max_reel_clip_duration_seconds
                )
                next_step["suggested_duration_seconds"] = round(
                    min(still_step_cap, self.max_reel_clip_duration_seconds, max(0.5, scaled_duration)),
                    1,
                )

            retimed_steps.append(next_step)

        return [
            {
                **step,
                "step_number": index + 1,
            }
            for index, step in enumerate(retimed_steps)
        ]

    def _build_video_first_timing_targets(
        self,
        steps: list[dict[str, Any]],
        *,
        media_by_id: dict[str, dict[str, Any]],
        target_duration_seconds: float,
        prioritize_video_story: bool,
    ) -> dict[str, float] | None:
        if not prioritize_video_story or target_duration_seconds < 45.0:
            return None

        video_steps = [step for step in steps if str(step.get("media_kind") or "") == "video"]
        still_steps = [step for step in steps if str(step.get("media_kind") or "") == "image"]
        if not video_steps:
            return None

        max_single_video_duration = max(
            (
                max(0.0, float(media_by_id.get(str(step.get("media_id") or ""), {}).get("duration_seconds") or 0.0))
                for step in video_steps
            ),
            default=0.0,
        )
        if max_single_video_duration < 600.0:
            return None

        max_still_step_duration = round(min(3.0, max(1.8, target_duration_seconds * 0.05)), 1)
        minimum_video_share = 0.84 if target_duration_seconds >= 55.0 else 0.8
        max_total_still_duration = round(
            min(
                target_duration_seconds * (1.0 - minimum_video_share),
                len(still_steps) * max_still_step_duration,
            ),
            1,
        )

        return {
            "max_still_step_duration": max_still_step_duration,
            "max_total_still_duration": max_total_still_duration,
            "min_total_video_duration": round(max(0.0, target_duration_seconds - max_total_still_duration), 1),
        }

    @staticmethod
    def _group_reel_steps_by_media_flow(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not steps:
            return []

        first_video_index_by_media: dict[str, int] = {}
        grouped_video_steps: dict[str, list[dict[str, Any]]] = {}
        image_steps: list[dict[str, Any]] = []

        for index, step in enumerate(steps):
            media_kind = str(step.get("media_kind") or "")
            media_id = str(step.get("media_id") or "")
            if media_kind == "video" and media_id:
                first_video_index_by_media.setdefault(media_id, index)
                grouped_video_steps.setdefault(media_id, []).append(step)
            else:
                image_steps.append(step)

        ordered_steps: list[dict[str, Any]] = []
        for media_id, _ in sorted(first_video_index_by_media.items(), key=lambda item: item[1]):
            ordered_steps.extend(grouped_video_steps.get(media_id, []))
        ordered_steps.extend(image_steps)

        return [
            {
                **step,
                "step_number": index + 1,
            }
            for index, step in enumerate(ordered_steps)
        ]

    def rebuild_reel_draft(
        self,
        album: dict[str, Any],
        edited_draft: dict[str, Any],
        *,
        existing_draft: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        media_by_id = {item["id"]: item for item in album.get("media_items", [])}
        raw_steps = edited_draft.get("steps") or []
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("The edited reel draft does not include any steps.")

        draft_steps: list[dict[str, Any]] = []
        video_use_counts: dict[str, int] = {}

        for index, raw_step in enumerate(raw_steps, start=1):
            media_id = str(raw_step.get("media_id") or "").strip()
            media_item = media_by_id.get(media_id)
            if media_item is None:
                raise ValueError(f"Draft step {index} points to media that is not in this album.")

            role = str(raw_step.get("role") or f"Step {index}").strip() or "Beat"
            media_kind = str(media_item.get("media_kind") or "unknown")
            source_role = str(raw_step.get("source_role") or "").strip()
            edit_instruction = str(raw_step.get("edit_instruction") or "").strip()
            why = str(raw_step.get("why") or "").strip()

            if media_kind == "video":
                clip_start_seconds = self._to_float(raw_step.get("clip_start_seconds"))
                clip_end_seconds = self._to_float(raw_step.get("clip_end_seconds"))
                usage_index = video_use_counts.get(media_id, 0)
                clip_start_seconds, clip_end_seconds = self._normalize_video_window(
                    media_item,
                    role=role,
                    clip_start_seconds=clip_start_seconds,
                    clip_end_seconds=clip_end_seconds,
                    usage_index=usage_index,
                )
                video_use_counts[media_id] = usage_index + 1
                suggested_duration_seconds = round(max(0.3, clip_end_seconds - clip_start_seconds), 1)
                selection_mode = "video_clip"
                normalized_source_role = source_role or ("hero_video" if index == 1 else "supporting_video")
                frame_mode = None
                focus_x_percent = None
                focus_y_percent = None
            else:
                clip_start_seconds = None
                clip_end_seconds = None
                suggested_duration_seconds = round(
                    min(
                        self.max_reel_clip_duration_seconds,
                        max(0.5, float(raw_step.get("suggested_duration_seconds") or self._suggest_reel_step_duration(media_item, role=role))),
                    ),
                    1,
                )
                selection_mode = "full_frame"
                normalized_source_role = source_role or "still_image"
                frame_mode = self._normalize_frame_mode(raw_step.get("frame_mode"))
                focus_x_percent = self._normalize_focus_percent(raw_step.get("focus_x_percent"))
                focus_y_percent = self._normalize_focus_percent(raw_step.get("focus_y_percent"))

            draft_steps.append(
                {
                    "step_number": index,
                    "role": role,
                    "media_id": media_id,
                    "original_filename": media_item.get("original_filename") or media_id,
                    "media_kind": media_kind,
                    "has_audio": media_item.get("has_audio"),
                    "source_role": normalized_source_role,
                    "selection_mode": selection_mode,
                    "clip_start_seconds": clip_start_seconds,
                    "clip_end_seconds": clip_end_seconds,
                    "frame_mode": frame_mode,
                    "focus_x_percent": focus_x_percent,
                    "focus_y_percent": focus_y_percent,
                    "relative_path": media_item.get("relative_path", ""),
                    "suggested_duration_seconds": suggested_duration_seconds,
                    "edit_instruction": edit_instruction or self._build_reel_step_instruction(media_item, role=role),
                    "why": why or "Edited manually before render.",
                }
            )

        asset_ids: list[str] = []
        cover_media_id = str(edited_draft.get("cover_media_id") or "").strip()
        if cover_media_id and cover_media_id in media_by_id:
            asset_ids.append(cover_media_id)
        for step in draft_steps:
            if step["media_id"] not in asset_ids:
                asset_ids.append(step["media_id"])

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

        derived_video_strategy = self._derive_video_strategy_from_steps(draft_steps)
        title = (
            str(edited_draft.get("title") or "").strip()
            or str(existing_draft.get("title") if isinstance(existing_draft, dict) else "").strip()
            or self._build_reel_title(album, caption_ideas=[])
        )
        caption = (
            str(edited_draft.get("caption") or "").strip()
            or str(existing_draft.get("caption") if isinstance(existing_draft, dict) else "").strip()
            or album.get("description")
            or title
        )
        draft_name = (
            str(existing_draft.get("draft_name") if isinstance(existing_draft, dict) else "").strip()
            or f"{self._slugify(str(album.get('name') or title))}-reel-draft"
        )
        normalized_cover_media_id = cover_media_id if cover_media_id in media_by_id else draft_steps[0]["media_id"]
        audio_strategy = self._normalize_audio_strategy(
            edited_draft.get("audio_strategy")
            if isinstance(edited_draft, dict) and edited_draft.get("audio_strategy") is not None
            else existing_draft.get("audio_strategy")
            if isinstance(existing_draft, dict)
            else None
        )
        filter_settings = self._normalize_filter_settings(
            edited_draft.get("filter_settings")
            if isinstance(edited_draft, dict) and edited_draft.get("filter_settings") is not None
            else existing_draft.get("filter_settings")
            if isinstance(existing_draft, dict)
            else None
        )

        reel_draft = {
            "draft_name": draft_name,
            "title": title,
            "caption": caption,
            "cover_media_id": normalized_cover_media_id,
            "video_strategy": derived_video_strategy,
            "estimated_total_duration_seconds": round(sum(step["suggested_duration_seconds"] for step in draft_steps), 1),
            "output_width": 1080,
            "output_height": 1920,
            "fps": 30,
            "audio_strategy": audio_strategy,
            "filter_settings": filter_settings,
            "steps": draft_steps,
            "assets": assets,
        }
        reel_draft["render_spec"] = self._build_reel_render_spec(reel_draft)
        return reel_draft

    @staticmethod
    def _normalize_audio_strategy(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"mute_all_audio", "mute", "remove_audio", "silent"}:
            return "mute_all_audio"
        return "preserve_source_audio"

    @staticmethod
    def _normalize_filter_settings(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            value = {}

        def _coerce(raw: Any, default: float, minimum: float, maximum: float) -> float:
            try:
                numeric = float(raw)
            except (TypeError, ValueError):
                numeric = default
            return round(min(maximum, max(minimum, numeric)), 2)

        return {
            "brightness": _coerce(value.get("brightness"), 0.0, -0.3, 0.3),
            "contrast": _coerce(value.get("contrast"), 1.0, 0.5, 1.8),
            "saturation": _coerce(value.get("saturation"), 1.0, 0.0, 2.0),
        }

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
        selected_video_windows: dict[str, list[tuple[float, float]]] = {}
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
                    existing_windows=selected_video_windows.get(candidate["media_id"], []),
                )
                video_use_counts[candidate["media_id"]] = usage_index + 1
                if clip_start_seconds is not None and clip_end_seconds is not None:
                    selected_video_windows.setdefault(candidate["media_id"], []).append(
                        (clip_start_seconds, clip_end_seconds)
                    )
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

        steps = self._group_reel_steps_by_media_flow(steps)
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
                    "has_audio": media_item.get("has_audio"),
                    "source_role": str(step.get("source_role") or "still_image"),
                    "selection_mode": str(step.get("selection_mode") or "full_frame"),
                    "clip_start_seconds": self._to_float(step.get("clip_start_seconds")),
                    "clip_end_seconds": self._to_float(step.get("clip_end_seconds")),
                    "frame_mode": self._normalize_frame_mode(step.get("frame_mode")) if media_item.get("media_kind") == "image" else None,
                    "focus_x_percent": self._normalize_focus_percent(step.get("focus_x_percent")) if media_item.get("media_kind") == "image" else None,
                    "focus_y_percent": self._normalize_focus_percent(step.get("focus_y_percent")) if media_item.get("media_kind") == "image" else None,
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
            "audio_strategy": "preserve_source_audio",
            "filter_settings": self._normalize_filter_settings(None),
            "steps": draft_steps,
            "assets": assets,
        }
        reel_draft["render_spec"] = self._build_reel_render_spec(reel_draft)
        return reel_draft

    @staticmethod
    def _derive_video_strategy_from_steps(steps: list[dict[str, Any]]) -> str:
        video_media_ids = {str(step.get("media_id") or "") for step in steps if step.get("media_kind") == "video"}
        if len(video_media_ids) >= 2:
            return "multi_clip_sequence"
        if len(video_media_ids) == 1:
            return "hero_video"
        return "still_sequence"

    def _normalize_video_window(
        self,
        media_item: dict[str, Any],
        *,
        role: str,
        clip_start_seconds: float | None,
        clip_end_seconds: float | None,
        usage_index: int,
    ) -> tuple[float, float]:
        duration_seconds = self._to_float(media_item.get("duration_seconds"))
        if clip_start_seconds is None or clip_end_seconds is None or clip_end_seconds <= clip_start_seconds:
            default_start, default_end = self._select_video_clip_window(
                media_item,
                role=role,
                usage_index=usage_index,
            )
            clip_start_seconds = default_start
            clip_end_seconds = default_end

        clip_start_seconds = max(0.0, round(float(clip_start_seconds), 1))
        clip_end_seconds = round(float(clip_end_seconds), 1)
        max_clip_duration_seconds = max(0.5, round(self.max_reel_clip_duration_seconds, 1))

        if duration_seconds is not None:
            max_start = max(duration_seconds - 0.3, 0.0)
            clip_start_seconds = min(clip_start_seconds, max_start)
            clip_end_seconds = min(clip_end_seconds, duration_seconds)

        clip_end_seconds = min(clip_end_seconds, round(clip_start_seconds + max_clip_duration_seconds, 1))

        if clip_end_seconds <= clip_start_seconds:
            clip_end_seconds = round(clip_start_seconds + 0.5, 1)
            if duration_seconds is not None:
                clip_end_seconds = min(clip_end_seconds, duration_seconds)
                if clip_end_seconds <= clip_start_seconds:
                    clip_start_seconds = max(0.0, round(duration_seconds - 0.5, 1))
                    clip_end_seconds = round(duration_seconds, 1)

        return clip_start_seconds, clip_end_seconds

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

    def _build_extended_plan_candidates(
        self,
        media_items: list[dict[str, Any]],
        *candidate_sets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged = self._merge_plan_candidates(*candidate_sets)
        seen_media_ids = {str(candidate.get("media_id") or "").strip() for candidate in merged}

        fallback_candidates: list[dict[str, Any]] = []
        for media_item in media_items:
            media_id = str(media_item.get("id") or "").strip()
            if not media_id or media_id in seen_media_ids:
                continue

            base_score = self._base_rank_score(media_item)
            if base_score <= 0:
                continue

            fallback_candidates.append(
                {
                    "media_id": media_id,
                    "media_kind": str(media_item.get("media_kind") or "unknown"),
                    "score": round(base_score, 1),
                    "reason": "fallback album candidate",
                    "group_id": None,
                }
            )

        fallback_candidates.sort(
            key=lambda item: (
                -float(item.get("score") or 0.0),
                item.get("media_kind") != "image",
                item.get("media_id"),
            )
        )
        return merged + fallback_candidates

    def _build_reel_render_spec(self, reel_draft: dict[str, Any]) -> dict[str, Any]:
        backend_available = shutil.which("ffmpeg") is not None
        audio_strategy = self._normalize_audio_strategy(reel_draft.get("audio_strategy"))
        filter_settings = self._normalize_filter_settings(reel_draft.get("filter_settings"))
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
            has_audio = bool(step.get("has_audio")) if media_kind == "video" else False
            frame_mode = self._normalize_frame_mode(step.get("frame_mode")) if media_kind == "image" else None
            focus_x_percent = self._normalize_focus_percent(step.get("focus_x_percent")) if media_kind == "image" else None
            focus_y_percent = self._normalize_focus_percent(step.get("focus_y_percent")) if media_kind == "image" else None

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
                    "frame_mode": frame_mode,
                    "focus_x_percent": focus_x_percent,
                    "focus_y_percent": focus_y_percent,
                    "output_duration_seconds": output_duration_seconds,
                    "audio_strategy": audio_strategy,
                    "filter_settings": filter_settings,
                }
            )

            shell_commands.append(
                self._build_ffmpeg_clip_command(
                    source_relative_path=source_relative,
                    output_relative_path=output_relative,
                    media_kind=media_kind,
                    has_audio=has_audio,
                    output_duration_seconds=output_duration_seconds,
                    clip_start_seconds=clip_start_seconds,
                    clip_end_seconds=clip_end_seconds,
                    frame_mode=frame_mode,
                    focus_x_percent=focus_x_percent,
                    focus_y_percent=focus_y_percent,
                    audio_strategy=audio_strategy,
                    filter_settings=filter_settings,
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
            "-map 0:v:0 -map 0:a:0 "
            "-c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 2 -movflags +faststart "
            f"{self._shell_quote(output_relative_path)}"
        )

        notes = [
            "This is a render-ready spec for the future reel worker.",
            "Each step first becomes a normalized 1080x1920 clip, then the clips are concatenated.",
        ]
        if audio_strategy == "mute_all_audio":
            notes.append("All beats are rendered with silent filler audio, even when the source videos include sound.")
        else:
            notes.append("Video beats can preserve source audio when it exists; still-image beats use silent filler audio.")
        if any(abs(float(filter_settings[key]) - baseline) > 0.001 for key, baseline in (("brightness", 0.0), ("contrast", 1.0), ("saturation", 1.0))):
            notes.append(
                f"Reel-wide look applied: brightness {filter_settings['brightness']:+.2f}, contrast {filter_settings['contrast']:.2f}, saturation {filter_settings['saturation']:.2f}."
            )
        notes.append("A richer soundtrack and audio-mixing layer has not been implemented yet.")
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
        has_audio: bool,
        output_duration_seconds: float,
        clip_start_seconds: float | None,
        clip_end_seconds: float | None,
        frame_mode: str | None,
        focus_x_percent: float | None,
        focus_y_percent: float | None,
        audio_strategy: str,
        filter_settings: dict[str, float],
    ) -> str:
        if media_kind == "video":
            vf_chain = self._apply_reel_filter_settings_to_vf_chain(
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
                "fps=30",
                filter_settings=filter_settings,
            )
            timing_prefix = ""
            if clip_start_seconds is not None:
                timing_prefix += f"-ss {clip_start_seconds:.2f} "
            if clip_end_seconds is not None:
                timing_prefix += f"-to {clip_end_seconds:.2f} "
            if has_audio and audio_strategy == "preserve_source_audio":
                return (
                    "ffmpeg -y "
                    f"{timing_prefix}-i {self._shell_quote(source_relative_path)} "
                    f"-vf {self._shell_quote(vf_chain)} "
                    "-map 0:v:0 -map 0:a:0 "
                    "-c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 2 -shortest "
                    f"{self._shell_quote(output_relative_path)}"
                )
            return (
                "ffmpeg -y "
                f"{timing_prefix}-i {self._shell_quote(source_relative_path)} "
                f"-f lavfi -t {output_duration_seconds:.1f} -i anullsrc=channel_layout=stereo:sample_rate=48000 "
                f"-vf {self._shell_quote(vf_chain)} "
                "-map 0:v:0 -map 0:a? -map 1:a:0 "
                "-c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 2 -shortest "
                f"{self._shell_quote(output_relative_path)}"
            )

        vf_chain = self._build_image_vf_chain(
            frame_mode=frame_mode,
            focus_x_percent=focus_x_percent,
            focus_y_percent=focus_y_percent,
            filter_settings=filter_settings,
        )
        return (
            "ffmpeg -y "
            f"-loop 1 -t {output_duration_seconds:.1f} -i {self._shell_quote(source_relative_path)} "
            f"-f lavfi -t {output_duration_seconds:.1f} -i anullsrc=channel_layout=stereo:sample_rate=48000 "
            f"-vf {self._shell_quote(vf_chain)} "
            "-map 0:v:0 -map 1:a:0 "
            "-c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 2 -shortest "
            f"{self._shell_quote(output_relative_path)}"
        )

    def _build_image_vf_chain(
        self,
        *,
        frame_mode: str | None,
        focus_x_percent: float | None,
        focus_y_percent: float | None,
        filter_settings: dict[str, float],
    ) -> str:
        normalized_frame_mode = self._normalize_frame_mode(frame_mode)
        if normalized_frame_mode != "cover":
            return self._apply_reel_filter_settings_to_vf_chain(
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
                "fps=30",
                filter_settings=filter_settings,
            )

        x_ratio = self._normalize_focus_percent(focus_x_percent) / 100
        y_ratio = self._normalize_focus_percent(focus_y_percent) / 100
        return self._apply_reel_filter_settings_to_vf_chain(
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(iw-1080)*{x_ratio:.3f}:(ih-1920)*{y_ratio:.3f},"
            "fps=30",
            filter_settings=filter_settings,
        )

    @staticmethod
    def _apply_reel_filter_settings_to_vf_chain(base_chain: str, *, filter_settings: dict[str, float]) -> str:
        brightness = round(float(filter_settings.get("brightness", 0.0)), 2)
        contrast = round(float(filter_settings.get("contrast", 1.0)), 2)
        saturation = round(float(filter_settings.get("saturation", 1.0)), 2)
        if abs(brightness) <= 0.001 and abs(contrast - 1.0) <= 0.001 and abs(saturation - 1.0) <= 0.001:
            return base_chain
        return f"{base_chain},eq=brightness={brightness:.2f}:contrast={contrast:.2f}:saturation={saturation:.2f}"

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
        avoid_video: bool = False,
        prefer_video_story: bool = False,
    ) -> tuple[dict[str, Any] | None, str]:
        if avoid_video:
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

        if not avoid_video and role == "Hook" and primary_video_id:
            candidate = self._find_candidate_by_media_id(ordered_candidates, primary_video_id)
            if candidate is not None:
                return candidate, "hero_video"

        if not avoid_video and role == "Establish":
            if video_strategy == "multi_clip_sequence" and secondary_video_id:
                candidate = self._find_candidate_by_media_id(ordered_candidates, secondary_video_id)
                if candidate is not None:
                    return candidate, "supporting_video"
            if video_strategy == "hero_video" and primary_video_id:
                candidate = self._find_candidate_by_media_id(ordered_candidates, primary_video_id)
                if candidate is not None:
                    return candidate, "hero_video"

        if role in {"Detail", "Closer"} and "video" not in preferred_kinds:
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

        effective_preferred_kinds = preferred_kinds
        if avoid_video:
            effective_preferred_kinds = {kind for kind in preferred_kinds if kind != "video"} or {"image"}

        candidate = self._pick_reel_plan_candidate(
            ordered_candidates,
            media_by_id,
            insight_by_id,
            used_still_media_ids,
            preferred_kinds=effective_preferred_kinds,
            preferred_use_cases=preferred_use_cases,
            scene_keywords=scene_keywords,
            role=role,
            prefer_video_story=prefer_video_story,
        )
        if candidate is None and avoid_video:
            candidate = self._pick_reel_plan_candidate(
                ordered_candidates,
                media_by_id,
                insight_by_id,
                used_still_media_ids,
                preferred_kinds=preferred_kinds,
                preferred_use_cases=preferred_use_cases,
                scene_keywords=scene_keywords,
                role=role,
                prefer_video_story=prefer_video_story,
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
        prefer_video_story: bool = False,
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
            if prefer_video_story:
                if media_kind == "video":
                    rank += 10
                elif media_kind == "image":
                    rank -= 4

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

    def _should_prioritize_video_story(
        self,
        media_by_id: dict[str, dict[str, Any]],
        *,
        target_duration_seconds: float,
    ) -> bool:
        if target_duration_seconds < 45.0:
            return False

        for media_item in media_by_id.values():
            if str(media_item.get("media_kind") or "") != "video":
                continue

            duration_seconds = self._to_float(media_item.get("duration_seconds")) or 0.0
            if duration_seconds >= 600.0:
                return True

            if bool(media_item.get("is_heavy_video")):
                return True

            processing_profile = str(media_item.get("processing_profile") or "")
            if processing_profile == "heavy_async":
                return True

            duration_tier = str(media_item.get("video_duration_tier") or "")
            if duration_tier in {"heavy", "very_long"}:
                return True

        return False

    def _select_video_clip_window(
        self,
        media_item: dict[str, Any],
        *,
        role: str,
        usage_index: int,
        existing_windows: list[tuple[float, float]] | None = None,
        window_selection_offset: int = 0,
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
        candidate_windows = self._build_video_window_candidates(
            duration_seconds=duration,
            suggested_duration_seconds=suggested_duration,
            analysis_timestamps=timestamps,
            role=role,
        )
        if not candidate_windows:
            start = max(0.0, min(duration - suggested_duration, duration * 0.18))
            end = min(duration, start + suggested_duration)
            return round(start, 2), round(end, 2)

        normalized_existing_windows = existing_windows or []
        combined_index = max(0, usage_index + window_selection_offset)
        available_windows = [
            window
            for window in candidate_windows
            if all(self._window_overlap_ratio(window, previous_window) < 0.55 for previous_window in normalized_existing_windows)
        ]
        if available_windows:
            chosen_index = min(combined_index, len(available_windows) - 1)
            start, end = available_windows[chosen_index]
            return round(start, 2), round(end, 2)

        distinct_windows: list[tuple[float, float]] = []
        for window in candidate_windows:
            if not distinct_windows:
                distinct_windows.append(window)
                continue

            if all(self._window_overlap_ratio(window, previous_window) < 0.55 for previous_window in distinct_windows):
                distinct_windows.append(window)

        if distinct_windows:
            chosen_index = min(combined_index, len(distinct_windows) - 1)
            start, end = distinct_windows[chosen_index]
            return round(start, 2), round(end, 2)

        chosen_index = min(combined_index, len(candidate_windows) - 1)
        start, end = candidate_windows[chosen_index]
        return round(start, 2), round(end, 2)

    def _build_video_window_candidates(
        self,
        *,
        duration_seconds: float,
        suggested_duration_seconds: float,
        analysis_timestamps: list[float],
        role: str,
    ) -> list[tuple[float, float]]:
        if duration_seconds <= 0:
            return []

        normalized_duration = max(0.5, min(suggested_duration_seconds, duration_seconds))
        role_target_ratios = {
            "Hook": [0.12, 0.2, 0.3, 0.45, 0.62, 0.8],
            "Establish": [0.28, 0.4, 0.55, 0.7, 0.18, 0.85],
            "Explore": [0.48, 0.6, 0.36, 0.74, 0.24, 0.88],
            "Journey": [0.5, 0.64, 0.38, 0.78, 0.26, 0.9],
            "Reveal": [0.7, 0.82, 0.56, 0.42, 0.26, 0.92],
            "Scale": [0.66, 0.8, 0.5, 0.34, 0.9],
            "Texture": [0.42, 0.56, 0.3, 0.7, 0.18, 0.84],
            "Detail": [0.44, 0.58, 0.32, 0.72, 0.2, 0.86],
            "Closer": [0.82, 0.7, 0.56, 0.4, 0.92],
        }.get(role, [0.5, 0.36, 0.64, 0.22, 0.82])

        base_anchor_count = max(6, min(10, int(duration_seconds / max(1.5, normalized_duration / 1.8)) + 2))
        timeline_timestamps = [
            round(duration_seconds * ((index + 1) / (base_anchor_count + 1)), 2)
            for index in range(base_anchor_count)
        ]

        raw_anchors: list[tuple[str, float]] = []
        for timestamp in analysis_timestamps:
            raw_anchors.append(("analysis", float(timestamp)))
        for timestamp in timeline_timestamps:
            raw_anchors.append(("timeline", float(timestamp)))

        def window_from_anchor(anchor_timestamp: float) -> tuple[float, float]:
            start = max(0.0, anchor_timestamp - (normalized_duration / 2))
            if start + normalized_duration > duration_seconds:
                start = max(0.0, duration_seconds - normalized_duration)
            end = min(duration_seconds, start + normalized_duration)
            return round(start, 2), round(end, 2)

        ranked_windows: list[tuple[float, float, float, float]] = []
        seen_window_keys: set[tuple[float, float]] = set()

        for source_kind, anchor_timestamp in raw_anchors:
            if anchor_timestamp < 0 or anchor_timestamp > duration_seconds:
                continue

            start, end = window_from_anchor(anchor_timestamp)
            if end - start < 0.3:
                continue

            window_key = (round(start, 1), round(end, 1))
            if window_key in seen_window_keys:
                continue
            seen_window_keys.add(window_key)

            anchor_ratio = anchor_timestamp / duration_seconds if duration_seconds > 0 else 0.5
            closest_role_distance = min(abs(anchor_ratio - ratio) for ratio in role_target_ratios)
            primary_target_distance = abs(anchor_ratio - role_target_ratios[0])
            sampled_bonus = -0.035 if source_kind == "analysis" else 0.0
            ranked_windows.append(
                (
                    round(closest_role_distance + sampled_bonus, 6),
                    round(primary_target_distance, 6),
                    start,
                    end,
                )
            )

        ranked_windows.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        return [(start, end) for _, _, start, end in ranked_windows]

    @staticmethod
    def _window_overlap_ratio(
        first_window: tuple[float, float],
        second_window: tuple[float, float],
    ) -> float:
        first_start, first_end = first_window
        second_start, second_end = second_window
        overlap_start = max(first_start, second_start)
        overlap_end = min(first_end, second_end)
        overlap = max(0.0, overlap_end - overlap_start)
        shortest_window = max(0.1, min(first_end - first_start, second_end - second_start))
        return overlap / shortest_window

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
