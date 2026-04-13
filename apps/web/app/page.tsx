"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useState, useTransition } from "react";

type MediaItem = {
  id: string;
  album_id: string;
  original_filename: string;
  stored_filename: string;
  stored_path: string;
  relative_path: string;
  content_type: string;
  media_kind: string;
  file_size_bytes: number;
  sha256: string;
  file_extension: string;
  captured_at: string | null;
  source_device: string | null;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  frame_rate: number | null;
  video_codec: string | null;
  gps: Record<string, unknown> | null;
  metadata_source: string | null;
  thumbnail_relative_path: string | null;
  thumbnail_content_type: string | null;
  media_score: number | null;
  media_score_label: string | null;
  detected_at: string;
  created_at: string;
};

type Album = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  media_items: MediaItem[];
};

type MediaInsight = {
  media_id: string | null;
  scene_guess: string;
  why_it_matters: string;
  use_case: string;
};

type AlbumSuggestion = {
  album_summary: string;
  visual_trip_story: string;
  likely_categories: string[];
  caption_ideas: string[];
  cover_image_media_id: string | null;
  media_insights: MediaInsight[];
  analysis_mode: string;
  route: Record<string, unknown> | null;
};

type AutoDescriptionResponse = {
  album: Album;
  description: string;
  likely_categories: string[];
  analysis_mode: string;
  route: Record<string, unknown> | null;
};

