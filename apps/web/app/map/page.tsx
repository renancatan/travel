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
  generation_prompt: string | null;
  gps_point_count: number;
  source: string;
  created_at: string;
  updated_at: string;
};

type Album = {
  id: string;
  name: string;
  map_entry?: MapEntry | null;
  media_items: MediaItem[];
};

type FilterValue = {
  country: string;
  city: string;
  group: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const LEAFLET_STYLE_ID = "travel-leaflet-style";
const LEAFLET_SCRIPT_ID = "travel-leaflet-script";

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
  return entry.selected_media_ids
    .map((mediaId) => mediaById.get(mediaId) ?? null)
    .filter((mediaItem): mediaItem is MediaItem => Boolean(mediaItem))
    .slice(0, 6);
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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

function buildPopupMarkup(entry: MapEntry) {
  const locationLine = buildLocationLine(entry) || entry.group_key;
  const summary =
    entry.summary && entry.summary.trim()
      ? `${entry.summary.trim().slice(0, 150)}${entry.summary.trim().length > 150 ? "..." : ""}`
      : "Open this stop to see the selected travel media.";
  return `
    <div class="travel-map-popup">
      <strong>${escapeHtml(entry.title)}</strong>
      <span>${escapeHtml(locationLine)}</span>
      <p>${escapeHtml(summary)}</p>
    </div>
  `;
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
    iconSize: [48, 48],
    iconAnchor: [24, 42],
    popupAnchor: [0, -34],
  });
}

function LeafletMapSurface({
  albums,
  selectedAlbumId,
  onSelectAlbum,
}: {
  albums: Album[];
  selectedAlbumId: string | null;
  onSelectAlbum: (albumId: string) => void;
}) {
  const mapHostRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

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

    const map = window.L.map(mapHostRef.current, {
      zoomControl: false,
      scrollWheelZoom: true,
      attributionControl: true,
    });

    window.L.control.zoom({ position: "bottomright" }).addTo(map);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [loadState]);

  useEffect(() => {
    if (loadState !== "ready" || !mapInstanceRef.current || !window.L) {
      return;
    }

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (albums.length === 0) {
      return;
    }

    const map = mapInstanceRef.current;
    const points: Array<[number, number]> = [];

    albums.forEach((album) => {
      const entry = album.map_entry;
      if (!entry) {
        return;
      }

      const marker = window.L.marker([entry.latitude, entry.longitude], {
        icon: createLeafletMarkerIcon(entry.icon_key, selectedAlbumId === album.id),
        title: entry.title,
        riseOnHover: true,
      }).addTo(map);

      marker.bindTooltip(entry.title, {
        direction: "top",
        offset: [0, -26],
        className: "travel-map-tooltip",
      });
      marker.bindPopup(buildPopupMarkup(entry));
      marker.on("click", () => onSelectAlbum(album.id));

      if (selectedAlbumId === album.id) {
        marker.openPopup();
      }

      markersRef.current.push(marker);
      points.push([entry.latitude, entry.longitude]);
    });

    const selectedEntry = albums.find((album) => album.id === selectedAlbumId)?.map_entry ?? null;
    if (selectedEntry) {
      map.setView([selectedEntry.latitude, selectedEntry.longitude], 12, { animate: true });
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 12, { animate: false });
      return;
    }

    map.fitBounds(window.L.latLngBounds(points).pad(0.22), { animate: false });
  }, [albums, selectedAlbumId, onSelectAlbum, loadState]);

  return (
    <div className="map-canvas-panel">
      <div className="map-live-header">
        <div>
          <p className="eyebrow">Interactive Map</p>
          <h3>Clickable trip markers</h3>
        </div>
        <span>{albums.length} visible stop(s)</span>
      </div>
      <div className="map-canvas-shell">
        <div className={`map-loading-state ${loadState === "loading" ? "visible" : ""}`}>
          Loading the interactive map layer...
        </div>
        {loadState === "error" ? (
          <div className="map-loading-state visible error">
            Leaflet could not load right now. The stop list and media explorer below still work.
          </div>
        ) : null}
        <div className="map-canvas" ref={mapHostRef} />
      </div>
    </div>
  );
}

