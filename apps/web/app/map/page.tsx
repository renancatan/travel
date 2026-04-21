"use client";

import { useEffect, useMemo, useState } from "react";

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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const MAP_ICON_EMOJI: Record<string, string> = {
  caves: "🕳️",
  beaches: "🏖️",
  bars: "🍻",
  boat: "🚤",
  falls: "💧",
  general: "📍",
};

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

export default function MapPage() {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [status, setStatus] = useState<{ tone: "idle" | "error"; message: string }>({
    tone: "idle",
    message: "Loading saved map stops...",
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
        setStatus({
          tone: "idle",
          message: mappedAlbums.length > 0 ? "" : "No saved map stops yet. Generate one from Step 5 first.",
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setStatus({
          tone: "error",
          message: error instanceof Error ? error.message : "Could not load the map preview.",
        });
      }
    }

    void loadAlbums();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedAlbum = useMemo(
    () => albums.find((album) => album.id === selectedAlbumId) ?? albums[0] ?? null,
    [albums, selectedAlbumId],
  );
  const selectedEntry = selectedAlbum?.map_entry ?? null;
  const selectedMedia = useMemo(() => {
    if (!selectedAlbum || !selectedEntry) {
      return [];
    }
    const mediaById = new Map(selectedAlbum.media_items.map((mediaItem) => [mediaItem.id, mediaItem]));
    return selectedEntry.selected_media_ids
      .map((mediaId) => mediaById.get(mediaId) ?? null)
      .filter((mediaItem): mediaItem is MediaItem => Boolean(mediaItem))
      .slice(0, 6);
  }, [selectedAlbum, selectedEntry]);

  return (
    <main className="shell map-shell">
      <section className="hero">
        <div className="hero-panel">
          <p className="eyebrow">Travel Map</p>
          <h1 className="hero-title">Map stops that actually show the trip.</h1>
          <p className="hero-copy">
            This page is the first public-style map surface for the project. Instead of only a raw GPS pin, each stop
            now carries the travel group, summary, chosen reel context, and selected media.
          </p>
          <div className="hero-stats">
            <div className="stat">
              <strong>{albums.length}</strong>
              <span>saved map stop(s)</span>
            </div>
            <div className="stat">
              <strong>{selectedMedia.length}</strong>
              <span>media item(s) in selected stop</span>
            </div>
            <div className="stat">
              <strong>{selectedEntry?.gps_point_count ?? 0}</strong>
              <span>GPS point(s) behind current stop</span>
            </div>
          </div>
        </div>

        <div className="hero-side">
          <div className="hero-note hero-panel">
            <h2>What this replaces</h2>
            <p>
              OpenStreetMap stays useful as a coordinate sanity check, but this page is where the richer travel stop
              experience starts: icon, chosen media, summary, and place hierarchy all together.
            </p>
          </div>
          <div className="hero-note hero-panel">
            <h2>Next map layer</h2>
            <p>
              The next iteration can place these richer stop cards on top of our own interactive map canvas instead of
              only linking out to OSM.
            </p>
          </div>
        </div>
      </section>

      <section className="grid">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Saved Stops</h2>
            <span>public preview</span>
          </div>
          {status.message ? <div className={`status ${status.tone === "error" ? "error" : ""}`}>{status.message}</div> : null}
          <div className="album-list">
            {albums.map((album) => {
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
              <div className="map-stop-card">
                <div className="map-stop-header">
                  <div>
                    <p className="eyebrow">Map Stop</p>
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
                  {selectedEntry.selected_reel_draft_name ? (
                    <span className="tag">reel: {selectedEntry.selected_reel_draft_name}</span>
                  ) : null}
                </div>

                {selectedEntry.summary ? <p className="map-stop-summary">{selectedEntry.summary}</p> : null}

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
