from __future__ import annotations

import re
import unicodedata
from typing import Any


COUNTRY_ALIASES: dict[str, str] = {
    "brazil": "Brazil",
    "brasil": "Brazil",
    "federative republic of brazil": "Brazil",
    "philippines": "Philippines",
    "the philippines": "Philippines",
    "republic of the philippines": "Philippines",
    "vietnam": "Vietnam",
    "viet nam": "Vietnam",
    "socialist republic of vietnam": "Vietnam",
    "indonesia": "Indonesia",
    "republic of indonesia": "Indonesia",
}

STATE_ALIASES: dict[str, dict[str, str]] = {
    "brazil": {
        "sao paulo": "Sao Paulo",
        "sao-paulo": "Sao Paulo",
        "sao paulo state": "Sao Paulo",
        "sp": "Sao Paulo",
        "parana": "Parana",
        "pr": "Parana",
    },
    "philippines": {
        "cebu": "Cebu",
        "davao del sur": "Davao del Sur",
    },
}

CITY_ALIASES: dict[str, dict[str, str]] = {
    "brazil": {
        "iporanga": "Iporanga",
        "eldorado": "Eldorado",
        "guaraquecaba": "Guaraquecaba",
        "guaraquecaba pr": "Guaraquecaba",
    },
    "philippines": {
        "cebu": "Cebu",
        "davao": "Davao",
    },
}

REGION_ALIASES: dict[str, str] = {
    "petar": "PETAR",
    "parque estadual turistico do alto ribeira": "PETAR",
    "vale do ribeira": "Vale do Ribeira",
    "paranagua bay": "Paranagua Bay",
    "visayas": "Visayas",
    "mindanao": "Mindanao",
}

LOWERCASE_CONNECTORS = {
    "and",
    "da",
    "das",
    "de",
    "del",
    "do",
    "dos",
    "e",
    "la",
    "of",
    "the",
    "y",
}


def normalize_map_place_fields(
    *,
    title: Any,
    country: Any,
    state: Any,
    city: Any,
    region: Any,
    location_label: Any,
    group_key: Any,
) -> dict[str, Any]:
    normalized_country = _normalize_country(country)
    country_lookup = _lookup_key(normalized_country)
    normalized_state = _normalize_state(state, country_lookup=country_lookup)
    normalized_city = _normalize_city(city, country_lookup=country_lookup)
    normalized_region = _normalize_region(region)
    normalized_location_label = _normalize_location_label(location_label)
    normalized_title = _normalize_title(title)
    normalized_group_key = str(group_key or "").strip().lower() or "general"

    if not normalized_location_label:
        normalized_location_label = normalized_city or normalized_region or normalized_state or normalized_country

    title_slug = slugify(normalized_title or normalized_location_label or "trip-stop")
    country_slug = slugify(normalized_country) if normalized_country else None
    state_slug = slugify(normalized_state) if normalized_state else None
    city_slug = slugify(normalized_city) if normalized_city else None
    region_slug = slugify(normalized_region) if normalized_region else None
    location_slug = slugify(normalized_location_label) if normalized_location_label else None
    storage_path = build_map_storage_path(
        country_slug=country_slug,
        state_slug=state_slug,
        city_slug=city_slug,
        region_slug=region_slug,
        group_key=normalized_group_key,
        title_slug=title_slug,
    )

    return {
        "title": normalized_title or normalized_location_label or "Trip stop",
        "country": normalized_country,
        "state": normalized_state,
        "city": normalized_city,
        "region": normalized_region,
        "location_label": normalized_location_label,
        "country_slug": country_slug,
        "state_slug": state_slug,
        "city_slug": city_slug,
        "region_slug": region_slug,
        "location_slug": location_slug,
        "title_slug": title_slug,
        "storage_path": storage_path,
    }


def build_map_storage_path(
    *,
    country_slug: str | None,
    state_slug: str | None,
    city_slug: str | None,
    region_slug: str | None,
    group_key: str,
    title_slug: str,
) -> str:
    if not country_slug:
        return "/".join(
            segment
            for segment in ("travel", "uncategorized", group_key or "general", title_slug or "trip-stop")
            if segment
        )

    segments = ["travel", "countries", country_slug]
    if state_slug:
        segments.append(state_slug)
    if city_slug:
        segments.append(city_slug)
    elif region_slug:
        segments.append(region_slug)
    if region_slug and region_slug not in segments:
        segments.append(region_slug)
    segments.append(group_key or "general")
    segments.append(title_slug or "trip-stop")
    return "/".join(segment for segment in segments if segment)


def slugify(value: Any) -> str:
    normalized = _ascii_fold(_collapse_spaces(str(value or "").strip()).lower())
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized[:120] or "item"


def _normalize_country(value: Any) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    alias = COUNTRY_ALIASES.get(_lookup_key(cleaned))
    return _ascii_display(alias or _smart_title_case(cleaned))


def _normalize_state(value: Any, *, country_lookup: str) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    alias_map = STATE_ALIASES.get(country_lookup, {})
    alias = alias_map.get(_lookup_key(cleaned))
    return _ascii_display(alias or _smart_title_case(cleaned))


def _normalize_city(value: Any, *, country_lookup: str) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    alias_map = CITY_ALIASES.get(country_lookup, {})
    alias = alias_map.get(_lookup_key(cleaned))
    return _ascii_display(alias or _smart_title_case(cleaned))


def _normalize_region(value: Any) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    alias = REGION_ALIASES.get(_lookup_key(cleaned))
    return _ascii_display(alias or _smart_title_case(cleaned))


def _normalize_location_label(value: Any) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    region_alias = REGION_ALIASES.get(_lookup_key(cleaned))
    return _ascii_display(region_alias or _smart_title_case(cleaned))


def _normalize_title(value: Any) -> str | None:
    cleaned = _clean_display_value(value)
    if not cleaned:
        return None
    return _ascii_display(_smart_title_case(cleaned))


def _clean_display_value(value: Any) -> str:
    return _collapse_spaces(str(value or "").strip())


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _lookup_key(value: str) -> str:
    return _ascii_fold(_collapse_spaces(value).lower()).replace("-", " ")


def _ascii_fold(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _ascii_display(value: str) -> str:
    return _collapse_spaces(_ascii_fold(value))


def _smart_title_case(value: str) -> str:
    value = _collapse_spaces(value)
    if not value:
        return ""

    if _lookup_key(value) in REGION_ALIASES:
        return REGION_ALIASES[_lookup_key(value)]

    parts = re.split(r"(\s+|-|/)", value.lower())
    titled_parts: list[str] = []
    is_first_word = True

    for part in parts:
        if not part:
            continue
        if re.fullmatch(r"\s+|-|/", part):
            titled_parts.append(part)
            continue

        if not is_first_word and part in LOWERCASE_CONNECTORS:
            titled_parts.append(part)
        elif len(part) <= 4 and part.isalpha() and part.upper() in {"PETAR", "USA", "UAE"}:
            titled_parts.append(part.upper())
        else:
            titled_parts.append(part.capitalize())
        is_first_word = False

    return "".join(titled_parts)