export default function MapPage() {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterValue>({
    country: "all",
    city: "all",
    group: "all",
  });

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
        const mappedAlbums = data.filter((album) => album.map_entry);
        setAlbums(mappedAlbums);
        setSelectedAlbumId((current) => current ?? mappedAlbums[0]?.id ?? null);
        setLoadError(null);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setLoadError(error instanceof Error ? error.message : "Could not load the map preview.");
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
    const cities = new Set<string>();
    const groups = new Set<string>();

    albums.forEach((album) => {
      const entry = album.map_entry;
      if (!entry) {
        return;
      }
      if (entry.country) {
        countries.add(entry.country);
      }
      if (entry.city) {
        cities.add(entry.city);
      }
      if (entry.group_key) {
        groups.add(entry.group_key);
      }
    });

    return {
      countries: Array.from(countries).sort(),
      cities: Array.from(cities).sort(),
      groups: Array.from(groups).sort(),
    };
  }, [albums]);

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
    if (filteredAlbums.length === 0) {
      setSelectedAlbumId(null);
      return;
    }
    if (!selectedAlbumId || !filteredAlbums.some((album) => album.id === selectedAlbumId)) {
      setSelectedAlbumId(filteredAlbums[0].id);
    }
  }, [filteredAlbums, selectedAlbumId]);

  const selectedAlbum = useMemo(
    () => filteredAlbums.find((album) => album.id === selectedAlbumId) ?? filteredAlbums[0] ?? null,
    [filteredAlbums, selectedAlbumId],
  );
  const selectedEntry = selectedAlbum?.map_entry ?? null;
  const selectedMedia = useMemo(
    () => buildSelectedMedia(selectedAlbum, selectedEntry),
    [selectedAlbum, selectedEntry],
  );
  const spotlightMedia = selectedMedia[0] ?? null;

  const statusMessage = loadError
    ? loadError
    : loading
      ? "Loading saved map stops..."
      : albums.length === 0
        ? "No saved map stops yet. Generate one from Step 5 first."
        : filteredAlbums.length === 0
          ? "No stops match the current owner filters. Try a broader country, city, or group."
          : "";

  return (
    <main className="shell map-shell">
      <section className="hero">
        <div className="hero-panel">
          <p className="eyebrow">Travel Map</p>
          <h1 className="hero-title">Map stops that open into actual travel stories.</h1>
          <p className="hero-copy">
            This is no longer just a raw GPS checkpoint. The map is becoming the owner-side explorer for chosen reels,
            selected images, trip summaries, and place grouping so you can quickly jump back into the moments that
            mattered.
          </p>
          <div className="hero-stats">
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
              <span>media item(s) in selected stop</span>
            </div>
          </div>
        </div>

        <div className="hero-side">
          <div className="hero-note hero-panel">
            <h2>Private travel memory map</h2>
            <p>
              Filters here are for the owner to jump between their own countries, cities, groups, and later ratings.
              This is not meant to become a public review clone.
            </p>
          </div>
          <div className="hero-note hero-panel">
            <h2>Legacy direction kept</h2>
            <p>
              The target is still the old travel app feel: custom icons on the map, clickable places, and rich
              media-heavy stop expansion rather than a plain pin-only map.
            </p>
          </div>
        </div>
      </section>

      <section className="grid">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Saved Stops</h2>
            <span>owner view</span>
          </div>

          {statusMessage ? <div className={`status ${loadError ? "error" : ""}`}>{statusMessage}</div> : null}

          <div className="map-filter-panel">
            <div className="field">
              <label className="label-row" htmlFor="country-filter">
                <span>Country</span>
              </label>
              <select
                className="input"
                id="country-filter"
                onChange={(event) => setFilters((current) => ({ ...current, country: event.target.value }))}
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
              <label className="label-row" htmlFor="city-filter">
                <span>City</span>
              </label>
              <select
                className="input"
                id="city-filter"
                onChange={(event) => setFilters((current) => ({ ...current, city: event.target.value }))}
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
              <label className="label-row" htmlFor="group-filter">
                <span>Group</span>
              </label>
              <select
                className="input"
                id="group-filter"
                onChange={(event) => setFilters((current) => ({ ...current, group: event.target.value }))}
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
          </div>

          <div className="album-list">
            {filteredAlbums.map((album) => {
              const entry = album.map_entry;
              if (!entry) {
                return null;
              }
              return (
                <button
                  className={`album-button ${selectedAlbum?.id === album.id ? "active" : ""}`}
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

        <section className="surface">
          {selectedAlbum && selectedEntry ? (
            <div className="map-preview-stack">
              <section className="map-stage">
                <LeafletMapSurface
                  albums={filteredAlbums}
                  onSelectAlbum={setSelectedAlbumId}
                  selectedAlbumId={selectedAlbum.id}
                />

                <article className="map-spotlight-card">
                  <div className="map-spotlight-copy">
                    <p className="eyebrow">Selected Stop</p>
                    <h2>
                      {MAP_ICON_EMOJI[selectedEntry.icon_key] ?? MAP_ICON_EMOJI.general} {selectedEntry.title}
                    </h2>
                    <p>{buildLocationLine(selectedEntry) || "Place still being normalized."}</p>
                  </div>

                  <div className="tag-row">
                    <span className="tag">{selectedEntry.group_key}</span>
                    {selectedEntry.city ? <span className="tag">{selectedEntry.city}</span> : null}
                    {selectedEntry.region ? <span className="tag">{selectedEntry.region}</span> : null}
                    {selectedEntry.selected_reel_draft_name ? (
                      <span className="tag">reel: {selectedEntry.selected_reel_draft_name}</span>
                    ) : null}
                  </div>

                  {selectedEntry.summary ? <p className="map-stop-summary">{selectedEntry.summary}</p> : null}

                  {spotlightMedia ? (
                    <div className="map-spotlight-media-frame">
                      {spotlightMedia.media_kind === "video" ? (
                        <video
                          className="map-spotlight-media"
                          controls
                          muted
                          playsInline
                          poster={getThumbnailUrl(spotlightMedia.album_id, spotlightMedia.id)}
                          preload="metadata"
                          src={getMediaUrl(spotlightMedia.album_id, spotlightMedia.id)}
                        />
                      ) : (
                        <img
                          alt={spotlightMedia.original_filename}
                          className="map-spotlight-media"
                          loading="lazy"
                          src={getMediaUrl(spotlightMedia.album_id, spotlightMedia.id)}
                        />
                      )}
                    </div>
                  ) : null}

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
                    <a className="button-secondary" href="#map-stop-details">
                      Jump to expanded stop
                    </a>
                  </div>
                </article>
              </section>

              <div className="map-stop-card" id="map-stop-details">
                <div className="map-stop-header">
                  <div>
                    <p className="eyebrow">Expanded Stop</p>
                    <h2>
                      {MAP_ICON_EMOJI[selectedEntry.icon_key] ?? MAP_ICON_EMOJI.general} {selectedEntry.title}
                    </h2>
                    <p>{buildLocationLine(selectedEntry) || "Place still being normalized."}</p>
                  </div>
                </div>

                <div className="reel-draft-grid">
                  <div className="selected-album-card">
                    <strong>Canonical place path</strong>
                    <code>{selectedEntry.storage_path ?? "pending"}</code>
                  </div>
                  <div className="selected-album-card">
                    <strong>Coordinates</strong>
                    <span>
                      {selectedEntry.latitude.toFixed(6)}, {selectedEntry.longitude.toFixed(6)}
                    </span>
                  </div>
                </div>

                <div className="map-media-grid">
                  {selectedMedia.length > 0 ? (
                    selectedMedia.map((mediaItem) => (
                      <article className="map-media-card" key={mediaItem.id}>
                        {mediaItem.media_kind === "video" ? (
                          <video
                            className="map-media-thumb"
                            controls
                            muted
                            playsInline
                            poster={getThumbnailUrl(mediaItem.album_id, mediaItem.id)}
                            preload="metadata"
                            src={getMediaUrl(mediaItem.album_id, mediaItem.id)}
                          />
                        ) : (
                          <img
                            alt={mediaItem.original_filename}
                            className="map-media-thumb"
                            loading="lazy"
                            src={getMediaUrl(mediaItem.album_id, mediaItem.id)}
                          />
                        )}
                        <div className="map-media-copy">
                          <strong>{mediaItem.original_filename}</strong>
                          <span>
                            {mediaItem.media_kind} • {mediaItem.content_type}
                          </span>
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="selected-album-card">
                      <strong>No selected media yet</strong>
                      <span>This stop was saved without chosen media, so only the text-side map data is available for now.</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty">
              <h2>No map stop selected</h2>
              <p>Generate and save a Step 5 map draft from the main workflow, then this public map preview will pick it up.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
