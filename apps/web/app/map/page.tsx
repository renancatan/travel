"use client";

import { useEffect, useMemo, useRef, useState } from "react";

declare global {
  interface Window {
    L?: any;
  }
}

type MediaItem = {
  id: string;
  album_id: string;
  original_filename: string;
  content_type: string;
  media_kind: string;
  thumbnail_relative_path: string | null;
};

type RenderedReel = {
  draft_name: string;
  relative_path: string;
  content_type: string;
  file_size_bytes: number;
  rendered_at: string;
  output_width: number;
  output_height: number;
  fps: number;
  estimated_total_duration_seconds: number;
  video_strategy: string;
};

type RenderedVariant = {
  variant_id: string;
  label: string;
  draft_name: string;
  content_type: string;
  file_size_bytes: number;
  rendered_at: string;
  output_width: number;
  output_height: number;
  fps: number;
  estimated_total_duration_seconds: number;
  video_strategy: string;
};

type MapEntry = {
  album_id: string;
  album_name: string;
  title: string;
  latitude: number;
  longitude: number;
  country: string | null;
  country_slug: string | null;
  state: string | null;
  state_slug: string | null;
  city: string | null;
  city_slug: string | null;
  region: string | null;
  region_slug: string | null;
  location_label: string | null;
  location_slug: string | null;
  title_slug: string | null;
  storage_path: string | null;
  group_key: string;
  icon_key: string;
  summary: string | null;
  selected_media_ids: string[];
  selected_reel_draft_name: string | null;
  selected_reel_variant_id: string | null;
  generation_prompt: string | null;
  gps_point_count: number;
  source: string;
  created_at: string;
  updated_at: string;
};

type Album = {
  id: string;
  name: string;
  cached_suggestion?: {
    rendered_variant_renders?: RenderedVariant[] | null;
  } | null;
  map_entry?: MapEntry | null;
  rendered_reel?: RenderedReel | null;
  media_items: MediaItem[];
};

type FilterValue = {
  country: string;
  city: string;
  group: string;
};

type PositionedAlbum = {
  album: Album;
  entry: MapEntry;
  displayLatitude: number;
  displayLongitude: number;
};

type MapDisplayMedia =
  | {
      id: string;
      album_id: string;
      label: string;
      content_type: string;
      media_kind: "video";
      kind: "rendered_reel";
      src: string;
      poster: string | null;
      renderedReel: RenderedReel;
    }
  | {
      id: string;
      album_id: string;
      label: string;
      content_type: string;
      media_kind: string;
      kind: "media_item";
      src: string;
      poster: string | null;
      mediaItem: MediaItem;
    };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const LEAFLET_STYLE_ID = "travel-leaflet-style";
const LEAFLET_SCRIPT_ID = "travel-leaflet-script";
const MAX_MAP_MEDIA = 8;

const MAP_ICON_EMOJI: Record<string, string> = {
  caves: "🕳️",
  beaches: "🏖️",
  bars: "🍻",
  boat: "🚤",
  falls: "💧",
  general: "📍",
};

let leafletAssetsPromise: Promise<void> | null = null;

function getMediaUrl(albumId: string, mediaId: string) {
  return `${API_BASE_URL}/albums/${albumId}/media/${mediaId}/content`;
}

function getThumbnailUrl(albumId: string, mediaId: string) {
  return `${API_BASE_URL}/albums/${albumId}/media/${mediaId}/thumbnail`;
}

function getRenderedReelUrl(albumId: string) {
  return `${API_BASE_URL}/albums/${albumId}/rendered-reel/content`;
}

function getRenderedVariantUrl(albumId: string, variantId: string) {
  return `${API_BASE_URL}/albums/${albumId}/rendered-variants/${variantId}/content`;
}

function getOpenStreetMapUrl(entry: MapEntry | null) {
  if (!entry) {
    return null;
  }
  return `https://www.openstreetmap.org/?mlat=${entry.latitude}&mlon=${entry.longitude}#map=14/${entry.latitude}/${entry.longitude}`;
}

function buildLocationLine(entry: MapEntry) {
  return [entry.country, entry.state, entry.city, entry.region]
    .filter((value): value is string => Boolean(value && value.trim()))
    .join(" / ");
}

