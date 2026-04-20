from __future__ import annotations

from copy import deepcopy
from typing import Any


REEL_VARIANT_PRESETS: list[dict[str, Any]] = [
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


def get_reel_variant_presets() -> list[dict[str, Any]]:
    return deepcopy(REEL_VARIANT_PRESETS)


def get_reel_variant_runtime_presets() -> list[dict[str, Any]]:
    return [
        {
            "variant_id": str(preset["variant_id"]),
            "label": str(preset["label"]),
            "target_duration_seconds": float(preset["target_duration_seconds"]),
            "creative_angle": str(preset["creative_angle"]),
        }
        for preset in REEL_VARIANT_PRESETS
    ]
