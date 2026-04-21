from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


ICON_CATEGORY_RULES: list[tuple[set[str], str]] = [
    ({"cave", "caves"}, "caves"),
    ({"beach", "beaches", "island", "surf", "coast"}, "beaches"),
    ({"bar", "bars", "pub", "nightlife", "beer", "cocktail"}, "bars"),
    ({"boat", "boats", "sailing", "island-hopping"}, "boat"),
    ({"falls", "waterfall", "waterfalls"}, "falls"),
]

COUNTRY_HINTS = {
    "brazil": "Brazil",
    "brasil": "Brazil",
    "philippines": "Philippines",
}

REGION_HINTS = {
    "petar": "PETAR",
    "iporanga": "PETAR",
    "paranagua": "Paranagua Bay",
    "guaraquecaba": "Paranagua Bay",
    "mindanao": "Mindanao",
    "visayas": "Visayas",
}

LOCATION_HINTS = {
    "iporanga": "Iporanga",
    "petar": "PETAR",
    "eldorado": "Eldorado",
    "guaraquecaba": "Guaraquecaba",
    "cebu": "Cebu",
    "davao": "Davao",
}


def build_auto_map_entry(album: dict[str, Any], existing_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    gps_media_items = _get_gps_media_items(album)
    if not gps_media_items:
        raise ValueError("This album does not have GPS-tagged media yet.")

    latitude, longitude = _centroid_for_media(gps_media_items)
    categories = _get_album_categories(album)
    icon_key = _choose_icon_key(categories)
    corpus = _build_text_corpus(album)
    country = _match_hint(corpus, COUNTRY_HINTS)
    region = _match_hint(corpus, REGION_HINTS)
    location_label = _match_hint(corpus, LOCATION_HINTS) or region or country or album.get("name") or "Trip stop"
    summary = _build_summary(album)
    selected_media_ids = _pick_selected_media_ids(album, gps_media_items)
    now = _utc_now()

    created_at = now
    if isinstance(existing_entry, dict):
        created_at = str(existing_entry.get("created_at") or now)

    return {
        "album_id": album["id"],
        "album_name": album.get("name") or "Untitled album",
        "title": str(album.get("name") or location_label or "Trip stop").strip(),
        "latitude": latitude,
        "longitude": longitude,
        "country": country,
        "region": region,
        "location_label": str(location_label).strip() or None,
        "icon_key": icon_key,
        "summary": summary,
        "selected_media_ids": selected_media_ids,
        "gps_point_count": len(gps_media_items),
        "source": "album_auto",
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
    if "region" in updates:
        merged_entry["region"] = str(updates.get("region") or "").strip() or None
    if "location_label" in updates:
        merged_entry["location_label"] = str(updates.get("location_label") or "").strip() or None
    if "icon_key" in updates:
        merged_entry["icon_key"] = str(updates.get("icon_key") or "").strip() or None
    if "summary" in updates:
        merged_entry["summary"] = str(updates.get("summary") or "").strip() or None
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

    title = str(merged_entry.get("title") or "").strip()
    icon_key = str(merged_entry.get("icon_key") or "").strip()
    latitude = merged_entry.get("latitude")
    longitude = merged_entry.get("longitude")
    if not title or not icon_key or latitude is None or longitude is None:
        raise ValueError("Map drafts need title, icon, latitude, and longitude before saving.")

    return merged_entry


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


def _choose_icon_key(categories: list[str]) -> str:
    category_set = {category.strip().lower() for category in categories if category.strip()}
    for keywords, icon_key in ICON_CATEGORY_RULES:
        if category_set.intersection(keywords):
            return icon_key
    return "general"


def _build_text_corpus(album: dict[str, Any]) -> str:
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


def _match_hint(corpus: str, hints: dict[str, str]) -> str | None:
    for keyword, label in hints.items():
        if keyword in corpus:
            return label
    return None


def _pick_selected_media_ids(album: dict[str, Any], gps_media_items: list[dict[str, Any]]) -> list[str]:
    gps_media_ids = {str(media_item.get("id") or "") for media_item in gps_media_items}
    picked_media_ids: list[str] = []

    cached_suggestion = album.get("cached_suggestion")
    if isinstance(cached_suggestion, dict):
        for key in ("cover_candidates", "carousel_candidates", "reel_candidates"):
            for candidate in cached_suggestion.get(key) or []:
                if not isinstance(candidate, dict):
                    continue
                media_id = str(candidate.get("media_id") or "").strip()
                if media_id and media_id in gps_media_ids and media_id not in picked_media_ids:
                    picked_media_ids.append(media_id)
                if len(picked_media_ids) >= 4:
                    return picked_media_ids

    for media_item in gps_media_items:
        media_id = str(media_item.get("id") or "").strip()
        if media_id and media_id not in picked_media_ids:
            picked_media_ids.append(media_id)
        if len(picked_media_ids) >= 4:
            break

    return picked_media_ids
