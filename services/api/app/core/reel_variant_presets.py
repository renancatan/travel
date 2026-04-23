from __future__ import annotations

from copy import deepcopy
from typing import Any


REEL_CREATIVE_PROFILES: list[dict[str, Any]] = [
    {
        "profile_id": "balanced",
        "label_suffix": "Balanced",
        "creative_angle": "balanced story",
        "title_seed_offset": 0,
        "candidate_mode": "default",
        "max_video_steps_delta": 0,
        "window_selection_offset": 0,
    },
    {
        "profile_id": "motion",
        "label_suffix": "Motion-first",
        "creative_angle": "motion-led adventure",
        "title_seed_offset": 1,
        "candidate_mode": "motion",
        "max_video_steps_delta": 1,
        "window_selection_offset": 1,
    },
    {
        "profile_id": "scenic",
        "label_suffix": "Scenic",
        "creative_angle": "still-rich scenic journey",
        "title_seed_offset": 2,
        "candidate_mode": "scenic",
        "max_video_steps_delta": -1,
        "window_selection_offset": 2,
    },
]

SHORT_FORM_PRESETS: list[dict[str, Any]] = [
    {
        "variant_id": "quick-10",
        "label": "Quick 10s",
        "creative_angle": "fast hook",
        "target_duration_seconds": 10.0,
        "title_seed_index": 0,
        "max_video_steps": 2,
        "role_specs": [
            {
                "role": "Hook",
                "preferred_kinds": ["video"],
                "preferred_use_cases": ["cover", "people"],
                "scene_keywords": ["motion", "entrance", "opening", "people", "water"],
            },
            {
                "role": "Establish",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["entrance", "forest", "view", "outside", "opening"],
            },
            {
                "role": "Detail",
                "preferred_kinds": ["image"],
                "preferred_use_cases": ["detail"],
                "scene_keywords": ["detail", "close", "texture", "formation"],
            },
            {
                "role": "Closer",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting", "people"],
                "scene_keywords": ["exit", "light", "outside", "view"],
            },
        ],
    },
    {
        "variant_id": "story-15",
        "label": "Story 15s",
        "creative_angle": "balanced story",
        "target_duration_seconds": 15.0,
        "title_seed_index": 1,
        "max_video_steps": 3,
        "role_specs": [
            {
                "role": "Hook",
                "preferred_kinds": ["video"],
                "preferred_use_cases": ["cover", "people"],
                "scene_keywords": ["motion", "water", "people", "opening"],
            },
            {
                "role": "Establish",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["entrance", "forest", "outside", "view"],
            },
            {
                "role": "Detail",
                "preferred_kinds": ["image"],
                "preferred_use_cases": ["detail"],
                "scene_keywords": ["texture", "formation", "detail", "close"],
            },
            {
                "role": "Reveal",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["cover", "people", "supporting"],
                "scene_keywords": ["light", "opening", "outside", "view", "people"],
            },
            {
                "role": "Closer",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["exit", "light", "outside", "closing"],
            },
        ],
    },
    {
        "variant_id": "extended-30",
        "label": "Extended 30s",
        "creative_angle": "scenic journey",
        "target_duration_seconds": 30.0,
        "title_seed_index": 2,
        "max_video_steps": 3,
        "role_specs": [
            {
                "role": "Hook",
                "preferred_kinds": ["video"],
                "preferred_use_cases": ["cover", "people"],
                "scene_keywords": ["motion", "water", "people", "opening"],
            },
            {
                "role": "Establish",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["entrance", "forest", "outside", "view"],
            },
            {
                "role": "Journey",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["supporting", "people"],
                "scene_keywords": ["path", "inside", "water", "travel", "journey"],
            },
            {
                "role": "Texture",
                "preferred_kinds": ["image"],
                "preferred_use_cases": ["detail"],
                "scene_keywords": ["texture", "formation", "close", "detail"],
            },
            {
                "role": "Scale",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["people", "cover"],
                "scene_keywords": ["people", "opening", "view", "forest"],
            },
            {
                "role": "Reveal",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["light", "outside", "opening", "forest"],
            },
            {
                "role": "Closer",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["exit", "closing", "view", "light"],
            },
        ],
    },
]