type DescriptionMeta = {
  likelyCategories: string[];
  analysisMode: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const NEW_ALBUM_DRAFT_KEY = "travel-project:new-album-draft";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function formatFrameRate(frameRate: number): string {
  if (frameRate >= 10) {
    return `${frameRate.toFixed(1)} fps`;
  }
  return `${frameRate.toFixed(2)} fps`;
}

function formatMediaScore(score: number, label: string | null): string {
  return `${score.toFixed(0)}/100${label ? ` - ${label}` : ""}`;
}

function formatGps(gps: Record<string, unknown>): string {
  const latitude = typeof gps.latitude === "number" ? gps.latitude : null;
  const longitude = typeof gps.longitude === "number" ? gps.longitude : null;
  const altitude = typeof gps.altitude_meters === "number" ? gps.altitude_meters : null;

  if (latitude === null || longitude === null) {
    return "Incomplete";
  }

  const base = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
  return altitude === null ? base : `${base} - ${altitude.toFixed(0)} m`;
}

function normalizeAlbumName(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function upsertAlbum(albums: Album[], updatedAlbum: Album): Album[] {
  const existingIndex = albums.findIndex((album) => album.id === updatedAlbum.id);
  if (existingIndex === -1) {
    return [updatedAlbum, ...albums];
  }

  return albums.map((album) => (album.id === updatedAlbum.id ? updatedAlbum : album));
}

function removeAlbum(albums: Album[], albumId: string): Album[] {
  return albums.filter((album) => album.id !== albumId);
}

export default function Page() {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [albumMode, setAlbumMode] = useState<"new" | "existing">("new");
  const [newAlbumId, setNewAlbumId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [descriptionMode, setDescriptionMode] = useState<"automatic" | "manual">("automatic");
  const [manualDescription, setManualDescription] = useState("");
  const [descriptionMetaByAlbum, setDescriptionMetaByAlbum] = useState<Record<string, DescriptionMeta>>({});
  const [suggestionsByAlbum, setSuggestionsByAlbum] = useState<Record<string, AlbumSuggestion>>({});
  const [status, setStatus] = useState<{ tone: "idle" | "ok" | "error"; message: string }>({
    tone: "idle",
    message: "Start by choosing a target album. Upload, description, and AI review will follow in order.",
  });
  const [albumsStatus, setAlbumsStatus] = useState<{ tone: "idle" | "ok" | "error"; message: string }>({
    tone: "idle",
    message: "",
  });
  const [descriptionStatus, setDescriptionStatus] = useState<{ tone: "idle" | "ok" | "error"; message: string }>({
    tone: "idle",
    message: "Upload media first. Then choose Automatic AI or Manual for the saved album description.",
  });
  const [suggestionStatus, setSuggestionStatus] = useState<{ tone: "idle" | "ok" | "error"; message: string }>({
    tone: "idle",
    message: "AI review will appear after media upload and description setup.",
  });
  const [isCreatingAlbum, setIsCreatingAlbum] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false);
  const [isSavingDescription, setIsSavingDescription] = useState(false);
  const [deletingAlbumId, setDeletingAlbumId] = useState<string | null>(null);
  const [deletingMediaId, setDeletingMediaId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const sidebarAlbum = albums.find((album) => album.id === selectedAlbumId) ?? null;
  const workflowAlbum =
    albumMode === "new" ? albums.find((album) => album.id === newAlbumId) ?? null : sidebarAlbum;
  const activeSuggestions = workflowAlbum ? suggestionsByAlbum[workflowAlbum.id] ?? null : null;
  const activeDescriptionMeta = workflowAlbum ? descriptionMetaByAlbum[workflowAlbum.id] ?? null : null;
  const uploadTargetAlbum = workflowAlbum;
  const showUploadStep = Boolean(uploadTargetAlbum);
  const showPostUploadSteps = Boolean(workflowAlbum && workflowAlbum.media_items.length > 0);
  const duplicateAlbum =
    albumMode === "new" && !newAlbumId && name.trim()
      ? albums.find((album) => normalizeAlbumName(album.name) === normalizeAlbumName(name))
      : null;

  function clearUploadSelection() {
    const fileInput = document.getElementById("upload-input") as HTMLInputElement | null;
    setSelectedFiles([]);
    setIsDragging(false);
    if (fileInput) {
      fileInput.value = "";
    }
  }

  function resetNewAlbumFlow() {
    clearUploadSelection();
    setNewAlbumId(null);
    setName("");
    setDescriptionMode("automatic");
    setManualDescription("");
    window.localStorage.removeItem(NEW_ALBUM_DRAFT_KEY);
    setStatus({
      tone: "idle",
      message: "Create the new album first. Upload will appear right after that.",
    });
  }

  async function loadAlbums(preserveSelected = true) {
    try {
      const response = await fetch(`${API_BASE_URL}/albums`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Failed to load albums (${response.status})`);
      }

      const data = (await response.json()) as Album[];
      setAlbums(data);
      setAlbumsStatus({ tone: "idle", message: "" });

      if (!preserveSelected) {
        setSelectedAlbumId(null);
        return true;
      }

      if (selectedAlbumId && !data.some((album) => album.id === selectedAlbumId)) {
        setSelectedAlbumId(null);
      }
      return true;
    } catch (error) {
      setAlbumsStatus({
        tone: "error",
        message:
          error instanceof Error
            ? `${error.message}. Make sure the API is running on ${API_BASE_URL}.`
            : `Could not reach the API at ${API_BASE_URL}.`,
      });
      return false;
    }
  }

  async function fetchAlbum(albumId: string): Promise<Album | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/albums/${albumId}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Failed to load album (${response.status})`);
      }

      const data = (await response.json()) as Album;
      setAlbums((current) => upsertAlbum(current, data));
      return data;
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Could not load album details.",
      });
      return null;
    }
  }

  useEffect(() => {
    startTransition(() => {
      void loadAlbums();
    });
  }, []);

  useEffect(() => {
    const storedDraft = window.localStorage.getItem(NEW_ALBUM_DRAFT_KEY);
    if (!storedDraft) {
      return;
    }

    if (name.trim() || newAlbumId) {
      return;
    }

    setName(storedDraft);
  }, []);

  useEffect(() => {
    if (albumMode !== "new" || newAlbumId) {
      return;
    }

    const trimmed = name.trim();
    if (!trimmed) {
      window.localStorage.removeItem(NEW_ALBUM_DRAFT_KEY);
      return;
    }

    window.localStorage.setItem(NEW_ALBUM_DRAFT_KEY, trimmed);
  }, [albumMode, name, newAlbumId]);

  useEffect(() => {
    clearUploadSelection();

    if (albumMode === "new") {
      setStatus({
        tone: "idle",
        message: newAlbumId
          ? "The new album already exists. Upload is available below."
          : "Create the new album first. Upload will appear right after that.",
      });
      return;
    }

    setStatus({
      tone: "idle",
      message: sidebarAlbum
        ? `Existing album "${sidebarAlbum.name}" is selected. Upload is ready below.`
        : "Choose an existing album in the sidebar to unlock upload.",
    });
  }, [albumMode, newAlbumId, sidebarAlbum]);

  useEffect(() => {
    setManualDescription(workflowAlbum?.description ?? "");

    if (!workflowAlbum) {
      setDescriptionStatus({
        tone: "idle",
        message: "Create or pick an album first. Description comes only after media upload.",
      });
      return;
    }

    if (workflowAlbum.media_items.length === 0) {
      setDescriptionStatus({
        tone: "idle",
        message: "Upload media first. Then choose Automatic AI or Manual for the description step.",
      });
      return;
    }

    if (workflowAlbum.description) {
      setDescriptionStatus({
        tone: "ok",
        message: "A saved description already exists. You can refine it manually or regenerate it with AI.",
      });
      return;
    }

    setDescriptionStatus({
      tone: "idle",
      message: "No saved description yet. Generate one from the media or write it manually.",
    });
  }, [workflowAlbum]);

  useEffect(() => {
    if (!workflowAlbum) {
      setSuggestionStatus({
        tone: "idle",
        message: "AI review will unlock after an album is chosen and media has been uploaded.",
      });
      return;
    }

    if (workflowAlbum.media_items.length === 0) {
      setSuggestionStatus({
        tone: "idle",
        message: "Upload media before asking AI to review the album.",
      });
      return;
    }

    if (activeSuggestions) {
      setSuggestionStatus({
        tone: "ok",
        message: "AI review is loaded for this album.",
      });
      return;
    }

    if (workflowAlbum.description) {
      setSuggestionStatus({
        tone: "idle",
        message: "Description is ready. Run AI review below when you want the first read.",
      });
      return;
    }

    setSuggestionStatus({
      tone: "idle",
      message: "Choose Automatic AI or Manual above first, then run the AI review.",
    });
  }, [workflowAlbum, activeSuggestions]);

  function handleModeChange(mode: "new" | "existing") {
    clearUploadSelection();
    setDescriptionMode("automatic");
    setAlbumMode(mode);

    if (mode === "new") {
      resetNewAlbumFlow();
      return;
    }

    setNewAlbumId(null);
    setSelectedAlbumId(null);
  }

  async function handleSidebarSelection(albumId: string) {
    clearUploadSelection();
    setSelectedAlbumId(albumId);
    if (albumMode === "existing") {
      const picked = (await fetchAlbum(albumId)) ?? albums.find((album) => album.id === albumId) ?? null;
      setStatus({
        tone: "ok",
        message: picked
          ? `Existing album "${picked.name}" is selected. Upload is ready below.`
          : "Existing album selected.",
      });
    }
  }

  async function handleCreateAlbum(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setStatus({ tone: "error", message: "Album name is required." });
      return;
    }

    if (duplicateAlbum) {
      setStatus({
        tone: "error",
        message: `Album "${duplicateAlbum.name}" already exists. Open it from the sidebar instead of creating a duplicate.`,
      });
      return;
    }

    setIsCreatingAlbum(true);
    setStatus({ tone: "idle", message: "Creating album..." });

    try {
      const response = await fetch(`${API_BASE_URL}/albums`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });

      if (!response.ok) {
        if (response.status === 409) {
          const conflict = (await response.json()) as { detail?: { message?: string; album_id?: string } };
          const existingAlbumId = conflict.detail?.album_id ?? null;
          if (existingAlbumId) {
            setSelectedAlbumId(existingAlbumId);
          }
          throw new Error(conflict.detail?.message ?? "Album with this name already exists.");
        }
        throw new Error(`Failed to create album (${response.status})`);
      }

      const createdAlbum = (await response.json()) as Album;
      setAlbums((current) => upsertAlbum(current, createdAlbum));
      clearUploadSelection();
      setName("");
      setNewAlbumId(createdAlbum.id);
      setSelectedAlbumId(createdAlbum.id);
      window.localStorage.removeItem(NEW_ALBUM_DRAFT_KEY);
      setStatus({
        tone: "ok",
        message: `Album "${createdAlbum.name}" created. Upload is now available below.`,
      });
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Album creation failed.",
      });
    } finally {
      setIsCreatingAlbum(false);
    }
  }

  function handleNewAlbumNameChange(event: ChangeEvent<HTMLInputElement>) {
    if (newAlbumId) {
      setNewAlbumId(null);
      clearUploadSelection();
    }
    setName(event.target.value);
  }

  function clearAlbumDerivedState(albumId: string) {
    setSuggestionsByAlbum((current) => {
      const next = { ...current };
      delete next[albumId];
      return next;
    });
    setDescriptionMetaByAlbum((current) => {
      const next = { ...current };
      delete next[albumId];
      return next;
    });
  }

  function handleFileSelection(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files);
    if (files.length > 0) {
      setStatus({ tone: "ok", message: `${files.length} file(s) selected and ready to upload.` });
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const files = Array.from(event.dataTransfer.files ?? []);
    if (files.length > 0) {
      setSelectedFiles(files);
      setStatus({ tone: "ok", message: `${files.length} file(s) selected and ready to upload.` });
    }
  }

  async function runAiSuggestions(albumId: string, successMessage?: string) {
    setIsAnalyzing(true);
    setSuggestionStatus({
      tone: "idle",
      message: "Running AI review on the uploaded media...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${albumId}/suggestions`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`AI review failed (${response.status})`);
      }

      const data = (await response.json()) as AlbumSuggestion;
      setSuggestionsByAlbum((current) => ({ ...current, [albumId]: data }));
      setSuggestionStatus({
        tone: "ok",
        message: successMessage ?? "AI review updated for this album.",
      });
    } catch (error) {
      setSuggestionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "AI review failed.",
      });
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleUploadFiles() {
    const targetAlbum = uploadTargetAlbum;

    if (!targetAlbum) {
      setStatus({ tone: "error", message: "Choose or create the target album first." });
      return;
    }

    if (selectedFiles.length === 0) {
      setStatus({ tone: "error", message: "Pick at least one file first." });
      return;
    }

    setStatus({ tone: "idle", message: `Uploading ${selectedFiles.length} file(s)...` });

    try {
      for (const file of selectedFiles) {
        const buffer = await file.arrayBuffer();
        const response = await fetch(`${API_BASE_URL}/albums/${targetAlbum.id}/upload`, {
          method: "POST",
          headers: {
            "Content-Type": file.type || "application/octet-stream",
            "X-Filename": file.name,
          },
          body: buffer,
        });

        if (!response.ok) {
          throw new Error(`Upload failed for ${file.name} (${response.status})`);
        }
      }

      const fileInput = document.getElementById("upload-input") as HTMLInputElement | null;
      if (fileInput) {
        fileInput.value = "";
      }
      setSelectedFiles([]);
      clearAlbumDerivedState(targetAlbum.id);
      await loadAlbums();
      setSelectedAlbumId(targetAlbum.id);
      setStatus({
        tone: "ok",
        message: `Upload finished for "${targetAlbum.name}". Step 3 is ready for description setup.`,
      });
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Upload failed.",
      });
    }
  }

  async function handleGenerateAutomaticDescription() {
    if (!workflowAlbum || workflowAlbum.media_items.length === 0) {
      setDescriptionStatus({
        tone: "error",
        message: "Upload media first. Automatic description needs real content to inspect.",
      });
      return;
    }

    setIsGeneratingDescription(true);
    setDescriptionStatus({
      tone: "idle",
      message: "Generating a saved album description from the uploaded media...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${workflowAlbum.id}/description/auto`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`Automatic description failed (${response.status})`);
      }

      const data = (await response.json()) as AutoDescriptionResponse;
      setAlbums((current) => upsertAlbum(current, data.album));
      setSelectedAlbumId(data.album.id);
      setManualDescription(data.description);
      setDescriptionMetaByAlbum((current) => ({
        ...current,
        [data.album.id]: {
          likelyCategories: data.likely_categories,
          analysisMode: data.analysis_mode,
        },
      }));
      setDescriptionStatus({
        tone: "ok",
        message: "AI description saved. Refreshing the album read below...",
      });
      await runAiSuggestions(data.album.id, "AI description saved and AI review refreshed below.");
    } catch (error) {
      setDescriptionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Automatic description failed.",
      });
    } finally {
      setIsGeneratingDescription(false);
    }
  }

  async function handleSaveManualDescription() {
    if (!workflowAlbum || workflowAlbum.media_items.length === 0) {
      setDescriptionStatus({
        tone: "error",
        message: "Upload media first. Manual description comes after the album has content.",
      });
      return;
    }

    setIsSavingDescription(true);
    setDescriptionStatus({
      tone: "idle",
      message: "Saving manual description...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${workflowAlbum.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: manualDescription.trim() || null }),
      });

      if (!response.ok) {
        throw new Error(`Manual description save failed (${response.status})`);
      }

      const updatedAlbum = (await response.json()) as Album;
      setAlbums((current) => upsertAlbum(current, updatedAlbum));
      setSelectedAlbumId(updatedAlbum.id);
      setManualDescription(updatedAlbum.description ?? "");
      setDescriptionStatus({
        tone: "ok",
        message: "Manual description saved. Refreshing the album read below...",
      });
      await runAiSuggestions(updatedAlbum.id, "Manual description saved and AI review refreshed below.");
    } catch (error) {
      setDescriptionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Manual description save failed.",
      });
    } finally {
      setIsSavingDescription(false);
    }
  }

  async function handleDeleteAlbum(album: Album) {
    const confirmed = window.confirm(`Delete album "${album.name}" and all of its uploaded media?`);
    if (!confirmed) {
      return;
    }

    setDeletingAlbumId(album.id);
    setStatus({
      tone: "idle",
      message: `Deleting album "${album.name}"...`,
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${album.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Album delete failed (${response.status})`);
      }

      setAlbums((current) => removeAlbum(current, album.id));
      clearAlbumDerivedState(album.id);
      clearUploadSelection();

      if (selectedAlbumId === album.id) {
        setSelectedAlbumId(null);
      }
      if (newAlbumId === album.id) {
        resetNewAlbumFlow();
      }

      setDescriptionStatus({
        tone: "idle",
        message: "Create or pick an album first. Description comes only after media upload.",
      });
      setSuggestionStatus({
        tone: "idle",
        message: "AI review will unlock after an album is chosen and media has been uploaded.",
      });
      setStatus({
        tone: "ok",
        message: `Album "${album.name}" deleted.`,
      });
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Album delete failed.",
      });
    } finally {
      setDeletingAlbumId(null);
    }
  }

  async function handleDeleteMediaItem(album: Album, item: MediaItem) {
    const confirmed = window.confirm(`Delete "${item.original_filename}" from "${album.name}"?`);
    if (!confirmed) {
      return;
    }

    setDeletingMediaId(item.id);
    setStatus({
      tone: "idle",
      message: `Deleting "${item.original_filename}"...`,
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${album.id}/media/${item.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Media delete failed (${response.status})`);
      }

      const updatedAlbum = (await response.json()) as Album;
      setAlbums((current) => upsertAlbum(current, updatedAlbum));
      clearAlbumDerivedState(album.id);
      setDescriptionStatus({
        tone: "idle",
        message:
          updatedAlbum.media_items.length > 0
            ? "Media updated. Re-run description or AI review when ready."
            : "This album is empty now. Upload media to continue.",
      });
      setSuggestionStatus({
        tone: "idle",
        message:
          updatedAlbum.media_items.length > 0
            ? "AI review was cleared because the album contents changed."
            : "AI review will unlock after new media is uploaded.",
      });
      setStatus({
        tone: "ok",
        message: `"${item.original_filename}" deleted from "${album.name}".`,
      });
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Media delete failed.",
      });
    } finally {
      setDeletingMediaId(null);
    }
  }

  function getInsightForMedia(mediaId: string): MediaInsight | null {
    return activeSuggestions?.media_insights.find((insight) => insight.media_id === mediaId) ?? null;
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="hero-panel">
          <p className="eyebrow">Travel Project V1</p>
          <h1 className="hero-title">Turn messy travel media into something you can actually review.</h1>
          <p className="hero-copy">
            This first browser slice is intentionally practical: choose a target album, upload media,
            decide how the album should be described, and then let AI build the first contextual read.
          </p>
          <div className="hero-stats">
            <div className="stat">
              <strong>{albums.length}</strong>
              <span>albums tracked locally</span>
            </div>
            <div className="stat">
              <strong>{workflowAlbum?.media_items.length ?? 0}</strong>
              <span>media items in active flow</span>
            </div>
            <div className="stat">
              <strong>{API_BASE_URL.replace("http://", "")}</strong>
              <span>current API target</span>
            </div>
          </div>
        </div>
        <div className="hero-side">
          <div className="hero-note">
            <h2>What works right now</h2>
            <p>
              Targeted album creation, explicit upload flow, local persistence, image preview, manual
              saved descriptions, AI-generated descriptions, and AI review from uploaded media.
            </p>
          </div>
          <div className="hero-note">
            <h2>What comes next</h2>
            <p>
              Better scene grouping, stronger travel-specific labels like cave or beach, EXIF and GPS
              extraction, and ranking for reels and carousel picks.
            </p>
          </div>
        </div>
      </section>

      <section className="grid">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Albums</h2>
            <span>{isPending ? "refreshing..." : "local view"}</span>
          </div>
          <p>Existing mode uses this sidebar as the target picker and review list.</p>
          {albumsStatus.message ? (
            <div className={`status ${albumsStatus.tone === "error" ? "error" : albumsStatus.tone === "ok" ? "ok" : ""}`}>
              {albumsStatus.message}
            </div>
          ) : null}

          <div className="album-list">
            {albums.length === 0 ? (
              <div className="empty">
                <p>No albums yet. Create the first one on the right.</p>
              </div>
            ) : (
              albums.map((album) => (
                <button
                  key={album.id}
                  className={`album-button ${selectedAlbumId === album.id ? "active" : ""}`}
                  onClick={() => void handleSidebarSelection(album.id)}
                  type="button"
                >
                  <strong>{album.name}</strong>
                  <small>
                    {album.media_items.length} item(s) • updated {formatDate(album.updated_at)}
                  </small>
                </button>
              ))
            )}
          </div>
        </aside>

        <div className="stack">
          <section className="surface">
            <div className="review-header">
              <div>
                <p className="eyebrow">Step 1</p>
                <h2>Choose target album</h2>
              </div>
            </div>

            <div className="mode-switch" role="tablist" aria-label="Album workflow mode">
              <button
                className={`mode-button ${albumMode === "new" ? "active" : ""}`}
                onClick={() => handleModeChange("new")}
                type="button"
              >
                New album
              </button>
              <button
                className={`mode-button ${albumMode === "existing" ? "active" : ""}`}
                onClick={() => handleModeChange("existing")}
                type="button"
              >
                Existing album
              </button>
            </div>

            {albumMode === "new" ? (
              <form className="form-grid" onSubmit={handleCreateAlbum}>
                <label className="field">
                  <span className="label-row">
                    <strong>Album name</strong>
                    <span className="hint">Required</span>
                  </span>
                  <input
                    className="input"
                    value={name}
                    onChange={handleNewAlbumNameChange}
                    placeholder="Petar cave run"
                  />
                </label>

                <div className="context-note">
                  <strong>Description comes later</strong>
                  <p>
                    For a new album, Step 1 only creates the target. After upload, Step 3 lets you
                    choose between an AI-generated description or a manual one.
                  </p>
                </div>

                {!newAlbumId && name.trim() ? (
                  <div className="selected-album-card">
                    <strong>Draft saved locally</strong>
                    <span>
                      This is still only a draft while you edit. Only the confirm button below makes
                      it a real album.
                    </span>
                  </div>
                ) : null}

                {duplicateAlbum ? (
                  <div className="selected-album-card">
                    <strong>Duplicate name detected</strong>
                    <span>
                      An album named "{duplicateAlbum.name}" already exists. Open that one instead of
                      creating a second album with the same name.
                    </span>
                    <div className="actions">
                      <button
                        className="button-secondary"
                        onClick={() => {
                          setAlbumMode("existing");
                          setSelectedAlbumId(duplicateAlbum.id);
                          setStatus({
                            tone: "ok",
                            message: `Opened existing album "${duplicateAlbum.name}".`,
                          });
                        }}
                        type="button"
                      >
                        Open existing album
                      </button>
                    </div>
                  </div>
                ) : null}

                <div className="actions">
                  <button
                    className="button-primary"
                    disabled={isPending || isCreatingAlbum || !name.trim() || Boolean(duplicateAlbum)}
                    type="submit"
                  >
                    {isCreatingAlbum ? "Creating..." : "Confirm and create album"}
                  </button>
                  {newAlbumId ? (
                    <button className="button-secondary" onClick={resetNewAlbumFlow} type="button">
                      Start another new album
                    </button>
                  ) : null}
                  <button
                    className="button-secondary"
                    disabled={isPending}
                    onClick={() => startTransition(() => void loadAlbums())}
                    type="button"
                  >
                    Refresh albums
                  </button>
                  {workflowAlbum ? (
                    <button
                      className="button-danger"
                      disabled={deletingAlbumId === workflowAlbum.id}
                      onClick={() => void handleDeleteAlbum(workflowAlbum)}
                      type="button"
                    >
                      {deletingAlbumId === workflowAlbum.id ? "Deleting..." : "Delete album"}
                    </button>
                  ) : null}
                </div>

                {newAlbumId && workflowAlbum ? (
                  <div className="selected-album-card">
                    <strong>Target ready</strong>
                    <span>{workflowAlbum.name} is ready. Upload appears below now.</span>
                  </div>
                ) : null}
              </form>
            ) : (
              <div className="form-grid">
                <div className="context-note compact">
                  <strong>Pick from the sidebar</strong>
                  <p>Click an existing album on the left. That is the whole selection step here.</p>
                </div>

                <div className="actions">
                  <button
                    className="button-secondary"
                    disabled={isPending}
                    onClick={() => startTransition(() => void loadAlbums())}
                    type="button"
                  >
                    Refresh albums
                  </button>
                  {workflowAlbum ? (
                    <button
                      className="button-danger"
                      disabled={deletingAlbumId === workflowAlbum.id}
                      onClick={() => void handleDeleteAlbum(workflowAlbum)}
                      type="button"
                    >
                      {deletingAlbumId === workflowAlbum.id ? "Deleting..." : "Delete album"}
                    </button>
                  ) : null}
                </div>

                <div className={`status ${workflowAlbum ? "ok" : ""}`}>
                  {workflowAlbum
                    ? `Current target: ${workflowAlbum.name}`
                    : "No existing album selected yet."}
                </div>
              </div>
            )}
          </section>

          {showUploadStep ? (
            <section className="surface">
              <div className="review-header">
                <div>
                  <p className="eyebrow">Step 2</p>
                  <h2>Upload files</h2>
                </div>
                <div className="review-meta">Target album: {uploadTargetAlbum?.name}</div>
              </div>

              <div className="form-grid">
                <div
                  className={`dropzone ${isDragging ? "dragging" : ""}`}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={(event) => {
                    event.preventDefault();
                    if (event.currentTarget === event.target) {
                      setIsDragging(false);
                    }
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    if (!isDragging) {
                      setIsDragging(true);
                    }
                  }}
                  onDrop={handleDrop}
                >
                  <span className="label-row">
                    <strong>Files</strong>
                    <span className="hint">Drag and drop or use the picker.</span>
                  </span>
                  <p className="dropzone-copy">
                    Upload into <strong>{uploadTargetAlbum?.name}</strong>. Images preview immediately.
                    Videos upload too, with richer metadata coming next.
                  </p>
                  <div className="actions">
                    <label className="button-secondary" htmlFor="upload-input">
                      Choose files
                    </label>
                  </div>
                  <input
                    id="upload-input"
                    className="sr-only"
                    multiple
                    onChange={handleFileSelection}
                    type="file"
                  />
                </div>

                {selectedFiles.length > 0 ? (
                  <div className="selected-files">
                    {selectedFiles.map((file) => (
                      <div className="file-pill" key={`${file.name}-${file.size}-${file.lastModified}`}>
                        <strong>{file.name}</strong>
                        <span>{formatBytes(file.size)}</span>
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="actions">
                  <button
                    className="button-primary"
                    disabled={selectedFiles.length === 0}
                    onClick={handleUploadFiles}
                    type="button"
                  >
                    Upload {selectedFiles.length > 0 ? `${selectedFiles.length} file(s)` : "files"}
                  </button>
                </div>
              </div>

              <div className={`status ${status.tone === "error" ? "error" : status.tone === "ok" ? "ok" : ""}`}>
                {status.message}
              </div>
            </section>
          ) : null}

          {showPostUploadSteps && workflowAlbum ? (
            <section className="surface">
              <div className="review-header">
                <div>
                  <p className="eyebrow">Step 3</p>
                  <h2>Describe the album</h2>
                </div>
                <div className="review-meta">
                  {workflowAlbum.media_items.length} item(s) in {workflowAlbum.name}
                </div>
              </div>

              <div className="mode-switch" role="tablist" aria-label="Description workflow mode">
                <button
                  className={`mode-button ${descriptionMode === "automatic" ? "active" : ""}`}
                  onClick={() => setDescriptionMode("automatic")}
                  type="button"
                >
                  Automatic AI
                </button>
                <button
                  className={`mode-button ${descriptionMode === "manual" ? "active" : ""}`}
                  onClick={() => setDescriptionMode("manual")}
                  type="button"
                >
                  Manual
                </button>
              </div>

              {descriptionMode === "automatic" ? (
                <div className="form-grid">
                  <div className="context-note">
                    <strong>Automatic description from uploaded media</strong>
                    <p>
                      AI will inspect the uploaded images, filenames, and metadata to generate the
                      saved album description. That becomes the context for the review step below.
                    </p>
                  </div>

                  {activeDescriptionMeta?.likelyCategories.length ? (
                    <div className="ai-card">
                      <strong>Automatic AI cues</strong>
                      <p>Last description pass used {activeDescriptionMeta.analysisMode} mode.</p>
                      <div className="tag-row">
                        {activeDescriptionMeta.likelyCategories.map((category) => (
                          <span className="tag" key={category}>
                            {category}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <div className="actions">
                    <button
                      className="button-primary"
                      disabled={isGeneratingDescription}
                      onClick={() => void handleGenerateAutomaticDescription()}
                      type="button"
                    >
                      {isGeneratingDescription
                        ? "Generating..."
                        : workflowAlbum.description
                          ? "Regenerate description with AI"
                          : "Generate description with AI"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="form-grid">
                  <label className="field">
                    <span className="label-row">
                      <strong>Manual description</strong>
                      <span className="hint">Saved after upload</span>
                    </span>
                    <textarea
                      className="textarea"
                      value={manualDescription}
                      onChange={(event) => setManualDescription(event.target.value)}
                      placeholder="Weekend through Petar caves with warm lamp light, tight stone passages, reflective pools, and a few group moments."
                    />
                  </label>

                  <div className="actions">
                    <button
                      className="button-primary"
                      disabled={isSavingDescription}
                      onClick={() => void handleSaveManualDescription()}
                      type="button"
                    >
                      {isSavingDescription ? "Saving..." : "Save manual description"}
                    </button>
                  </div>
                </div>
              )}

              <div
                className={`status ${
                  descriptionStatus.tone === "error" ? "error" : descriptionStatus.tone === "ok" ? "ok" : ""
                }`}
              >
                {descriptionStatus.message}
              </div>

              <div className="selected-album-card">
                <strong>Saved description</strong>
                <span>{workflowAlbum.description || "No saved description yet."}</span>
              </div>
            </section>
          ) : null}

          {showPostUploadSteps && workflowAlbum ? (
            <section className="surface">
              <div className="review-header">
                <div>
                  <p className="eyebrow">Step 4</p>
                  <h2>Review and AI analysis</h2>
                </div>
                <div className="review-meta">
                  {workflowAlbum.media_items.length} item(s) in {workflowAlbum.name}
                </div>
              </div>

              <div className="album-summary">
                <div className="ai-panel">
                  <div className="ai-panel-header">
                    <div>
                      <strong>AI review</strong>
                      <span>
                        {activeSuggestions
                          ? `Analysis mode: ${activeSuggestions.analysis_mode}`
                          : "Run the AI review when you want the first read of this album."}
                      </span>
                    </div>
                    <button
                      className="button-primary"
                      disabled={isAnalyzing}
                      onClick={() => void runAiSuggestions(workflowAlbum.id)}
                      type="button"
                    >
                      {isAnalyzing ? "Analyzing..." : activeSuggestions ? "Refresh AI read" : "Analyze album"}
                    </button>
                  </div>

                  <div
                    className={`status ${
                      suggestionStatus.tone === "error" ? "error" : suggestionStatus.tone === "ok" ? "ok" : ""
                    }`}
                  >
                    {suggestionStatus.message}
                  </div>

                  {activeSuggestions ? (
                    <div className="ai-grid">
                      <div className="ai-card ai-card-wide">
                        <strong>Album read</strong>
                        <p>{activeSuggestions.album_summary}</p>
                      </div>
                      <div className="ai-card ai-card-wide">
                        <strong>Trip story</strong>
                        <p>{activeSuggestions.visual_trip_story}</p>
                      </div>
                      <div className="ai-card">
                        <strong>Likely categories</strong>
                        <div className="tag-row">
                          {activeSuggestions.likely_categories.map((category) => (
                            <span className="tag" key={category}>
                              {category}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="ai-card">
                        <strong>Caption ideas</strong>
                        <ol className="caption-list">
                          {activeSuggestions.caption_ideas.map((caption) => (
                            <li key={caption}>{caption}</li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="media-grid">
                {workflowAlbum.media_items.map((item) => {
                  const mediaUrl = `${API_BASE_URL}/albums/${item.album_id}/media/${item.id}/content`;
                  const thumbnailUrl = item.thumbnail_relative_path
                    ? `${API_BASE_URL}/albums/${item.album_id}/media/${item.id}/thumbnail`
                    : undefined;
                  const insight = getInsightForMedia(item.id);

                  return (
                    <article className="media-card" key={item.id}>
                      <div className="media-visual">
                        {item.media_kind === "image" ? (
                          <img alt={item.original_filename} src={mediaUrl} />
                        ) : item.media_kind === "video" ? (
                          <video controls poster={thumbnailUrl} preload="metadata" src={mediaUrl} />
                        ) : (
                          <span>No inline preview yet</span>
                        )}
                      </div>
                      <div className="media-body">
                        <div className="media-card-header">
                          <strong>{item.original_filename}</strong>
                          <button
                            className="button-danger button-chip"
                            disabled={deletingMediaId === item.id}
                            onClick={() => void handleDeleteMediaItem(workflowAlbum, item)}
                            type="button"
                          >
                            {deletingMediaId === item.id ? "Deleting..." : "Delete"}
                          </button>
                        </div>
                        <div>
                          <p>{item.content_type}</p>
                        </div>

                        {insight ? (
                          <div className="ai-inline-note">
                            <strong>{insight.scene_guess}</strong>
                            <span>
                              {insight.use_case} • {insight.why_it_matters}
                            </span>
                          </div>
                        ) : null}

                        <div className="meta-grid">
                          <div className="meta-card">
                            <strong>Size</strong>
                            <span>{formatBytes(item.file_size_bytes)}</span>
                          </div>
                          <div className="meta-card">
                            <strong>Dimensions</strong>
                            <span>
                              {item.width && item.height ? `${item.width} × ${item.height}` : "Not detected"}
                            </span>
                          </div>
                          <div className="meta-card">
                            <strong>Kind</strong>
                            <span>{item.media_kind}</span>
                          </div>
                          <div className="meta-card">
                            <strong>Quality signal</strong>
                            <span>
                              {item.media_score !== null
                                ? formatMediaScore(item.media_score, item.media_score_label)
                                : "Pending"}
                            </span>
                          </div>
                          {item.duration_seconds !== null ? (
                            <div className="meta-card">
                              <strong>Duration</strong>
                              <span>{formatDuration(item.duration_seconds)}</span>
                            </div>
                          ) : null}
                          {item.frame_rate !== null ? (
                            <div className="meta-card">
                              <strong>Frame rate</strong>
                              <span>{formatFrameRate(item.frame_rate)}</span>
                            </div>
                          ) : null}
                          {item.video_codec ? (
                            <div className="meta-card">
                              <strong>Codec</strong>
                              <span>{item.video_codec}</span>
                            </div>
                          ) : null}
                          {item.metadata_source ? (
                            <div className="meta-card">
                              <strong>Metadata read</strong>
                              <span>{item.metadata_source}</span>
                            </div>
                          ) : null}
                          {item.captured_at ? (
                            <div className="meta-card">
                              <strong>Captured</strong>
                              <span>{formatDate(item.captured_at)}</span>
                            </div>
                          ) : null}
                          {item.source_device ? (
                            <div className="meta-card">
                              <strong>Device</strong>
                              <span>{item.source_device}</span>
                            </div>
                          ) : null}
                          {item.gps ? (
                            <div className="meta-card">
                              <strong>GPS</strong>
                              <span>{formatGps(item.gps)}</span>
                            </div>
                          ) : null}
                          <div className="meta-card">
                            <strong>Detected</strong>
                            <span>{formatDate(item.detected_at)}</span>
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}