function buildSelectedMedia(album: Album | null, entry: MapEntry | null) {
  if (!album || !entry) {
    return [];
  }
  const mediaById = new Map(album.media_items.map((mediaItem) => [mediaItem.id, mediaItem]));
  const originalOrder = new Map(entry.selected_media_ids.map((mediaId, index) => [mediaId, index]));
  const selectedSourceMedia = entry.selected_media_ids
    .map((mediaId) => mediaById.get(mediaId) ?? null)
    .filter((mediaItem): mediaItem is MediaItem => Boolean(mediaItem))
    .sort((left, right) => {
      const leftRank = left.media_kind === "video" ? 0 : 1;
      const rightRank = right.media_kind === "video" ? 0 : 1;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return (originalOrder.get(left.id) ?? 0) - (originalOrder.get(right.id) ?? 0);
    });

  const posterSource =
    selectedSourceMedia.find((mediaItem) => mediaItem.media_kind === "video") ??
    selectedSourceMedia[0] ??
    null;
  const draftFamilyPrefix = entry.selected_reel_draft_name?.replace(/-reel-draft$/, "") ?? null;
  const matchingRenderedVariant =
    album.cached_suggestion?.rendered_variant_renders?.find((renderedVariant) => {
      if (entry.selected_reel_variant_id) {
        return renderedVariant.variant_id === entry.selected_reel_variant_id;
      }
      if (!draftFamilyPrefix) {
        return false;
      }
      return renderedVariant.draft_name.startsWith(`${draftFamilyPrefix}-`);
    }) ?? null;
  const renderedReel =
    album.rendered_reel &&
    entry.selected_reel_draft_name &&
    !entry.selected_reel_variant_id &&
    album.rendered_reel.draft_name === entry.selected_reel_draft_name
      ? {
          id: `rendered-reel:${album.id}:${album.rendered_reel.draft_name}`,
          album_id: album.id,
          label: `${album.rendered_reel.draft_name} (final reel)`,
          content_type: album.rendered_reel.content_type,
          media_kind: "video" as const,
          kind: "rendered_reel" as const,
          src: getRenderedReelUrl(album.id),
          poster: posterSource ? getThumbnailUrl(posterSource.album_id, posterSource.id) : null,
          renderedReel: album.rendered_reel,
        }
      : null;
  const renderedVariant =
    !renderedReel && matchingRenderedVariant
      ? {
          id: `rendered-variant:${album.id}:${matchingRenderedVariant.variant_id}`,
          album_id: album.id,
          label: `${matchingRenderedVariant.label} (chosen reel)`,
          content_type: matchingRenderedVariant.content_type,
          media_kind: "video" as const,
          kind: "rendered_reel" as const,
          src: getRenderedVariantUrl(album.id, matchingRenderedVariant.variant_id),
          poster: posterSource ? getThumbnailUrl(posterSource.album_id, posterSource.id) : null,
          renderedReel: {
            draft_name: matchingRenderedVariant.draft_name,
            relative_path: "",
            content_type: matchingRenderedVariant.content_type,
            file_size_bytes: matchingRenderedVariant.file_size_bytes,
            rendered_at: matchingRenderedVariant.rendered_at,
            output_width: matchingRenderedVariant.output_width,
            output_height: matchingRenderedVariant.output_height,
            fps: matchingRenderedVariant.fps,
            estimated_total_duration_seconds: matchingRenderedVariant.estimated_total_duration_seconds,
            video_strategy: matchingRenderedVariant.video_strategy,
          },
        }
      : null;

  const sourceMedia = selectedSourceMedia
    .map(
      (mediaItem): MapDisplayMedia => ({
        id: mediaItem.id,
        album_id: mediaItem.album_id,
        label: mediaItem.original_filename,
        content_type: mediaItem.content_type,
        media_kind: mediaItem.media_kind,
        kind: "media_item",
        src: getMediaUrl(mediaItem.album_id, mediaItem.id),
        poster: mediaItem.media_kind === "video" ? getThumbnailUrl(mediaItem.album_id, mediaItem.id) : null,
        mediaItem,
      }),
    )
    .slice(0, renderedReel || renderedVariant ? MAX_MAP_MEDIA - 1 : MAX_MAP_MEDIA);

  const linkedReel = renderedReel ?? renderedVariant;
  return linkedReel ? [linkedReel, ...sourceMedia] : sourceMedia;
}

