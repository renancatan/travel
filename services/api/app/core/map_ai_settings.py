from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


# Change this one value if you want the dedicated map AI flow to use a different model route.
DEFAULT_MAP_AI_MODEL_ALIAS = "gpt4o"


@dataclass(frozen=True)
class MapAiSettings:
    model_alias: str


@lru_cache
def get_map_ai_settings() -> MapAiSettings:
    model_alias = os.getenv("TRAVEL_MAP_AI_MODEL_ALIAS", DEFAULT_MAP_AI_MODEL_ALIAS).strip() or DEFAULT_MAP_AI_MODEL_ALIAS
    return MapAiSettings(model_alias=model_alias)
