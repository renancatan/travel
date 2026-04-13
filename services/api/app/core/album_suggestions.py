from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from services.api.app.core.llm_router import MultiProviderRouter

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


class AlbumSuggestionService:
    def __init__(self) -> None:
        self.router = MultiProviderRouter()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.gemini_model = os.getenv("GEMINI_REASONING_MODEL") or os.getenv("GEMINI_FAST_MODEL") or "gemini-2.5-flash"
        self.gemini_client = genai.Client(api_key=self.gemini_api_key) if self.gemini_api_key else None

    def generate(self, album: dict[str, Any]) -> dict[str, Any]:
        multimodal_parts = self._build_multimodal_parts(album)
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

        prompt = self._build_text_prompt(album)
        data = self.router.ask_json(prompt, model_alias="ggl2")
        return {
            **self._normalize_suggestion_payload(data, album),
            "analysis_mode": "metadata_fallback",
            "route": self.router.get_last_resolution(),
        }

    def generate_description(self, album: dict[str, Any]) -> dict[str, Any]:
        multimodal_parts = self._build_multimodal_description_parts(album)
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

    def _build_multimodal_parts(self, album: dict[str, Any]) -> list[types.Part]:
        parts: list[types.Part] = [types.Part.from_text(text=self._build_multimodal_prompt(album))]

        image_count = 0
        for media_item in album.get("media_items", []):
            if image_count >= 4:
                break

            content_type = media_item.get("content_type") or ""
            if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
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
            image_count += 1

        return parts if image_count > 0 else []

    def _build_multimodal_description_parts(self, album: dict[str, Any]) -> list[types.Part]:
        parts: list[types.Part] = [types.Part.from_text(text=self._build_description_multimodal_prompt(album))]

        image_count = 0
        for media_item in album.get("media_items", []):
            if image_count >= 4:
                break

            content_type = media_item.get("content_type") or ""
            if content_type not in SUPPORTED_IMAGE_MIME_TYPES:
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
            image_count += 1

        return parts if image_count > 0 else []

    def _build_multimodal_prompt(self, album: dict[str, Any]) -> str:
        return (
            "You are helping a travel-media app understand an uploaded album.\n"
            "Use the album description, filenames, metadata, and attached images.\n"
            "Return strict JSON with keys:\n"
            "album_summary, visual_trip_story, likely_categories, caption_ideas, cover_image_media_id, media_insights.\n"
            "Rules:\n"
            "- likely_categories must be an array of short lowercase strings like cave, beach, bar, boat, food, city, nature, people, travel, general.\n"
            "- caption_ideas must contain exactly 3 concise captions.\n"
            "- media_insights must be an array with items containing media_id, scene_guess, why_it_matters, use_case.\n"
            "- use_case should be one of cover, detail, people, supporting, skip.\n"
            "- If the album description and the actual images disagree, trust the images and mention the mismatch in album_summary.\n"
            f"Album name: {album.get('name')}\n"
            f"Album description: {album.get('description') or 'No description provided.'}\n"
            f"Media count: {len(album.get('media_items', []))}\n"
        )

    def _build_description_multimodal_prompt(self, album: dict[str, Any]) -> str:
        return (
            "You are helping a travel-media app create a concise album description from uploaded media.\n"
            "Use the attached images, filenames, and metadata. Return strict JSON with keys:\n"
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
