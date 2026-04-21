from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from services.api.app.core.map_ai_settings import get_map_ai_settings
from services.api.app.core.map_place_normalizer import normalize_map_place_fields
from services.api.app.core.llm_router import MultiProviderRouter


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


MAP_GROUPS: dict[str, dict[str, Any]] = {
    "caves": {
        "label": "Caves",
        "icon_key": "caves",
        "keywords": {"cave", "caves", "stalactite", "stalagmite", "spelunk", "underground", "cavern"},
    },
    "beaches": {
        "label": "Beaches",
        "icon_key": "beaches",
        "keywords": {"beach", "beaches", "coast", "coastal", "island", "ocean", "shore", "surf"},
    },
    "bars": {
        "label": "Bars",
        "icon_key": "bars",
        "keywords": {"bar", "bars", "pub", "beer", "cocktail", "nightlife"},
    },
    "boat": {
        "label": "Boat",
        "icon_key": "boat",
        "keywords": {"boat", "boats", "sailing", "ferry", "island-hopping", "bay"},
    },
    "falls": {
        "label": "Falls",
        "icon_key": "falls",
        "keywords": {"falls", "waterfall", "waterfalls", "cascade"},
    },
    "general": {
        "label": "General",
        "icon_key": "general",
        "keywords": set(),
    },
}

PLACE_HINTS: list[dict[str, Any]] = [
    {
        "keywords": {"petar", "iporanga"},
        "country": "Brazil",
        "state": "Sao Paulo",
        "city": "Iporanga",
        "region": "PETAR",
        "location_label": "Iporanga",
        "latitude": -24.5350,
        "longitude": -48.7046,
        "group_key": "caves",
    },
    {
        "keywords": {"eldorado", "caverna", "diabo"},
        "country": "Brazil",
        "state": "Sao Paulo",
        "city": "Eldorado",
        "region": "Vale do Ribeira",
        "location_label": "Eldorado",
        "latitude": -24.6353,
        "longitude": -48.4029,
        "group_key": "caves",
    },
    {
        "keywords": {"guaraquecaba", "paranagua"},
        "country": "Brazil",
        "state": "Parana",
        "city": "Guaraquecaba",
        "region": "Paranagua Bay",
        "location_label": "Guaraquecaba",
        "latitude": -25.2996,
        "longitude": -48.3444,
        "group_key": "boat",
    },
    {
        "keywords": {"cebu"},
        "country": "Philippines",
        "state": "Cebu",
        "city": "Cebu",
        "region": "Visayas",
        "location_label": "Cebu",
        "latitude": 10.3157,
        "longitude": 123.8854,
        "group_key": "general",
    },
    {
        "keywords": {"davao"},
        "country": "Philippines",
        "state": "Davao del Sur",
        "city": "Davao",
        "region": "Mindanao",
        "location_label": "Davao",
        "latitude": 7.1907,
        "longitude": 125.4553,
        "group_key": "general",
    },
]