function ensureLeafletStylesheet() {
  if (typeof document === "undefined") {
    return;
  }
  if (document.getElementById(LEAFLET_STYLE_ID)) {
    return;
  }
  const link = document.createElement("link");
  link.id = LEAFLET_STYLE_ID;
  link.rel = "stylesheet";
  link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  document.head.appendChild(link);
}

function ensureLeafletAssets() {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }
  if (window.L) {
    ensureLeafletStylesheet();
    return Promise.resolve();
  }
  if (leafletAssetsPromise) {
    return leafletAssetsPromise;
  }

  leafletAssetsPromise = new Promise<void>((resolve, reject) => {
    ensureLeafletStylesheet();

    const existing = document.getElementById(LEAFLET_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      if (existing.dataset.ready === "true" || window.L) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Could not load Leaflet.")), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = LEAFLET_SCRIPT_ID;
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.async = true;
    script.onload = () => {
      script.dataset.ready = "true";
      resolve();
    };
    script.onerror = () => reject(new Error("Could not load Leaflet."));
    document.body.appendChild(script);
  });

  return leafletAssetsPromise;
}

function createLeafletMarkerIcon(iconKey: string, selected: boolean) {
  const emoji = MAP_ICON_EMOJI[iconKey] ?? MAP_ICON_EMOJI.general;
  return window.L.divIcon({
    className: "travel-map-marker-shell",
    html: `
      <div class="travel-map-marker ${selected ? "is-active" : ""} travel-map-marker--${iconKey}">
        <span>${emoji}</span>
      </div>
    `,
    iconSize: [52, 52],
    iconAnchor: [26, 44],
    popupAnchor: [0, -36],
  });
}

function buildDisplayCoordinates(albums: Album[]) {
  const grouped = new Map<string, Album[]>();

  albums.forEach((album) => {
    const entry = album.map_entry;
    if (!entry) {
      return;
    }
    const key = `${entry.latitude.toFixed(4)}:${entry.longitude.toFixed(4)}`;
    grouped.set(key, [...(grouped.get(key) ?? []), album]);
  });

  const displayCoordinates = new Map<string, { latitude: number; longitude: number }>();

  grouped.forEach((groupAlbums) => {
    const firstEntry = groupAlbums[0]?.map_entry;
    if (!firstEntry) {
      return;
    }

    if (groupAlbums.length === 1) {
      displayCoordinates.set(groupAlbums[0].id, {
        latitude: firstEntry.latitude,
        longitude: firstEntry.longitude,
      });
      return;
    }

    const radiusMeters = Math.min(20 + groupAlbums.length * 6, 54);
    const latitudeRadians = (firstEntry.latitude * Math.PI) / 180;
    const safeCosine = Math.max(Math.cos(latitudeRadians), 0.3);

    groupAlbums.forEach((album, index) => {
      const angle = (-Math.PI / 2) + ((Math.PI * 2 * index) / groupAlbums.length);
      const latitudeOffset = (radiusMeters / 111_320) * Math.sin(angle);
      const longitudeOffset = (radiusMeters / (111_320 * safeCosine)) * Math.cos(angle);

      displayCoordinates.set(album.id, {
        latitude: firstEntry.latitude + latitudeOffset,
        longitude: firstEntry.longitude + longitudeOffset,
      });
    });
  });

  return displayCoordinates;
}

function MapMediaPreview({
  mediaItem,
  active,
}: {
  mediaItem: MapDisplayMedia;
  active: boolean;
}) {
  if (mediaItem.media_kind === "video") {
    return (
      <video
        className={active ? "map-floating-media" : "map-media-strip-thumb"}
        controls={active}
        muted
        playsInline
        poster={mediaItem.poster ?? undefined}
        preload="metadata"
        src={mediaItem.src}
      />
    );
  }

  return (
    <img
      alt={mediaItem.label}
      className={active ? "map-floating-media" : "map-media-strip-thumb"}
      loading="lazy"
      src={mediaItem.src}
    />
  );
}