LONG_FORM_PRESETS: list[dict[str, Any]] = [
    *SHORT_FORM_PRESETS,
    {
        "variant_id": "longform-60",
        "label": "Long-form 60s",
        "creative_angle": "extended multi-scene story",
        "target_duration_seconds": 60.0,
        "title_seed_index": 2,
        "max_video_steps": 5,
        "role_specs": [
            {
                "role": "Hook",
                "preferred_kinds": ["video"],
                "preferred_use_cases": ["cover", "people"],
                "scene_keywords": ["motion", "opening", "people", "water"],
            },
            {
                "role": "Establish",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["entrance", "outside", "forest", "view"],
            },
            {
                "role": "Journey",
                "preferred_kinds": ["video"],
                "preferred_use_cases": ["supporting", "people"],
                "scene_keywords": ["path", "inside", "movement", "travel", "water"],
            },
            {
                "role": "Detail",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["detail", "supporting"],
                "scene_keywords": ["texture", "formation", "close", "detail"],
            },
            {
                "role": "Scale",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["people", "cover"],
                "scene_keywords": ["people", "opening", "view", "forest"],
            },
            {
                "role": "Reveal",
                "preferred_kinds": ["video", "image"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["light", "outside", "opening", "forest"],
            },
            {
                "role": "Closer",
                "preferred_kinds": ["image", "video"],
                "preferred_use_cases": ["cover", "supporting"],
                "scene_keywords": ["exit", "closing", "view", "light"],
            },
        ],
    },
]

REEL_VARIANT_RULES: dict[str, Any] = {
    "default_policy_id": "short_form",
    "long_form_activation": {
        # Keep the current flow untouched for ordinary clips shorter than five minutes.
        "single_video_duration_seconds": 300.0,
        # This stays intentionally high for now so multiple shorter clips still behave
        # like the current editor until we ship the dedicated heavy-media pipeline.
        "total_video_duration_seconds": 1800.0,
    },
    "policies": {
        "short_form": {
            "policy_id": "short_form",
            "label": "Short-form album",
            "description": "Current fast reel flow for short source clips.",
            "preferred_auto_targets_seconds": [10.0, 15.0, 30.0],
            "future_story_bundle_targets_seconds": [10.0, 15.0, 30.0],
            "distinct_story_candidates_per_target": 3,
            "presets": SHORT_FORM_PRESETS,
        },
        "long_form": {
            "policy_id": "long_form",
            "label": "Long-form album",
            "description": "Use longer auto targets and future multi-story generation for heavy source videos.",
            "preferred_auto_targets_seconds": [15.0, 30.0, 60.0],
            "future_story_bundle_targets_seconds": [15.0, 30.0, 60.0],
            "distinct_story_candidates_per_target": 3,
            "presets": LONG_FORM_PRESETS,
        },
    },
}


def _get_policy_record(policy_id: str | None = None) -> dict[str, Any]:
    resolved_policy_id = str(policy_id or REEL_VARIANT_RULES["default_policy_id"])
    policies = REEL_VARIANT_RULES["policies"]
    return deepcopy(policies.get(resolved_policy_id) or policies[REEL_VARIANT_RULES["default_policy_id"]])


def _build_video_duration_stats(media_items: list[dict[str, Any]] | None) -> dict[str, float]:
    durations = [
        max(0.0, float(item.get("duration_seconds") or 0.0))
        for item in (media_items or [])
        if str(item.get("media_kind") or "") == "video"
    ]
    if not durations:
        return {
            "video_count": 0.0,
            "max_single_video_duration_seconds": 0.0,
            "total_video_duration_seconds": 0.0,
        }

    return {
        "video_count": float(len(durations)),
        "max_single_video_duration_seconds": max(durations),
        "total_video_duration_seconds": sum(durations),
    }


def get_reel_variant_policy_id(media_items: list[dict[str, Any]] | None = None) -> str:
    stats = _build_video_duration_stats(media_items)
    activation = REEL_VARIANT_RULES["long_form_activation"]
    if (
        stats["max_single_video_duration_seconds"] > float(activation["single_video_duration_seconds"])
        or stats["total_video_duration_seconds"] > float(activation["total_video_duration_seconds"])
    ):
        return "long_form"
    return str(REEL_VARIANT_RULES["default_policy_id"])


def get_reel_variant_policy(
    media_items: list[dict[str, Any]] | None = None,
    *,
    policy_id: str | None = None,
) -> dict[str, Any]:
    resolved_policy_id = str(policy_id or get_reel_variant_policy_id(media_items))
    return _get_policy_record(resolved_policy_id)


def get_reel_variant_presets(
    media_items: list[dict[str, Any]] | None = None,
    *,
    policy_id: str | None = None,
) -> list[dict[str, Any]]:
    policy = get_reel_variant_policy(media_items, policy_id=policy_id)
    return deepcopy(policy.get("presets") or [])


def get_reel_creative_profiles() -> list[dict[str, Any]]:
    return deepcopy(REEL_CREATIVE_PROFILES)


def get_reel_variant_runtime_presets(policy_id: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "variant_id": str(preset["variant_id"]),
            "label": str(preset["label"]),
            "target_duration_seconds": float(preset["target_duration_seconds"]),
            "creative_angle": str(preset["creative_angle"]),
        }
        for preset in get_reel_variant_presets(policy_id=policy_id)
    ]


def get_reel_variant_runtime_rules() -> dict[str, Any]:
    policy_summaries: list[dict[str, Any]] = []
    for policy_id in REEL_VARIANT_RULES["policies"]:
        policy = _get_policy_record(policy_id)
        policy_summaries.append(
            {
                "policy_id": str(policy["policy_id"]),
                "label": str(policy["label"]),
                "description": str(policy["description"]),
                "preferred_auto_targets_seconds": [
                    round(float(value), 1) for value in policy.get("preferred_auto_targets_seconds") or []
                ],
                "future_story_bundle_targets_seconds": [
                    round(float(value), 1) for value in policy.get("future_story_bundle_targets_seconds") or []
                ],
                "distinct_story_candidates_per_target": int(policy.get("distinct_story_candidates_per_target") or 0),
                "presets": get_reel_variant_runtime_presets(policy_id=policy_id),
            }
        )

    return {
        "default_policy_id": str(REEL_VARIANT_RULES["default_policy_id"]),
        "long_form_activation": {
            "single_video_duration_seconds": round(
                float(REEL_VARIANT_RULES["long_form_activation"]["single_video_duration_seconds"]),
                1,
            ),
            "total_video_duration_seconds": round(
                float(REEL_VARIANT_RULES["long_form_activation"]["total_video_duration_seconds"]),
                1,
            ),
        },
        "creative_profiles": [
            {
                "profile_id": str(profile["profile_id"]),
                "label_suffix": str(profile["label_suffix"]),
                "creative_angle": str(profile["creative_angle"]),
            }
            for profile in REEL_CREATIVE_PROFILES
        ],
        "policies": policy_summaries,
    }