class MapEntrySuggestionService:
    def __init__(self) -> None:
        self.router = MultiProviderRouter()
        self.map_ai_settings = get_map_ai_settings()

    def generate(
        self,
        album: dict[str, Any],
        *,
        user_prompt: str | None,
        generation_mode: str,
        selected_media_ids: list[str] | None = None,
        selected_reel_draft_name: str | None = None,
        selected_reel_title: str | None = None,
        selected_reel_caption: str | None = None,
        selected_reel_video_strategy: str | None = None,
        existing_entry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fallback_entry = build_auto_map_entry(
            album,
            existing_entry=existing_entry,
            user_prompt=user_prompt,
            selected_media_ids=selected_media_ids,
            selected_reel_draft_name=selected_reel_draft_name,
            source="map_ai_fallback",
        )

        prompt = self._build_prompt(
            album,
            user_prompt=user_prompt,
            generation_mode=generation_mode,
            selected_media_ids=selected_media_ids,
            selected_reel_draft_name=selected_reel_draft_name,
            selected_reel_title=selected_reel_title,
            selected_reel_caption=selected_reel_caption,
            selected_reel_video_strategy=selected_reel_video_strategy,
            fallback_entry=fallback_entry,
        )

        try:
            data = self.router.ask_json(prompt, model_alias=self.map_ai_settings.model_alias)
            return self._normalize_generated_entry(
                album,
                data if isinstance(data, dict) else {},
                fallback_entry=fallback_entry,
                user_prompt=user_prompt,
                selected_media_ids=selected_media_ids,
                selected_reel_draft_name=selected_reel_draft_name,
            )
        except Exception:
            return fallback_entry

    def _build_prompt(
        self,
        album: dict[str, Any],
        *,
        user_prompt: str | None,
        generation_mode: str,
        selected_media_ids: list[str] | None,
        selected_reel_draft_name: str | None,
        selected_reel_title: str | None,
        selected_reel_caption: str | None,
        selected_reel_video_strategy: str | None,
        fallback_entry: dict[str, Any],
    ) -> str:
        media_items = album.get("media_items") or []
        selected_media_summary = []
        selected_media_set = {str(media_id).strip() for media_id in selected_media_ids or [] if str(media_id).strip()}
        for media_item in media_items:
            media_id = str(media_item.get("id") or "").strip()
            if media_id not in selected_media_set:
                continue
            selected_media_summary.append(
                {
                    "media_id": media_id,
                    "filename": media_item.get("original_filename"),
                    "kind": media_item.get("media_kind"),
                    "gps": media_item.get("gps"),
                }
            )

        payload = {
            "album_name": album.get("name"),
            "album_description": album.get("description"),
            "album_summary": (album.get("cached_suggestion") or {}).get("album_summary"),
            "visual_trip_story": (album.get("cached_suggestion") or {}).get("visual_trip_story"),
            "likely_categories": (album.get("cached_suggestion") or {}).get("likely_categories")
            or (album.get("description_meta") or {}).get("likely_categories")
            or [],
            "generation_mode": generation_mode,
            "user_prompt": user_prompt,
            "selected_reel": {
                "draft_name": selected_reel_draft_name,
                "title": selected_reel_title,
                "caption": selected_reel_caption,
                "video_strategy": selected_reel_video_strategy,
            }
            if generation_mode == "chosen_reel"
            else None,
            "selected_media": selected_media_summary,
            "all_filenames": [str(media_item.get("original_filename") or "") for media_item in media_items],
            "gps_points": [
                media_item.get("gps")
                for media_item in media_items
                if isinstance(media_item.get("gps"), dict)
                and isinstance((media_item.get("gps") or {}).get("latitude"), (int, float))
                and isinstance((media_item.get("gps") or {}).get("longitude"), (int, float))
            ],
            "taxonomy": {
                "group_keys": list(MAP_GROUPS.keys()),
                "legacy_location_examples": [
                    {
                        "keywords": sorted(place["keywords"]),
                        "country": place["country"],
                        "state": place["state"],
                        "city": place["city"],
                        "region": place["region"],
                        "location_label": place["location_label"],
                        "group_key": place["group_key"],
                    }
                    for place in PLACE_HINTS
                ],
            },
            "fallback_entry": fallback_entry,
        }

        return (
            "You are generating a structured travel-map draft for a travel media app.\n"
            "This is a separate map AI call, not the album-review call.\n"
            "Resolve the location hierarchy and group taxonomy from the prompt and album context.\n"
            "Priority order for truth:\n"
            "1. user_prompt\n"
            "2. album_description\n"
            "3. selected_reel title/caption/media\n"
            "4. album_summary / trip_story / filenames\n"
            "5. GPS as validation or fallback\n"
            "If a specific named place is strongly implied, trust that over generic GPS.\n"
            "Return strict JSON with keys:\n"
            "title, country, state, city, region, location_label, group_key, summary, selected_media_ids.\n"
            "Rules:\n"
            "- group_key must be one of: caves, beaches, bars, boat, falls, general.\n"
            "- Return country, state, and city using stable common names, not abbreviations.\n"
            "- Example: use Brazil instead of Brasil, Sao Paulo or São Paulo instead of SP.\n"
            "- Prefer the provided selected_media_ids when generation_mode is chosen_reel.\n"
            "- Keep title concise and map-friendly.\n"
            "- Keep summary to 1-2 sentences.\n"
            "- If you are unsure, use the fallback entry values rather than inventing.\n"
            f"Context JSON:\n{payload}\n"
        )

    def _normalize_generated_entry(
        self,
        album: dict[str, Any],
        data: dict[str, Any],
        *,
        fallback_entry: dict[str, Any],
        user_prompt: str | None,
        selected_media_ids: list[str] | None,
        selected_reel_draft_name: str | None,
    ) -> dict[str, Any]:
        valid_media_ids = {str(item.get('id') or '').strip() for item in album.get("media_items") or []}
        candidate_media_ids = [
            media_id
            for media_id in (
                str(media_id).strip() for media_id in data.get("selected_media_ids") or selected_media_ids or []
            )
            if media_id and media_id in valid_media_ids
        ]

        group_key = normalize_group_key(data.get("group_key") or fallback_entry.get("group_key"))
        normalized_place_fields = normalize_map_place_fields(
            title=data.get("title") or fallback_entry.get("title") or album.get("name") or "Trip stop",
            country=data.get("country") or fallback_entry.get("country"),
            state=data.get("state") or fallback_entry.get("state"),
            city=data.get("city") or fallback_entry.get("city"),
            region=data.get("region") or fallback_entry.get("region"),
            location_label=data.get("location_label") or fallback_entry.get("location_label"),
            group_key=group_key,
        )
        now = _utc_now()
        return {
            "album_id": album["id"],
            "album_name": album.get("name") or "Untitled album",
            "title": normalized_place_fields["title"],
            "latitude": float(data.get("latitude") if isinstance(data.get("latitude"), (int, float)) else fallback_entry["latitude"]),
            "longitude": float(
                data.get("longitude") if isinstance(data.get("longitude"), (int, float)) else fallback_entry["longitude"]
            ),
            "country": normalized_place_fields["country"],
            "state": normalized_place_fields["state"],
            "city": normalized_place_fields["city"],
            "region": normalized_place_fields["region"],
            "location_label": normalized_place_fields["location_label"],
            "country_slug": normalized_place_fields["country_slug"],
            "state_slug": normalized_place_fields["state_slug"],
            "city_slug": normalized_place_fields["city_slug"],
            "region_slug": normalized_place_fields["region_slug"],
            "location_slug": normalized_place_fields["location_slug"],
            "title_slug": normalized_place_fields["title_slug"],
            "storage_path": normalized_place_fields["storage_path"],
            "group_key": group_key,
            "icon_key": group_to_icon_key(group_key),
            "summary": str(data.get("summary") or fallback_entry.get("summary") or "").strip() or None,
            "selected_media_ids": candidate_media_ids[:8] or fallback_entry.get("selected_media_ids") or [],
            "selected_reel_draft_name": str(selected_reel_draft_name or fallback_entry.get("selected_reel_draft_name") or "").strip() or None,
            "generation_prompt": str(user_prompt or "").strip() or None,
            "gps_point_count": int(fallback_entry.get("gps_point_count") or 0),
            "source": "map_ai",
            "created_at": str(fallback_entry.get("created_at") or now),
            "updated_at": now,
        }


def build_auto_map_entry(
    album: dict[str, Any],
    existing_entry: dict[str, Any] | None = None,
    *,
    user_prompt: str | None = None,
    selected_media_ids: list[str] | None = None,
    selected_reel_draft_name: str | None = None,
    source: str = "album_auto",
) -> dict[str, Any]:
    gps_media_items = _get_gps_media_items(album)
    corpus = _build_text_corpus(album, extra_texts=[user_prompt])
    place_hint = _match_place_hint(corpus)
    categories = _get_album_categories(album)
    inferred_group = normalize_group_key(place_hint.get("group_key") if place_hint else _choose_group_key(categories, corpus))

    if place_hint:
        latitude = float(place_hint["latitude"])
        longitude = float(place_hint["longitude"])
    elif gps_media_items:
        latitude, longitude = _centroid_for_media(gps_media_items)
    else:
        raise ValueError("This album needs GPS media or a recognizable place hint before a map draft can be generated.")

    summary = _build_summary(album)
    selected_ids = _pick_selected_media_ids(album, preferred_media_ids=selected_media_ids)
    now = _utc_now()

    created_at = now
    if isinstance(existing_entry, dict):
        created_at = str(existing_entry.get("created_at") or now)

    country = place_hint.get("country") if place_hint else None
    state = place_hint.get("state") if place_hint else None
    city = place_hint.get("city") if place_hint else None
    region = place_hint.get("region") if place_hint else _match_region_hint(corpus)
    location_label = place_hint.get("location_label") if place_hint else _match_location_hint(corpus) or city or region or country
    normalized_place_fields = normalize_map_place_fields(
        title=album.get("name") or location_label or "Trip stop",
        country=country,
        state=state,
        city=city,
        region=region,
        location_label=location_label,
        group_key=inferred_group,
    )

    return {
        "album_id": album["id"],
        "album_name": album.get("name") or "Untitled album",
        "title": normalized_place_fields["title"],
        "latitude": latitude,
        "longitude": longitude,
        "country": normalized_place_fields["country"],
        "state": normalized_place_fields["state"],
        "city": normalized_place_fields["city"],
        "region": normalized_place_fields["region"],
        "location_label": normalized_place_fields["location_label"],
        "country_slug": normalized_place_fields["country_slug"],
        "state_slug": normalized_place_fields["state_slug"],
        "city_slug": normalized_place_fields["city_slug"],
        "region_slug": normalized_place_fields["region_slug"],
        "location_slug": normalized_place_fields["location_slug"],
        "title_slug": normalized_place_fields["title_slug"],
        "storage_path": normalized_place_fields["storage_path"],
        "group_key": inferred_group,
        "icon_key": group_to_icon_key(inferred_group),
        "summary": summary,
        "selected_media_ids": selected_ids,
        "selected_reel_draft_name": str(selected_reel_draft_name or "").strip() or None,
        "generation_prompt": str(user_prompt or "").strip() or None,
        "gps_point_count": len(gps_media_items),
        "source": source,
        "created_at": created_at,
        "updated_at": now,
    }


def merge_map_entry(
    album: dict[str, Any],
    *,
    existing_entry: dict[str, Any] | None,
    updates: dict[str, Any],
) -> dict[str, Any]:
    base_entry = deepcopy(existing_entry) if isinstance(existing_entry, dict) else build_auto_map_entry(album)
    merged_entry = {
        **base_entry,
        "album_id": album["id"],
        "album_name": album.get("name") or "Untitled album",
    }

    if "title" in updates:
        merged_entry["title"] = str(updates.get("title") or "").strip() or None
    if "latitude" in updates:
        merged_entry["latitude"] = float(updates["latitude"]) if updates.get("latitude") is not None else None
    if "longitude" in updates:
        merged_entry["longitude"] = float(updates["longitude"]) if updates.get("longitude") is not None else None
    if "country" in updates:
        merged_entry["country"] = str(updates.get("country") or "").strip() or None
    if "state" in updates:
        merged_entry["state"] = str(updates.get("state") or "").strip() or None
    if "city" in updates:
        merged_entry["city"] = str(updates.get("city") or "").strip() or None
    if "region" in updates:
        merged_entry["region"] = str(updates.get("region") or "").strip() or None
    if "location_label" in updates:
        merged_entry["location_label"] = str(updates.get("location_label") or "").strip() or None
    if "group_key" in updates:
        merged_entry["group_key"] = normalize_group_key(updates.get("group_key"))
        merged_entry["icon_key"] = group_to_icon_key(merged_entry["group_key"])
    if "icon_key" in updates and "group_key" not in updates:
        merged_entry["icon_key"] = str(updates.get("icon_key") or "").strip() or None
    if "summary" in updates:
        merged_entry["summary"] = str(updates.get("summary") or "").strip() or None
    if "selected_reel_draft_name" in updates:
        merged_entry["selected_reel_draft_name"] = str(updates.get("selected_reel_draft_name") or "").strip() or None
    if "generation_prompt" in updates:
        merged_entry["generation_prompt"] = str(updates.get("generation_prompt") or "").strip() or None
    if "selected_media_ids" in updates:
        media_ids = updates.get("selected_media_ids") or []
        valid_media_ids = {str(item.get("id") or "") for item in album.get("media_items") or []}
        merged_entry["selected_media_ids"] = [
            media_id
            for media_id in (str(media_id).strip() for media_id in media_ids)
            if media_id and media_id in valid_media_ids
        ][:8]

    merged_entry["gps_point_count"] = len(_get_gps_media_items(album))
    merged_entry["updated_at"] = _utc_now()
    merged_entry["created_at"] = str(base_entry.get("created_at") or merged_entry["updated_at"])

    group_key = normalize_group_key(merged_entry.get("group_key"))
    merged_entry["group_key"] = group_key
    if not str(merged_entry.get("icon_key") or "").strip():
        merged_entry["icon_key"] = group_to_icon_key(group_key)
    normalized_place_fields = normalize_map_place_fields(
        title=merged_entry.get("title"),
        country=merged_entry.get("country"),
        state=merged_entry.get("state"),
        city=merged_entry.get("city"),
        region=merged_entry.get("region"),
        location_label=merged_entry.get("location_label"),
        group_key=group_key,
    )
    merged_entry["title"] = normalized_place_fields["title"]
    merged_entry["country"] = normalized_place_fields["country"]
    merged_entry["state"] = normalized_place_fields["state"]
    merged_entry["city"] = normalized_place_fields["city"]
    merged_entry["region"] = normalized_place_fields["region"]
    merged_entry["location_label"] = normalized_place_fields["location_label"]
    merged_entry["country_slug"] = normalized_place_fields["country_slug"]
    merged_entry["state_slug"] = normalized_place_fields["state_slug"]
    merged_entry["city_slug"] = normalized_place_fields["city_slug"]
    merged_entry["region_slug"] = normalized_place_fields["region_slug"]
    merged_entry["location_slug"] = normalized_place_fields["location_slug"]
    merged_entry["title_slug"] = normalized_place_fields["title_slug"]
    merged_entry["storage_path"] = normalized_place_fields["storage_path"]

    title = str(merged_entry.get("title") or "").strip()
    latitude = merged_entry.get("latitude")
    longitude = merged_entry.get("longitude")
    if not title or not group_key or latitude is None or longitude is None:
        raise ValueError("Map drafts need title, group, latitude, and longitude before saving.")

    return merged_entry


def normalize_group_key(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in MAP_GROUPS:
        return normalized

    for group_key, group_meta in MAP_GROUPS.items():
        if normalized in group_meta["keywords"]:
            return group_key

    return "general"


def group_to_icon_key(group_key: Any) -> str:
    normalized_group = normalize_group_key(group_key)
    return str(MAP_GROUPS[normalized_group]["icon_key"])


def _get_gps_media_items(album: dict[str, Any]) -> list[dict[str, Any]]:
    gps_media_items: list[dict[str, Any]] = []
    for media_item in album.get("media_items") or []:
        gps = media_item.get("gps")
        if not isinstance(gps, dict):
            continue
        latitude = gps.get("latitude")
        longitude = gps.get("longitude")
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            gps_media_items.append(media_item)
    return gps_media_items


def _centroid_for_media(media_items: list[dict[str, Any]]) -> tuple[float, float]:
    latitude_values: list[float] = []
    longitude_values: list[float] = []
    for media_item in media_items:
        gps = media_item.get("gps") or {}
        latitude_values.append(float(gps["latitude"]))
        longitude_values.append(float(gps["longitude"]))
    latitude = round(sum(latitude_values) / len(latitude_values), 6)
    longitude = round(sum(longitude_values) / len(longitude_values), 6)
    return latitude, longitude


def _get_album_categories(album: dict[str, Any]) -> list[str]:
    cached_suggestion = album.get("cached_suggestion")
    if isinstance(cached_suggestion, dict):
        categories = cached_suggestion.get("likely_categories")
        if isinstance(categories, list):
            return [str(category).strip().lower() for category in categories if str(category).strip()]

    description_meta = album.get("description_meta")
    if isinstance(description_meta, dict):
        categories = description_meta.get("likely_categories")
        if isinstance(categories, list):
            return [str(category).strip().lower() for category in categories if str(category).strip()]

    return []


def _choose_group_key(categories: list[str], corpus: str) -> str:
    combined_terms = {category.strip().lower() for category in categories if category.strip()}
    combined_terms.update(word for word in corpus.split() if word)
    for group_key, group_meta in MAP_GROUPS.items():
        if combined_terms.intersection(group_meta["keywords"]):
            return group_key
    return "general"


def _build_text_corpus(album: dict[str, Any], extra_texts: list[str | None] | None = None) -> str:
    parts = [
        str(album.get("name") or ""),
        str(album.get("description") or ""),
    ]
    cached_suggestion = album.get("cached_suggestion")
    if isinstance(cached_suggestion, dict):
        parts.append(str(cached_suggestion.get("album_summary") or ""))
        parts.append(str(cached_suggestion.get("visual_trip_story") or ""))
    for media_item in album.get("media_items") or []:
        parts.append(str(media_item.get("original_filename") or ""))
    for extra_text in extra_texts or []:
        if extra_text:
            parts.append(str(extra_text))
    return " ".join(parts).lower()


def _build_summary(album: dict[str, Any]) -> str | None:
    description = str(album.get("description") or "").strip()
    if description:
        return description

    cached_suggestion = album.get("cached_suggestion")
    if isinstance(cached_suggestion, dict):
        summary = str(cached_suggestion.get("album_summary") or "").strip()
        if summary:
            return summary

    return None


def _match_place_hint(corpus: str) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_score = 0
    for place_hint in PLACE_HINTS:
        score = sum(1 for keyword in place_hint["keywords"] if keyword in corpus)
        if score > best_score:
            best_match = place_hint
            best_score = score
    return best_match if best_score > 0 else None


def _match_region_hint(corpus: str) -> str | None:
    place_hint = _match_place_hint(corpus)
    return str(place_hint.get("region") or "").strip() or None if place_hint else None


def _match_location_hint(corpus: str) -> str | None:
    place_hint = _match_place_hint(corpus)
    return str(place_hint.get("location_label") or "").strip() or None if place_hint else None


def _pick_selected_media_ids(album: dict[str, Any], preferred_media_ids: list[str] | None = None) -> list[str]:
    valid_media_ids = {str(media_item.get("id") or "").strip() for media_item in album.get("media_items") or []}
    picked_media_ids: list[str] = []

    for media_id in preferred_media_ids or []:
        normalized = str(media_id).strip()
        if normalized and normalized in valid_media_ids and normalized not in picked_media_ids:
            picked_media_ids.append(normalized)
        if len(picked_media_ids) >= 8:
            return picked_media_ids

    cached_suggestion = album.get("cached_suggestion")
    if isinstance(cached_suggestion, dict):
        for key in ("cover_candidates", "carousel_candidates", "reel_candidates"):
            for candidate in cached_suggestion.get(key) or []:
                if not isinstance(candidate, dict):
                    continue
                media_id = str(candidate.get("media_id") or "").strip()
                if media_id and media_id in valid_media_ids and media_id not in picked_media_ids:
                    picked_media_ids.append(media_id)
                if len(picked_media_ids) >= 8:
                    return picked_media_ids

    for media_item in album.get("media_items") or []:
        media_id = str(media_item.get("id") or "").strip()
        if media_id and media_id not in picked_media_ids:
            picked_media_ids.append(media_id)
        if len(picked_media_ids) >= 8:
            break

    return picked_media_ids
