from __future__ import annotations

from copy import deepcopy
from typing import Any


# AI feature model map.
#
# Supported aliases are resolved by MultiProviderRouter:
# - "ggl2" = Gemini fast route; quota errors fall back to the Azure GPT-4/4o route.
# - "gpt4" or "gpt4o" = Azure GPT-4/4o route.
# - "gpt5", "gpt54", or "gpt5.4" = Azure GPT-5-family route.
#
# To try a different model, change only the feature's `model_alias`.
# For GPT-5.4 specifically, point AZURE_OPENAI_GPT5_DEPLOYMENT at the
# GPT-5.4 deployment and keep the alias as "gpt54" or "gpt5".
AI_FEATURE_MODELS: dict[str, dict[str, Any]] = {
    "album_review": {
        "label": "ALBUM REVIEW",
        "model_alias": "ggl2",
        "fallback_model_alias": "gpt4o",
        "note": "Main album story/read. Gemini multimodal first when visual inputs exist.",
    },
    "album_description": {
        "label": "ALBUM DESCRIPTION",
        "model_alias": "ggl2",
        "fallback_model_alias": "gpt4o",
        "note": "Short saved album description and categories.",
    },
    "map_entry": {
        "label": "MAP ENTRY",
        "model_alias": "gpt4o",
        "fallback_model_alias": "ggl2",
        "note": "Location hierarchy, map summary, and place metadata.",
    },
    "reel_best_pick": {
        "label": "REEL BEST PICK",
        "model_alias": "ggl2",
        "fallback_model_alias": "gpt4o",
        "note": "Compares already rendered reels; Gemini can inspect contact sheets.",
    },
    "reel_variant_mix": {
        "label": "REEL VARIANT MIX",
        "model_alias": "gpt54",
        "fallback_model_alias": "ggl2",
        "note": "Plans the best-of mix cuts before deterministic render. Falls back to heuristic if AI is unavailable.",
    },
}


def get_ai_feature_model(feature_id: str) -> dict[str, Any]:
    config = AI_FEATURE_MODELS.get(feature_id)
    if config is None:
        raise KeyError(f"Unknown AI feature model: {feature_id}")
    return deepcopy(config)


def get_ai_feature_runtime_models() -> dict[str, dict[str, Any]]:
    return deepcopy(AI_FEATURE_MODELS)