function MapFloatingCard({
  album,
  entry,
  mediaItems,
  activeMediaId,
  onActiveMediaIdChange,
  onClearSelection,
}: {
  album: Album | null;
  entry: MapEntry | null;
  mediaItems: MapDisplayMedia[];
  activeMediaId: string | null;
  onActiveMediaIdChange: (mediaId: string) => void;
  onClearSelection: () => void;
}) {
  const activeMedia = mediaItems.find((mediaItem) => mediaItem.id === activeMediaId) ?? mediaItems[0] ?? null;

  if (!entry || !album) {
    return (
      <aside className="map-floating-card">
        <div className="map-floating-header">
          <p className="eyebrow">Selected Place</p>
          <h2>Browse the trip map</h2>
          <p>Click a marker or a saved stop to open its media. Click empty map space anytime to clear the current selection.</p>
        </div>

        <div className="selected-album-card">
          <strong>What this view is for</strong>
          <span>The map stays in focus while the selected place opens on top of it, so you do not lose the geography while exploring the media.</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="map-floating-card">
      <div className="map-floating-header">
        <div>
          <p className="eyebrow">Selected Place</p>
          <h2>
            {MAP_ICON_EMOJI[entry.icon_key] ?? MAP_ICON_EMOJI.general} {entry.title}
          </h2>
          <p>{buildLocationLine(entry) || "Place still being normalized."}</p>
        </div>

        <div className="actions">
          <button className="button-secondary button-chip" onClick={onClearSelection} type="button">
            Unselect
          </button>
        </div>
      </div>

      <div className="tag-row">
        <span className="tag">{entry.group_key}</span>
        {entry.city ? <span className="tag">{entry.city}</span> : null}
        {entry.region ? <span className="tag">{entry.region}</span> : null}
        {entry.selected_reel_draft_name ? <span className="tag">reel: {entry.selected_reel_draft_name}</span> : null}
      </div>

      {entry.summary ? <p className="map-stop-summary">{entry.summary}</p> : null}

      {activeMedia ? (
        <div className="map-floating-media-frame">
          <MapMediaPreview active mediaItem={activeMedia} />
        </div>
      ) : (
        <div className="selected-album-card">
          <strong>No linked media</strong>
          <span>This stop currently has map metadata saved, but no selected reel media has been attached yet.</span>
        </div>
      )}

      {mediaItems.length > 1 ? (
        <div className="map-media-strip">
          {mediaItems.map((mediaItem) => (
            <button
              className={`map-media-strip-button ${mediaItem.id === activeMediaId ? "active" : ""}`}
              key={mediaItem.id}
              onClick={() => onActiveMediaIdChange(mediaItem.id)}
              type="button"
            >
              <MapMediaPreview active={false} mediaItem={mediaItem} />
              <span>{mediaItem.label}</span>
            </button>
          ))}
        </div>
      ) : null}

      <div className="map-floating-meta">
        <div className="selected-album-card">
          <strong>Album</strong>
          <span>{album.name}</span>
        </div>
        <div className="selected-album-card">
          <strong>GPS sources</strong>
          <span>{entry.gps_point_count} point(s)</span>
        </div>
      </div>

      <div className="actions">
        {getOpenStreetMapUrl(entry) ? (
          <a
            className="button-secondary button-chip"
            href={getOpenStreetMapUrl(entry) ?? undefined}
            rel="noreferrer"
            target="_blank"
          >
            Open raw GPS in OSM
          </a>
        ) : null}
        <a className="button-secondary button-chip" href="#map-stop-details">
          Jump to expanded stop
        </a>
      </div>
    </aside>
  );
}

function LeafletMapSurface({
  positionedAlbums,
  selectedAlbumId,
  onSelectAlbum,
  onClearSelection,
}: {
  positionedAlbums: PositionedAlbum[];
  selectedAlbumId: string | null;
  onSelectAlbum: (albumId: string) => void;
  onClearSelection: () => void;
}) {
  const mapHostRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const selectedHaloRef = useRef<any>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

  const invalidateMapLayout = () => {
    const map = mapInstanceRef.current;
    if (!map) {
      return;
    }
    map.invalidateSize(false);
  };

  useEffect(() => {
    let cancelled = false;

    void ensureLeafletAssets()
      .then(() => {
        if (!cancelled) {
          setLoadState("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadState("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loadState !== "ready" || !mapHostRef.current || mapInstanceRef.current || !window.L) {
      return;
    }

    const host = mapHostRef.current;
    const map = window.L.map(host, {
      zoomControl: false,
      scrollWheelZoom: true,
      attributionControl: true,
      preferCanvas: true,
    });
    map.setView([0, 0], 2, { animate: false });

    window.L.control.zoom({ position: "bottomright" }).addTo(map);

    const baseLayer = window.L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png", {
      subdomains: "abcd",
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    window.L.tileLayer("https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png", {
      subdomains: "abcd",
      maxZoom: 20,
      pane: "overlayPane",
      opacity: 0.9,
    }).addTo(map);

    map.on("click", () => {
      onClearSelection();
    });

    mapInstanceRef.current = map;
    map.whenReady(() => {
      requestAnimationFrame(() => {
        invalidateMapLayout();
      });
    });
    baseLayer.on("load", () => {
      requestAnimationFrame(() => {
        invalidateMapLayout();
      });
    });
    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => {
            requestAnimationFrame(() => {
              invalidateMapLayout();
            });
          })
        : null;
    resizeObserver?.observe(host);
    requestAnimationFrame(() => {
      invalidateMapLayout();
      window.setTimeout(() => {
        invalidateMapLayout();
      }, 120);
    });

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      if (selectedHaloRef.current) {
        selectedHaloRef.current.remove();
        selectedHaloRef.current = null;
      }
      resizeObserver?.disconnect();
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [loadState, onClearSelection]);

  useEffect(() => {
    if (loadState !== "ready" || !mapInstanceRef.current || !window.L) {
      return;
    }

    const map = mapInstanceRef.current;
    invalidateMapLayout();

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (selectedHaloRef.current) {
      selectedHaloRef.current.remove();
      selectedHaloRef.current = null;
    }

    if (positionedAlbums.length === 0) {
      return;
    }

    const points: Array<[number, number]> = [];

    positionedAlbums.forEach(({ album, entry, displayLatitude, displayLongitude }) => {
      const marker = window.L.marker([displayLatitude, displayLongitude], {
        icon: createLeafletMarkerIcon(entry.icon_key, selectedAlbumId === album.id),
        title: entry.title,
        riseOnHover: true,
        zIndexOffset: selectedAlbumId === album.id ? 500 : 0,
      }).addTo(map);

      marker.bindTooltip(entry.title, {
        direction: "top",
        offset: [0, -28],
        className: "travel-map-tooltip",
      });
      marker.on("click", (event: any) => {
        window.L.DomEvent.stopPropagation(event);
        onSelectAlbum(album.id);
      });

      markersRef.current.push(marker);
      points.push([displayLatitude, displayLongitude]);
    });

    const selectedPoint = positionedAlbums.find(({ album }) => album.id === selectedAlbumId) ?? null;

    if (selectedPoint) {
      selectedHaloRef.current = window.L.circleMarker(
        [selectedPoint.displayLatitude, selectedPoint.displayLongitude],
        {
          radius: 26,
          color: "rgba(20, 108, 106, 0.18)",
          weight: 16,
          fillOpacity: 0,
          interactive: false,
        },
      ).addTo(map);

      map.setView([selectedPoint.displayLatitude, selectedPoint.displayLongitude], 13, {
        animate: true,
      });
      requestAnimationFrame(() => {
        invalidateMapLayout();
      });
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 12, { animate: false });
      requestAnimationFrame(() => {
        invalidateMapLayout();
      });
      return;
    }

    map.fitBounds(window.L.latLngBounds(points).pad(0.2), { animate: false });
    requestAnimationFrame(() => {
      invalidateMapLayout();
    });
  }, [positionedAlbums, selectedAlbumId, onSelectAlbum, loadState]);

  return (
    <>
      <div className={`map-loading-state ${loadState === "loading" ? "visible" : ""}`}>
        Loading the interactive trip map...
      </div>
      {loadState === "error" ? (
        <div className="map-loading-state visible error">
          Leaflet could not load right now. The saved-stop rail still works, but the live map layer is unavailable.
        </div>
      ) : null}
      <div className="map-canvas map-canvas--immersive" ref={mapHostRef} />
    </>
  );
}

export default function MapPage() {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [activeMediaId, setActiveMediaId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterValue>({
    country: "all",
    city: "all",
    group: "all",
  });
  const didInitialSelectRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function loadAlbums() {
      try {
        const response = await fetch(`${API_BASE_URL}/albums`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Could not load map albums (${response.status}).`);
        }
        const data = (await response.json()) as Album[];
        if (cancelled) {
          return;
        }

        const mappedAlbums = data
          .filter((album) => album.map_entry)
          .sort((left, right) => {
            const leftDate = left.map_entry ? new Date(left.map_entry.updated_at).getTime() : 0;
            const rightDate = right.map_entry ? new Date(right.map_entry.updated_at).getTime() : 0;
            return rightDate - leftDate;
          });

        setAlbums(mappedAlbums);
        setLoadError(null);

        if (!didInitialSelectRef.current && mappedAlbums[0]) {
          setSelectedAlbumId(mappedAlbums[0].id);
          didInitialSelectRef.current = true;
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setLoadError(error instanceof Error ? error.message : "Could not load the travel map.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAlbums();
    return () => {
      cancelled = true;
    };
  }, []);

  const filterOptions = useMemo(() => {
    const countries = new Set<string>();
    const groups = new Set<string>();

    albums.forEach((album) => {
      const entry = album.map_entry;
      if (!entry) {
        return;
      }
      if (entry.country) {
        countries.add(entry.country);
      }
      if (entry.group_key) {
        groups.add(entry.group_key);
      }
    });

    const citySource = albums.filter((album) => {
      const entry = album.map_entry;
      if (!entry) {
        return false;
      }
      return filters.country === "all" || entry.country === filters.country;
    });

    const cities = new Set<string>();
    citySource.forEach((album) => {
      const entry = album.map_entry;
      if (entry?.city) {
        cities.add(entry.city);
      }
    });

    return {
      countries: Array.from(countries).sort(),
      cities: Array.from(cities).sort(),
      groups: Array.from(groups).sort(),
    };
  }, [albums, filters.country]);

  const filteredAlbums = useMemo(() => {
    return albums.filter((album) => {
      const entry = album.map_entry;
      if (!entry) {
        return false;
      }
      const countryMatches = filters.country === "all" || entry.country === filters.country;
      const cityMatches = filters.city === "all" || entry.city === filters.city;
      const groupMatches = filters.group === "all" || entry.group_key === filters.group;
      return countryMatches && cityMatches && groupMatches;
    });
  }, [albums, filters]);

  useEffect(() => {
    if (filters.country !== "all" && !filterOptions.cities.includes(filters.city)) {
      setFilters((current) => ({
        ...current,
        city: "all",
      }));
    }
  }, [filterOptions.cities, filters.city, filters.country]);

  useEffect(() => {
    if (filteredAlbums.length === 0) {
      if (selectedAlbumId !== null) {
        setSelectedAlbumId(null);
      }
      return;
    }

    if (selectedAlbumId && !filteredAlbums.some((album) => album.id === selectedAlbumId)) {
      setSelectedAlbumId(filteredAlbums[0].id);
    }
  }, [filteredAlbums, selectedAlbumId]);

  const selectedAlbum = useMemo(
    () => filteredAlbums.find((album) => album.id === selectedAlbumId) ?? null,
    [filteredAlbums, selectedAlbumId],
  );
  const selectedEntry = selectedAlbum?.map_entry ?? null;
  const selectedMedia = useMemo(
    () => buildSelectedMedia(selectedAlbum, selectedEntry),
    [selectedAlbum, selectedEntry],
  );

  useEffect(() => {
    if (selectedMedia.length === 0) {
      setActiveMediaId(null);
      return;
    }

    if (!activeMediaId || !selectedMedia.some((mediaItem) => mediaItem.id === activeMediaId)) {
      setActiveMediaId(selectedMedia[0].id);
    }
  }, [selectedMedia, activeMediaId]);

  const positionedAlbums = useMemo(() => {
    const displayCoordinates = buildDisplayCoordinates(filteredAlbums);
    return filteredAlbums
      .map((album) => {
        const entry = album.map_entry;
        const display = displayCoordinates.get(album.id);
        if (!entry || !display) {
          return null;
        }
        return {
          album,
          entry,
          displayLatitude: display.latitude,
          displayLongitude: display.longitude,
        };
      })
      .filter((item): item is PositionedAlbum => Boolean(item));
  }, [filteredAlbums]);

  const statusMessage = loadError
    ? loadError
    : loading
      ? "Loading saved trip stops..."
      : albums.length === 0
        ? "No saved map stops yet. Generate one from Step 5 first."
        : filteredAlbums.length === 0
          ? "No saved stops match the current filters."
          : "";

  const clearFilters = () => {
    setFilters({
      country: "all",
      city: "all",
      group: "all",
    });
  };

  return (
    <main className="shell map-shell map-shell--immersive">
      <section className="surface map-page-intro">
        <p className="eyebrow">Travel Map</p>
        <h1 className="map-page-title">Navigate the trip inside the map, not below it.</h1>
        <p className="hero-copy">
          This view keeps the geography on screen while you move between stops. Clickable markers, a cleaner basemap,
          richer media on selection, and less stacked-point chaos are the first step toward the old travel-map feel.
        </p>
        <div className="hero-stats map-page-stats">
          <div className="stat">
            <strong>{albums.length}</strong>
            <span>saved stop(s)</span>
          </div>
          <div className="stat">
            <strong>{filteredAlbums.length}</strong>
            <span>visible after filters</span>
          </div>
          <div className="stat">
            <strong>{selectedMedia.length}</strong>
            <span>linked media in selection</span>
          </div>
        </div>
      </section>

      <section className="map-layout">
        <aside className="sidebar map-sidebar">
          <div className="sidebar-header">
            <h2>Saved Stops</h2>
            <span>owner view</span>
          </div>

          {statusMessage ? <div className={`status ${loadError ? "error" : ""}`}>{statusMessage}</div> : null}

          <div className="album-list map-stop-list">
            {filteredAlbums.map((album) => {
              const entry = album.map_entry;
              if (!entry) {
                return null;
              }

              return (
                <button
                  className={`album-button ${selectedAlbumId === album.id ? "active" : ""}`}
                  key={album.id}
                  onClick={() => setSelectedAlbumId(album.id)}
                  type="button"
                >
                  <strong>
                    {MAP_ICON_EMOJI[entry.icon_key] ?? MAP_ICON_EMOJI.general} {entry.title}
                  </strong>
                  <small>{buildLocationLine(entry) || "unnamed stop"}</small>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="surface map-workspace">
          <div className="map-live-header">
            <div>
              <p className="eyebrow">Interactive Map</p>
              <h2>Clickable trip markers</h2>
              <p>Click a stop from the list or a marker on the map. Click empty map space or use `Unselect` to return to browsing mode.</p>
            </div>
            <span>{filteredAlbums.length} visible stop(s)</span>
          </div>

          <div className="map-filter-panel map-filter-panel--top">
            <div className="field">
              <label className="label-row" htmlFor="map-country-filter">
                <span>Country</span>
              </label>
              <select
                className="input"
                id="map-country-filter"
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    country: event.target.value,
                  }))
                }
                value={filters.country}
              >
                <option value="all">All countries</option>
                {filterOptions.countries.map((country) => (
                  <option key={country} value={country}>
                    {country}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="label-row" htmlFor="map-city-filter">
                <span>City</span>
              </label>
              <select
                className="input"
                id="map-city-filter"
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    city: event.target.value,
                  }))
                }
                value={filters.city}
              >
                <option value="all">All cities</option>
                {filterOptions.cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="label-row" htmlFor="map-group-filter">
                <span>Group</span>
              </label>
              <select
                className="input"
                id="map-group-filter"
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    group: event.target.value,
                  }))
                }
                value={filters.group}
              >
                <option value="all">All groups</option>
                {filterOptions.groups.map((group) => (
                  <option key={group} value={group}>
                    {group}
                  </option>
                ))}
              </select>
            </div>

            <div className="actions map-filter-actions">
              <button className="button-secondary" onClick={clearFilters} type="button">
                Reset filters
              </button>
              <button
                className="button-secondary"
                disabled={!selectedAlbumId}
                onClick={() => setSelectedAlbumId(null)}
                type="button"
              >
                Clear selection
              </button>
            </div>
          </div>

          <div className="map-canvas-shell map-canvas-shell--immersive">
            <LeafletMapSurface
              onClearSelection={() => setSelectedAlbumId(null)}
              onSelectAlbum={setSelectedAlbumId}
              positionedAlbums={positionedAlbums}
              selectedAlbumId={selectedAlbumId}
            />
            <MapFloatingCard
              activeMediaId={activeMediaId}
              album={selectedAlbum}
              entry={selectedEntry}
              mediaItems={selectedMedia}
              onActiveMediaIdChange={setActiveMediaId}
              onClearSelection={() => setSelectedAlbumId(null)}
            />
          </div>
        </section>
      </section>

      {selectedAlbum && selectedEntry ? (
        <section className="surface">
          <div className="review-header" id="map-stop-details">
            <div>
              <p className="eyebrow">Expanded Stop</p>
              <h2>
                {MAP_ICON_EMOJI[selectedEntry.icon_key] ?? MAP_ICON_EMOJI.general} {selectedEntry.title}
              </h2>
              <p>{buildLocationLine(selectedEntry) || "Place still being normalized."}</p>
            </div>

            <div className="actions">
              {getOpenStreetMapUrl(selectedEntry) ? (
                <a
                  className="button-secondary"
                  href={getOpenStreetMapUrl(selectedEntry) ?? undefined}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open raw GPS in OSM
                </a>
              ) : null}
            </div>
          </div>

          <div className="tag-row">
            <span className="tag">{selectedEntry.group_key}</span>
            {selectedEntry.city ? <span className="tag">{selectedEntry.city}</span> : null}
            {selectedEntry.region ? <span className="tag">{selectedEntry.region}</span> : null}
            {selectedEntry.selected_reel_draft_name ? <span className="tag">reel: {selectedEntry.selected_reel_draft_name}</span> : null}
          </div>

          {selectedEntry.summary ? <p className="map-stop-summary">{selectedEntry.summary}</p> : null}

          <div className="reel-draft-grid">
            <div className="selected-album-card">
              <strong>Coordinates</strong>
              <span>
                {selectedEntry.latitude.toFixed(6)}, {selectedEntry.longitude.toFixed(6)}
              </span>
            </div>
            <div className="selected-album-card">
              <strong>Location label</strong>
              <span>{selectedEntry.location_label || selectedEntry.city || selectedEntry.title}</span>
            </div>
          </div>

          <div className="media-grid">
            {selectedMedia.length > 0 ? (
              selectedMedia.map((mediaItem) => (
                <article className="media-card" key={mediaItem.id}>
                  <div className="media-visual">
                    {mediaItem.media_kind === "video" ? (
                      <video
                        controls
                        muted
                        playsInline
                        poster={mediaItem.poster ?? undefined}
                        preload="metadata"
                        src={mediaItem.src}
                      />
                    ) : (
                      <img
                        alt={mediaItem.label}
                        loading="lazy"
                        src={mediaItem.src}
                      />
                    )}
                  </div>

                  <div className="media-body">
                    <div className="media-card-header">
                      <strong>{mediaItem.label}</strong>
                    </div>
                    <div className="meta-grid">
                      <div className="meta-card">
                        <strong>Kind</strong>
                        <span>{mediaItem.kind === "rendered_reel" ? "rendered reel" : mediaItem.media_kind}</span>
                      </div>
                      <div className="meta-card">
                        <strong>Content type</strong>
                        <span>{mediaItem.content_type}</span>
                      </div>
                    </div>
                  </div>
                </article>
              ))
            ) : (
              <div className="selected-album-card">
                <strong>No selected media yet</strong>
                <span>This stop was saved without chosen media, so only the place metadata is available here for now.</span>
              </div>
            )}
          </div>
        </section>
      ) : null}
    </main>
  );
}
