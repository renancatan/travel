from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from services.api.app.core.ai_feature_models import get_ai_feature_model

# Change the default map route in ai_feature_models.py. Keep this env override
# for local experiments that should not touch the business config file.
DEFAULT_MAP_AI_MODEL_ALIAS = str(get_ai_feature_model("map_entry")["model_alias"])


@dataclass(frozen=True)
class MapAiSettings:
    model_alias: str


@lru_cache
def get_map_ai_settings() -> MapAiSettings:
    model_alias = os.getenv("TRAVEL_MAP_AI_MODEL_ALIAS", DEFAULT_MAP_AI_MODEL_ALIAS).strip() or DEFAULT_MAP_AI_MODEL_ALIAS
    return MapAiSettings(model_alias=model_alias)
