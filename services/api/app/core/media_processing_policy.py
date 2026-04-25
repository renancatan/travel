from __future__ import annotations

from typing import Any


MEDIA_PROCESSING_RULES: dict[str, Any] = {
    "standard_max_duration_seconds": 300.0,
    "long_form_min_duration_seconds": 300.0,
    "heavy_async_min_duration_seconds": 600.0,
    "very_long_min_duration_seconds": 1800.0,
    "large_file_bytes": 500 * 1024 * 1024,
    "very_large_file_bytes": 2 * 1024 * 1024 * 1024,
    "uhd_min_width": 3840,
    "uhd_min_height": 2160,
    "proxy_high_bitrate_bits_per_second": 40_000_000,
}


def classify_media_processing(media_item: dict[str, Any]) -> dict[str, Any]:
    media_kind = str(media_item.get("media_kind") or "unknown")
    if media_kind != "video":
        return {
            "processing_profile": "standard",
            "processing_profile_label": "Standard media",
            "processing_recommendation": "Use the normal interactive album flow.",
            "analysis_strategy": "interactive",
            "is_heavy_video": False,
            "video_duration_tier": None,
            "video_resolution_tier": None,
        }

    duration_seconds = _to_float(media_item.get("duration_seconds")) or 0.0
    file_size_bytes = int(_to_float(media_item.get("file_size_bytes")) or 0)
    width = int(_to_float(media_item.get("width")) or 0)
    height = int(_to_float(media_item.get("height")) or 0)

    duration_tier = _duration_tier(duration_seconds)
    resolution_tier = _resolution_tier(width, height)
    is_uhd = resolution_tier == "uhd_4k"
    is_large_file = file_size_bytes >= int(MEDIA_PROCESSING_RULES["large_file_bytes"])
    is_very_large_file = file_size_bytes >= int(MEDIA_PROCESSING_RULES["very_large_file_bytes"])

    if (
        duration_seconds >= float(MEDIA_PROCESSING_RULES["heavy_async_min_duration_seconds"])
        or is_very_large_file
        or (is_uhd and is_large_file)
    ):
        return {
            "processing_profile": "heavy_async",
            "processing_profile_label": "Heavy video",
            "processing_recommendation": (
                "Extract server keyframes first; create a lighter proxy only when the source size, codec, or downstream work justifies it."
            ),
            "analysis_strategy": "async_proxy_required",
            "is_heavy_video": True,
            "video_duration_tier": duration_tier,
            "video_resolution_tier": resolution_tier,
        }

    if duration_seconds > float(MEDIA_PROCESSING_RULES["standard_max_duration_seconds"]) or is_uhd or is_large_file:
        return {
            "processing_profile": "long_form",
            "processing_profile_label": "Long-form video",
            "processing_recommendation": (
                "Use long-form story candidates and avoid treating this as a single short clip."
            ),
            "analysis_strategy": "long_form_story_candidates",
            "is_heavy_video": False,
            "video_duration_tier": duration_tier,
            "video_resolution_tier": resolution_tier,
        }

    return {
        "processing_profile": "standard",
        "processing_profile_label": "Standard video",
        "processing_recommendation": "Use the normal short-video reel flow.",
        "analysis_strategy": "interactive",
        "is_heavy_video": False,
        "video_duration_tier": duration_tier,
        "video_resolution_tier": resolution_tier,
    }


def get_media_processing_runtime_rules() -> dict[str, Any]:
    return {
        "standard_max_duration_seconds": float(MEDIA_PROCESSING_RULES["standard_max_duration_seconds"]),
        "long_form_min_duration_seconds": float(MEDIA_PROCESSING_RULES["long_form_min_duration_seconds"]),
        "heavy_async_min_duration_seconds": float(MEDIA_PROCESSING_RULES["heavy_async_min_duration_seconds"]),
        "very_long_min_duration_seconds": float(MEDIA_PROCESSING_RULES["very_long_min_duration_seconds"]),
        "large_file_bytes": int(MEDIA_PROCESSING_RULES["large_file_bytes"]),
        "very_large_file_bytes": int(MEDIA_PROCESSING_RULES["very_large_file_bytes"]),
        "uhd_min_width": int(MEDIA_PROCESSING_RULES["uhd_min_width"]),
        "uhd_min_height": int(MEDIA_PROCESSING_RULES["uhd_min_height"]),
        "proxy_high_bitrate_bits_per_second": int(MEDIA_PROCESSING_RULES["proxy_high_bitrate_bits_per_second"]),
    }


def _duration_tier(duration_seconds: float) -> str:
    if duration_seconds <= 0:
        return "unknown"
    if duration_seconds <= float(MEDIA_PROCESSING_RULES["standard_max_duration_seconds"]):
        return "short"
    if duration_seconds < float(MEDIA_PROCESSING_RULES["heavy_async_min_duration_seconds"]):
        return "long"
    if duration_seconds < float(MEDIA_PROCESSING_RULES["very_long_min_duration_seconds"]):
        return "heavy"
    return "very_long"


def _resolution_tier(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown"

    long_edge = max(width, height)
    short_edge = min(width, height)
    if long_edge >= int(MEDIA_PROCESSING_RULES["uhd_min_width"]) and short_edge >= int(MEDIA_PROCESSING_RULES["uhd_min_height"]):
        return "uhd_4k"
    if long_edge >= 1920 and short_edge >= 1080:
        return "fhd"
    if long_edge >= 1280 and short_edge >= 720:
        return "hd"
    return "sd"


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
