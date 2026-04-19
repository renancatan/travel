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
  analysis_frame_count: number;
  analysis_frame_timestamps_seconds: number[];
  media_score: number | null;
  media_score_label: string | null;
  detected_at: string;
  created_at: string;
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

type Album = {
  id: string;
  name: string;
  description: string | null;
  description_meta?: {
    likely_categories?: string[];
    analysis_mode?: string;
    route?: Record<string, unknown> | null;
  } | null;
  cached_suggestion?: AlbumSuggestion | null;
  rendered_reel?: RenderedReel | null;
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

type CurationCandidate = {
  media_id: string;
  media_kind: string;
  score: number;
  reason: string;
  group_id: string | null;
};

type ShotGroup = {
  group_id: string;
  label: string;
  representative_media_id: string;
  picked_media_id: string;
  media_ids: string[];
  item_count: number;
};

type ReelPlanStep = {
  step_number: number;
  role: string;
  media_id: string;
  media_kind: string;
  source_role: string;
  selection_mode: string;
  clip_start_seconds: number | null;
  clip_end_seconds: number | null;
  suggested_duration_seconds: number;
  edit_instruction: string;
  why: string;
};

type ReelPlan = {
  cover_media_id: string | null;
  video_strategy: string;
  estimated_total_duration_seconds: number;
  steps: ReelPlanStep[];
};

type ReelDraftAsset = {
  media_id: string;
  original_filename: string;
  media_kind: string;
  content_type: string;
  relative_path: string;
  thumbnail_relative_path: string | null;
};

type ReelDraftStep = {
  step_number: number;
  role: string;
  media_id: string;
  original_filename: string;
  media_kind: string;
  source_role: string;
  selection_mode: string;
  clip_start_seconds: number | null;
  clip_end_seconds: number | null;
  relative_path: string;
  suggested_duration_seconds: number;
  edit_instruction: string;
  why: string;
};

type ReelRenderClip = {
  step_number: number;
  role: string;
  media_id: string;
  original_filename: string;
  media_kind: string;
  render_mode: string;
  source_relative_path: string;
  output_relative_path: string;
  clip_start_seconds: number | null;
  clip_end_seconds: number | null;
  output_duration_seconds: number;
};

type ReelRenderSpec = {
  backend: string;
  backend_available: boolean;
  working_directory: string;
  output_relative_path: string;
  concat_relative_path: string;
  shell_commands: string[];
  notes: string[];
  clips: ReelRenderClip[];
};

type ReelDraft = {
  draft_name: string;
  title: string;
  caption: string;
  cover_media_id: string | null;
  video_strategy: string;
  estimated_total_duration_seconds: number;
  output_width: number;
  output_height: number;
  fps: number;
  audio_strategy: string;
  steps: ReelDraftStep[];
  assets: ReelDraftAsset[];
  render_spec: ReelRenderSpec | null;
};

type AlbumSuggestion = {
  album_summary: string;
  visual_trip_story: string;
  likely_categories: string[];
  caption_ideas: string[];
  cover_image_media_id: string | null;
  media_insights: MediaInsight[];
  cover_candidates: CurationCandidate[];
  carousel_candidates: CurationCandidate[];
  reel_candidates: CurationCandidate[];
  reel_plan: ReelPlan | null;
  reel_draft: ReelDraft | null;
  shot_groups: ShotGroup[];
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

type RenderReelResponse = {
  album: Album;
  rendered_reel: RenderedReel;
};

type DescriptionMeta = {
  likelyCategories: string[];
  analysisMode: string;
};

type UploadMediaResponse = {
  album: Album;
  media_item: MediaItem;
};

type AnalysisFrameSample = {
  timestamp_seconds: number;
  data_url: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const NEW_ALBUM_DRAFT_KEY = "travel-project:new-album-draft";
const DEFAULT_MAX_REEL_CLIP_DURATION_SECONDS = 30;

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

function formatCandidateScore(score: number): string {
  return `${score.toFixed(1)} pts`;
}

function formatVideoStrategy(value: string | null | undefined): string {
  if (value === "hero_video") {
    return "hero video";
  }
  if (value === "multi_clip_sequence") {
    return "multi-clip sequence";
  }
  if (value === "still_sequence") {
    return "still-led sequence";
  }
  return "mixed sequence";
}

function formatSourceRole(value: string): string {
  if (value === "hero_video") {
    return "hero video";
  }
  if (value === "supporting_video") {
    return "supporting video";
  }
  return "still image";
}

function formatClipWindow(start: number | null, end: number | null): string | null {
  if (start === null || end === null) {
    return null;
  }
  return `${start.toFixed(1)}s - ${end.toFixed(1)}s`;
}

function formatDraftAssetStatus(asset: ReelDraftAsset): string {
  if (asset.media_kind === "video") {
    return asset.thumbnail_relative_path ? "stored locally • preview frame ready" : "stored locally";
  }
  return "stored locally in album media";
}

function formatRenderMode(value: string): string {
  if (value === "video_trim") {
    return "trimmed video clip";
  }
  if (value === "image_hold") {
    return "held still image";
  }
  return value;
}

function roundToTenth(value: number): number {
  return Number(value.toFixed(1));
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function getMediaDurationSeconds(mediaItem: MediaItem | null): number | null {
  const duration = mediaItem?.duration_seconds;
  if (typeof duration !== "number" || !Number.isFinite(duration) || duration <= 0) {
    return null;
  }
  return roundToTenth(duration);
}

function getProjectReelClipDurationCap(value: number | null | undefined): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return DEFAULT_MAX_REEL_CLIP_DURATION_SECONDS;
  }
  return roundToTenth(value);
}

function getEditableVideoStepLimits(
  step: ReelDraftStep,
  mediaItem: MediaItem | null,
  projectMaxDurationSeconds: number,
) {
  const minDurationSeconds = 0.3;
  const mediaDurationSeconds = getMediaDurationSeconds(mediaItem);
  const maxClipDurationSeconds =
    mediaDurationSeconds === null
      ? projectMaxDurationSeconds
      : roundToTenth(Math.min(projectMaxDurationSeconds, mediaDurationSeconds));
  const currentClipStartSeconds = roundToTenth(Math.max(0, step.clip_start_seconds ?? 0));
  const maxClipStartSeconds =
    mediaDurationSeconds === null
      ? roundToTenth(Math.max(projectMaxDurationSeconds - minDurationSeconds, 0))
      : roundToTenth(Math.max(mediaDurationSeconds - minDurationSeconds, 0));
  const normalizedClipStartSeconds = Math.min(currentClipStartSeconds, maxClipStartSeconds);
  const maxClipEndSeconds =
    mediaDurationSeconds === null
      ? roundToTenth(normalizedClipStartSeconds + maxClipDurationSeconds)
      : roundToTenth(Math.min(mediaDurationSeconds, normalizedClipStartSeconds + maxClipDurationSeconds));
  const maxStepDurationSeconds = roundToTenth(
    Math.max(minDurationSeconds, maxClipEndSeconds - normalizedClipStartSeconds),
  );

  return {
    minDurationSeconds,
    mediaDurationSeconds,
    maxClipDurationSeconds,
    maxClipStartSeconds,
    maxClipEndSeconds,
    maxStepDurationSeconds,
  };
}

function normalizeEditableVideoStep(
  step: ReelDraftStep,
  mediaItem: MediaItem | null,
  projectMaxDurationSeconds: number,
): ReelDraftStep {
  const limits = getEditableVideoStepLimits(step, mediaItem, projectMaxDurationSeconds);
  let clipStartSeconds = roundToTenth(
    clampNumber(step.clip_start_seconds ?? 0, 0, limits.maxClipStartSeconds),
  );
  const maxClipEndSeconds =
    limits.mediaDurationSeconds === null
      ? roundToTenth(clipStartSeconds + limits.maxClipDurationSeconds)
      : roundToTenth(Math.min(limits.mediaDurationSeconds, clipStartSeconds + limits.maxClipDurationSeconds));
  let clipEndSeconds = step.clip_end_seconds ?? clipStartSeconds + (step.suggested_duration_seconds || 0.3);
  clipEndSeconds = roundToTenth(
    clampNumber(clipEndSeconds, clipStartSeconds + limits.minDurationSeconds, maxClipEndSeconds),
  );

  if (clipEndSeconds <= clipStartSeconds) {
    const fallbackEndSeconds = roundToTenth(
      Math.min(maxClipEndSeconds, clipStartSeconds + limits.minDurationSeconds),
    );
    if (fallbackEndSeconds <= clipStartSeconds) {
      clipStartSeconds = roundToTenth(Math.max(0, maxClipEndSeconds - limits.minDurationSeconds));
      clipEndSeconds = roundToTenth(maxClipEndSeconds);
    } else {
      clipEndSeconds = fallbackEndSeconds;
    }
  }

  const suggestedDurationSeconds = roundToTenth(
    Math.max(limits.minDurationSeconds, clipEndSeconds - clipStartSeconds),
  );

  return {
    ...step,
    clip_start_seconds: clipStartSeconds,
    clip_end_seconds: clipEndSeconds,
    suggested_duration_seconds: suggestedDurationSeconds,
  };
}

function getRenderedReelContentUrl(album: Album | null): string | null {
  const renderedReel = album?.rendered_reel;
  if (!album || !renderedReel) {
    return null;
  }

  const cacheKey = encodeURIComponent(
    `${renderedReel.rendered_at}-${renderedReel.file_size_bytes}-${renderedReel.estimated_total_duration_seconds}`,
  );
  return `${API_BASE_URL}/albums/${album.id}/rendered-reel/content?v=${cacheKey}`;
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

function buildAlbumCaches(albums: Album[]): {
  suggestions: Record<string, AlbumSuggestion>;
  descriptionMeta: Record<string, DescriptionMeta>;
} {
  const nextSuggestions: Record<string, AlbumSuggestion> = {};
  const nextDescriptionMeta: Record<string, DescriptionMeta> = {};

  for (const album of albums) {
    if (album.cached_suggestion) {
      nextSuggestions[album.id] = album.cached_suggestion;
    }
    if (album.description_meta) {
      nextDescriptionMeta[album.id] = {
        likelyCategories: album.description_meta.likely_categories ?? [],
        analysisMode: album.description_meta.analysis_mode ?? "unknown",
      };
    }
  }

  return {
    suggestions: nextSuggestions,
    descriptionMeta: nextDescriptionMeta,
  };
}

function cloneReelDraft(draft: ReelDraft | null | undefined): ReelDraft | null {
  if (!draft) {
    return null;
  }
  return JSON.parse(JSON.stringify(draft)) as ReelDraft;
}

function buildReelDraftEditPayload(draft: ReelDraft) {
  return {
    reel_draft: {
      title: draft.title,
      caption: draft.caption,
      cover_media_id: draft.cover_media_id,
      steps: draft.steps.map((step) => ({
        role: step.role,
        media_id: step.media_id,
        source_role: step.source_role,
        suggested_duration_seconds: step.suggested_duration_seconds,
        clip_start_seconds: step.clip_start_seconds,
        clip_end_seconds: step.clip_end_seconds,
        edit_instruction: step.edit_instruction,
        why: step.why,
      })),
    },
  };
}

function downloadJsonFile(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function extractVideoFrameSamples(file: File): Promise<AnalysisFrameSample[]> {
  const objectUrl = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "auto";
  video.muted = true;
  video.playsInline = true;
  video.src = objectUrl;

  try {
    await new Promise<void>((resolve, reject) => {
      const handleLoaded = () => {
        cleanup();
        resolve();
      };
      const handleError = () => {
        cleanup();
        reject(new Error(`Could not read video frames from ${file.name}.`));
      };
      const cleanup = () => {
        video.removeEventListener("loadeddata", handleLoaded);
        video.removeEventListener("error", handleError);
      };

      video.addEventListener("loadeddata", handleLoaded);
      video.addEventListener("error", handleError);
    });

    const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0;
    const timestamps = duration > 0
      ? Array.from(
          new Set(
            [duration * 0.15, duration * 0.5, duration * 0.85]
              .map((value) => {
                const capped = Math.min(value, Math.max(duration - 0.05, 0));
                return Number(Math.max(capped, 0).toFixed(2));
              })
              .filter((value) => Number.isFinite(value)),
          ),
        )
      : [0];

    const maxEdge = 960;
    const scale = Math.min(1, maxEdge / Math.max(video.videoWidth || 1, video.videoHeight || 1));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round((video.videoWidth || 1) * scale));
    canvas.height = Math.max(1, Math.round((video.videoHeight || 1) * scale));
    const context = canvas.getContext("2d");
    if (!context) {
      return [];
    }

    const frames: AnalysisFrameSample[] = [];
    for (const timestamp of timestamps) {
      await seekVideoForFrame(video, timestamp);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      frames.push({
        timestamp_seconds: timestamp,
        data_url: canvas.toDataURL("image/jpeg", 0.82),
      });
    }

    return frames;
  } finally {
    URL.revokeObjectURL(objectUrl);
    video.removeAttribute("src");
    video.load();
  }
}

async function seekVideoForFrame(video: HTMLVideoElement, timestamp: number): Promise<void> {
  const safeTimestamp =
    Number.isFinite(video.duration) && video.duration > 0
      ? Math.min(Math.max(timestamp, 0), Math.max(video.duration - 0.05, 0))
      : 0;

  if (Math.abs(video.currentTime - safeTimestamp) < 0.05) {
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const handleSeeked = () => {
      cleanup();
      resolve();
    };
    const handleError = () => {
      cleanup();
      reject(new Error("Video seek failed while sampling frames."));
    };
    const cleanup = () => {
      video.removeEventListener("seeked", handleSeeked);
      video.removeEventListener("error", handleError);
    };

    video.addEventListener("seeked", handleSeeked);
    video.addEventListener("error", handleError);
    video.currentTime = safeTimestamp;
  });

  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
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
  const [autoRebuiltSuggestionAlbumIds, setAutoRebuiltSuggestionAlbumIds] = useState<Record<string, boolean>>({});
  const [deletingAlbumId, setDeletingAlbumId] = useState<string | null>(null);
  const [deletingMediaId, setDeletingMediaId] = useState<string | null>(null);
  const [isRenderingReel, setIsRenderingReel] = useState(false);
  const [isSavingReelDraft, setIsSavingReelDraft] = useState(false);
  const [editableReelDraft, setEditableReelDraft] = useState<ReelDraft | null>(null);
  const [maxReelClipDurationSeconds, setMaxReelClipDurationSeconds] = useState(
    DEFAULT_MAX_REEL_CLIP_DURATION_SECONDS,
  );
  const [isPending, startTransition] = useTransition();

  const sidebarAlbum = albums.find((album) => album.id === selectedAlbumId) ?? null;
  const workflowAlbum =
    albumMode === "new" ? albums.find((album) => album.id === newAlbumId) ?? null : sidebarAlbum;
  const activeSuggestions = workflowAlbum ? suggestionsByAlbum[workflowAlbum.id] ?? null : null;
  const activeDescriptionMeta = workflowAlbum ? descriptionMetaByAlbum[workflowAlbum.id] ?? null : null;
  const workingReelDraft = editableReelDraft ?? activeSuggestions?.reel_draft ?? null;
  const isReelDraftDirty = Boolean(
    editableReelDraft &&
      activeSuggestions?.reel_draft &&
      JSON.stringify(buildReelDraftEditPayload(editableReelDraft)) !==
        JSON.stringify(buildReelDraftEditPayload(activeSuggestions.reel_draft))
  );
  const renderSpec =
    !isReelDraftDirty && workingReelDraft?.render_spec ? workingReelDraft.render_spec : activeSuggestions?.reel_draft?.render_spec ?? null;
  const renderBackendAvailable = Boolean(renderSpec?.backend_available);
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
      const caches = buildAlbumCaches(data);
      setSuggestionsByAlbum(caches.suggestions);
      setDescriptionMetaByAlbum(caches.descriptionMeta);
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

  async function loadRuntimeConfig() {
    try {
      const response = await fetch(`${API_BASE_URL}/runtime`, { cache: "no-store" });
      if (!response.ok) {
        return;
      }

      const data = (await response.json()) as {
        editor_limits?: { max_reel_clip_duration_seconds?: number };
      };
      const nextLimit = getProjectReelClipDurationCap(
        data.editor_limits?.max_reel_clip_duration_seconds,
      );
      setMaxReelClipDurationSeconds(nextLimit);
    } catch {
      // Fall back to the local default when runtime metadata is unavailable.
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
      if (data.cached_suggestion) {
        setSuggestionsByAlbum((current) => ({ ...current, [data.id]: data.cached_suggestion as AlbumSuggestion }));
      } else {
        setSuggestionsByAlbum((current) => {
          const next = { ...current };
          delete next[data.id];
          return next;
        });
      }
      if (data.description_meta) {
        setDescriptionMetaByAlbum((current) => ({
          ...current,
          [data.id]: {
            likelyCategories: data.description_meta?.likely_categories ?? [],
            analysisMode: data.description_meta?.analysis_mode ?? "unknown",
          },
        }));
      } else {
        setDescriptionMetaByAlbum((current) => {
          const next = { ...current };
          delete next[data.id];
          return next;
        });
      }
      return data;
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Could not load album details.",
      });
      return null;
    }
  }

  function syncAlbumStateFromApi(updatedAlbum: Album) {
    setAlbums((current) => upsertAlbum(current, updatedAlbum));

    if (updatedAlbum.cached_suggestion) {
      setSuggestionsByAlbum((current) => ({
        ...current,
        [updatedAlbum.id]: updatedAlbum.cached_suggestion as AlbumSuggestion,
      }));
    } else {
      setSuggestionsByAlbum((current) => {
        const next = { ...current };
        delete next[updatedAlbum.id];
        return next;
      });
    }

    if (updatedAlbum.description_meta) {
      setDescriptionMetaByAlbum((current) => ({
        ...current,
        [updatedAlbum.id]: {
          likelyCategories: updatedAlbum.description_meta?.likely_categories ?? [],
          analysisMode: updatedAlbum.description_meta?.analysis_mode ?? "unknown",
        },
      }));
    } else {
      setDescriptionMetaByAlbum((current) => {
        const next = { ...current };
        delete next[updatedAlbum.id];
        return next;
      });
    }
  }

  function getWorkflowMediaItem(mediaId: string): MediaItem | null {
    if (!workflowAlbum) {
      return null;
    }
    return workflowAlbum.media_items.find((item) => item.id === mediaId) ?? null;
  }

  function resetEditableReelDraft() {
    setEditableReelDraft(cloneReelDraft(activeSuggestions?.reel_draft));
  }

  function moveEditableReelStep(stepIndex: number, direction: -1 | 1) {
    setEditableReelDraft((current) => {
      if (!current) {
        return current;
      }

      const targetIndex = stepIndex + direction;
      if (targetIndex < 0 || targetIndex >= current.steps.length) {
        return current;
      }

      const nextSteps = [...current.steps];
      const [movedStep] = nextSteps.splice(stepIndex, 1);
      nextSteps.splice(targetIndex, 0, movedStep);
      return {
        ...current,
        steps: nextSteps.map((step, index) => ({
          ...step,
          step_number: index + 1,
        })),
      };
    });
  }

  function updateEditableReelStepMedia(stepIndex: number, mediaId: string) {
    setEditableReelDraft((current) => {
      if (!current) {
        return current;
      }

      const mediaItem = getWorkflowMediaItem(mediaId);
      if (!mediaItem) {
        return current;
      }

      const nextSteps = current.steps.map((step, index) => {
        if (index !== stepIndex) {
          return step;
        }

        if (mediaItem.media_kind === "video") {
          const defaultDurationSeconds = Math.min(
            getMediaDurationSeconds(mediaItem) ?? maxReelClipDurationSeconds,
            3,
          );
          return normalizeEditableVideoStep(
            {
              ...step,
              media_id: mediaItem.id,
              original_filename: mediaItem.original_filename,
              media_kind: mediaItem.media_kind,
              relative_path: mediaItem.relative_path,
              source_role:
                step.source_role === "still_image"
                  ? stepIndex === 0
                    ? "hero_video"
                    : "supporting_video"
                  : step.source_role,
              selection_mode: "video_clip",
              clip_start_seconds: 0,
              clip_end_seconds: roundToTenth(defaultDurationSeconds),
              suggested_duration_seconds: roundToTenth(defaultDurationSeconds),
            },
            mediaItem,
            maxReelClipDurationSeconds,
          );
        }

        return {
          ...step,
          media_id: mediaItem.id,
          original_filename: mediaItem.original_filename,
          media_kind: mediaItem.media_kind,
          relative_path: mediaItem.relative_path,
          source_role: "still_image",
          selection_mode: "full_frame",
          clip_start_seconds: null,
          clip_end_seconds: null,
          suggested_duration_seconds: roundToTenth(
            Math.min(maxReelClipDurationSeconds, Math.max(0.5, step.suggested_duration_seconds)),
          ),
        };
      });

      const nextAssets = current.assets.some((asset) => asset.media_id === mediaItem.id)
        ? current.assets
        : [
            ...current.assets,
            {
              media_id: mediaItem.id,
              original_filename: mediaItem.original_filename,
              media_kind: mediaItem.media_kind,
              content_type: mediaItem.content_type,
              relative_path: mediaItem.relative_path,
              thumbnail_relative_path: mediaItem.thumbnail_relative_path,
            },
          ];

      return {
        ...current,
        cover_media_id: current.cover_media_id ?? nextSteps[0]?.media_id ?? current.cover_media_id,
        assets: nextAssets,
        steps: nextSteps,
      };
    });
  }

  function updateEditableReelStepField(
    stepIndex: number,
    field: "role" | "edit_instruction" | "why" | "suggested_duration_seconds" | "clip_start_seconds" | "clip_end_seconds",
    value: string
  ) {
    setEditableReelDraft((current) => {
      if (!current) {
        return current;
      }

      const nextSteps = current.steps.map((step, index) => {
        if (index !== stepIndex) {
          return step;
        }

        if (field === "role" || field === "edit_instruction" || field === "why") {
          return {
            ...step,
            [field]: value,
          };
        }

        const parsedValue = value === "" ? null : Number(value);
        if (parsedValue === null || Number.isNaN(parsedValue)) {
          return {
            ...step,
            [field]: null,
          };
        }

        if (step.media_kind !== "video") {
          if (field === "suggested_duration_seconds") {
            return {
              ...step,
              suggested_duration_seconds: roundToTenth(
                clampNumber(parsedValue, 0.5, maxReelClipDurationSeconds),
              ),
            };
          }
          return {
            ...step,
            [field]: roundToTenth(Math.max(0, parsedValue)),
          };
        }

        const nextStep = {
          ...step,
          [field]: roundToTenth(Math.max(0, parsedValue)),
        };

        if (field === "suggested_duration_seconds") {
          const clipStartSeconds = roundToTenth(nextStep.clip_start_seconds ?? 0);
          nextStep.clip_start_seconds = clipStartSeconds;
          nextStep.clip_end_seconds = roundToTenth(clipStartSeconds + parsedValue);
        }

        return normalizeEditableVideoStep(
          nextStep,
          getWorkflowMediaItem(step.media_id),
          maxReelClipDurationSeconds,
        );
      });

      return {
        ...current,
        steps: nextSteps,
      };
    });
  }

  useEffect(() => {
    void loadRuntimeConfig();
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

  useEffect(() => {
    setEditableReelDraft(cloneReelDraft(activeSuggestions?.reel_draft));
  }, [workflowAlbum?.id, activeSuggestions?.reel_draft]);

  useEffect(() => {
    if (albumMode !== "existing" || !workflowAlbum || activeSuggestions || isAnalyzing) {
      return;
    }

    if (workflowAlbum.media_items.length === 0 || !workflowAlbum.description) {
      return;
    }

    if (workflowAlbum.cached_suggestion || autoRebuiltSuggestionAlbumIds[workflowAlbum.id]) {
      return;
    }

    setAutoRebuiltSuggestionAlbumIds((current) => ({ ...current, [workflowAlbum.id]: true }));
    setSuggestionStatus({
      tone: "idle",
      message: "No cached AI review was found for this older album. Rebuilding it now...",
    });
    void runAiSuggestions(workflowAlbum.id, "AI review rebuilt and cached for this album.");
  }, [albumMode, workflowAlbum, activeSuggestions, isAnalyzing, autoRebuiltSuggestionAlbumIds]);

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

  async function uploadVideoAnalysisFrames(
    albumId: string,
    mediaId: string,
    frames: AnalysisFrameSample[],
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/albums/${albumId}/media/${mediaId}/analysis-frames`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frames }),
    });

    if (!response.ok) {
      throw new Error(`Video analysis frame upload failed (${response.status})`);
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
      let sampledVideoCount = 0;
      let sampledFrameCount = 0;
      const warnings: string[] = [];

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

        const uploadResult = (await response.json()) as UploadMediaResponse;
        if (uploadResult.media_item.media_kind === "video") {
          try {
            const frames = await extractVideoFrameSamples(file);
            if (frames.length > 0) {
              await uploadVideoAnalysisFrames(targetAlbum.id, uploadResult.media_item.id, frames);
              sampledVideoCount += 1;
              sampledFrameCount += frames.length;
            } else {
              warnings.push(`No browser frame samples were created for ${file.name}.`);
            }
          } catch (error) {
            warnings.push(
              error instanceof Error ? `${file.name}: ${error.message}` : `${file.name}: video frame sampling failed.`,
            );
          }
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
        message:
          `Upload finished for "${targetAlbum.name}". Step 3 is ready for description setup.` +
          (sampledVideoCount > 0 ? ` Sampled ${sampledFrameCount} AI frame(s) from ${sampledVideoCount} video(s).` : "") +
          (warnings.length > 0 ? ` ${warnings.join(" ")}` : ""),
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

  async function handleCopyReelCaption() {
    if (!workingReelDraft) {
      setSuggestionStatus({
        tone: "error",
        message: "Run AI review first. The reel draft is not ready yet.",
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(workingReelDraft.caption);
      setSuggestionStatus({
        tone: "ok",
        message: "Reel caption copied to your clipboard.",
      });
    } catch (error) {
      setSuggestionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Could not copy the caption.",
      });
    }
  }

  function handleDownloadReelDraft() {
    if (!workingReelDraft) {
      setSuggestionStatus({
        tone: "error",
        message: "Run AI review first. The reel draft is not ready yet.",
      });
      return;
    }

    downloadJsonFile(`${workingReelDraft.draft_name}.json`, workingReelDraft);
    setSuggestionStatus({
      tone: "ok",
      message: "Reel draft JSON downloaded.",
    });
  }

  async function handleCopyRenderCommands() {
    if (!renderSpec?.shell_commands.length) {
      setSuggestionStatus({
        tone: "error",
        message: "No render commands are available yet for this reel draft.",
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(renderSpec.shell_commands.join("\n"));
      setSuggestionStatus({
        tone: "ok",
        message: "Render commands copied to your clipboard.",
      });
    } catch (error) {
      setSuggestionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Could not copy render commands.",
      });
    }
  }

  async function handleApplyReelDraftEdits() {
    if (!workflowAlbum || !editableReelDraft) {
      setSuggestionStatus({
        tone: "error",
        message: "Choose an album and run AI review before editing the reel draft.",
      });
      return;
    }

    setIsSavingReelDraft(true);
    setSuggestionStatus({
      tone: "idle",
      message: "Saving reel draft edits...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${workflowAlbum.id}/reel-draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildReelDraftEditPayload(editableReelDraft)),
      });

      if (!response.ok) {
        const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(detail?.detail ?? `Could not save reel edits (${response.status})`);
      }

      const updatedAlbum = (await response.json()) as Album;
      syncAlbumStateFromApi(updatedAlbum);
      setSuggestionStatus({
        tone: "ok",
        message: "Reel draft edits saved. The render spec has been refreshed.",
      });
    } catch (error) {
      setSuggestionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Could not save reel draft edits.",
      });
    } finally {
      setIsSavingReelDraft(false);
    }
  }

  async function handleRenderReel() {
    if (!workflowAlbum) {
      setSuggestionStatus({
        tone: "error",
        message: "Choose an album first. There is no active reel to render.",
      });
      return;
    }

    if (!workingReelDraft) {
      setSuggestionStatus({
        tone: "error",
        message: "Run AI review first. The reel draft is not ready yet.",
      });
      return;
    }

    if (!renderBackendAvailable) {
      setSuggestionStatus({
        tone: "error",
        message: "Local reel rendering is disabled because ffmpeg is not installed on this machine yet.",
      });
      return;
    }

    setIsRenderingReel(true);
    setSuggestionStatus({
      tone: "idle",
      message: isReelDraftDirty ? "Saving edits and rendering reel locally..." : "Rendering reel locally...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/albums/${workflowAlbum.id}/rendered-reel`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: isReelDraftDirty ? JSON.stringify(buildReelDraftEditPayload(workingReelDraft)) : undefined,
      });

      if (!response.ok) {
        const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(detail?.detail ?? `Render failed (${response.status})`);
      }

      const data = (await response.json()) as RenderReelResponse;
      syncAlbumStateFromApi(data.album);
      setSuggestionStatus({
        tone: "ok",
        message: isReelDraftDirty
          ? `Edits were applied and the rendered reel is ready for "${data.album.name}".`
          : `Rendered reel is ready for "${data.album.name}".`,
      });
    } catch (error) {
      setSuggestionStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Render failed.",
      });
    } finally {
      setIsRenderingReel(false);
    }
  }

  function handleDownloadRenderedReel() {
    if (!workflowAlbum?.rendered_reel) {
      setSuggestionStatus({
        tone: "error",
        message: "Render a reel first. There is no final video to download yet.",
      });
      return;
    }

    const renderedReelUrl = getRenderedReelContentUrl(workflowAlbum);
    if (!renderedReelUrl) {
      setSuggestionStatus({
        tone: "error",
        message: "Rendered reel URL is not available yet.",
      });
      return;
    }

    const link = document.createElement("a");
    link.href = renderedReelUrl;
    link.download = `${workflowAlbum.rendered_reel.draft_name}.mp4`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function getInsightForMedia(mediaId: string): MediaInsight | null {
    return activeSuggestions?.media_insights.find((insight) => insight.media_id === mediaId) ?? null;
  }

  function getMediaLabel(mediaId: string | null): string {
    if (!mediaId || !workflowAlbum) {
      return "Unknown media";
    }

    const mediaItem = workflowAlbum.media_items.find((item) => item.id === mediaId);
    return mediaItem?.original_filename ?? mediaId;
  }

  const renderedReelContentUrl = getRenderedReelContentUrl(workflowAlbum);

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
                      <div className="ai-card">
                        <strong>Cover picks</strong>
                        {activeSuggestions.cover_candidates.length > 0 ? (
                          <div className="candidate-list">
                            {activeSuggestions.cover_candidates.map((candidate) => (
                              <div className="candidate-row" key={`cover-${candidate.media_id}`}>
                                <div>
                                  <strong>{getMediaLabel(candidate.media_id)}</strong>
                                  <span>{candidate.reason}</span>
                                </div>
                                <em>{formatCandidateScore(candidate.score)}</em>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p>No cover picks yet.</p>
                        )}
                      </div>
                      <div className="ai-card">
                        <strong>Carousel picks</strong>
                        {activeSuggestions.carousel_candidates.length > 0 ? (
                          <div className="candidate-list">
                            {activeSuggestions.carousel_candidates.map((candidate) => (
                              <div className="candidate-row" key={`carousel-${candidate.media_id}`}>
                                <div>
                                  <strong>{getMediaLabel(candidate.media_id)}</strong>
                                  <span>{candidate.reason}</span>
                                </div>
                                <em>{formatCandidateScore(candidate.score)}</em>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p>No carousel picks yet.</p>
                        )}
                      </div>
                      <div className="ai-card ai-card-wide">
                        <strong>Reel candidates</strong>
                        {activeSuggestions.reel_candidates.length > 0 ? (
                          <div className="candidate-list">
                            {activeSuggestions.reel_candidates.map((candidate) => (
                              <div className="candidate-row" key={`reel-${candidate.media_id}`}>
                                <div>
                                  <strong>{getMediaLabel(candidate.media_id)}</strong>
                                  <span>{candidate.reason}</span>
                                </div>
                                <em>{formatCandidateScore(candidate.score)}</em>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p>No reel candidates yet.</p>
                        )}
                      </div>
                      <div className="ai-card ai-card-wide">
                        <div className="reel-plan-header">
                          <div>
                            <strong>Reel plan</strong>
                            <p>
                              {activeSuggestions.reel_plan
                                ? `${activeSuggestions.reel_plan.steps.length} beat(s) • estimated ${formatDuration(
                                    activeSuggestions.reel_plan.estimated_total_duration_seconds,
                                  )} • ${formatVideoStrategy(activeSuggestions.reel_plan.video_strategy)}`
                                : "A step-by-step short-form sequence appears here after the reel read is built."}
                            </p>
                          </div>
                          {activeSuggestions.reel_plan?.cover_media_id ? (
                            <span className="reel-plan-cover">
                              Cover: {getMediaLabel(activeSuggestions.reel_plan.cover_media_id)}
                            </span>
                          ) : null}
                        </div>
                        {activeSuggestions.reel_plan?.steps.length ? (
                          <div className="reel-plan-list">
                            {activeSuggestions.reel_plan.steps.map((step) => (
                              <div className="reel-plan-step" key={`reel-plan-${step.step_number}-${step.media_id}`}>
                                <div className="reel-plan-step-header">
                                  <div>
                                    <span className="reel-plan-index">Step {step.step_number}</span>
                                    <strong>
                                      {step.role}: {getMediaLabel(step.media_id)}
                                    </strong>
                                  </div>
                                  <div className="reel-plan-meta">
                                    <span>
                                      {step.media_kind} • {formatSourceRole(step.source_role)}
                                    </span>
                                    {step.selection_mode === "video_clip" ? (
                                      <span>{formatClipWindow(step.clip_start_seconds, step.clip_end_seconds)}</span>
                                    ) : null}
                                    <em>{formatDuration(step.suggested_duration_seconds)}</em>
                                  </div>
                                </div>
                                <p>{step.edit_instruction}</p>
                                <small>{step.why}</small>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p>No reel plan yet.</p>
                        )}
                      </div>
                      <div className="ai-card ai-card-wide">
                        <div className="reel-plan-header">
                          <div>
                            <strong>Reel draft export</strong>
                            <p>
                              {workingReelDraft
                                ? `${workingReelDraft.output_width}x${workingReelDraft.output_height} • ${workingReelDraft.fps} fps • ${workingReelDraft.assets.length} asset(s) • ${formatVideoStrategy(workingReelDraft.video_strategy)}`
                                : "A downloadable reel draft manifest appears here after the AI review runs."}
                            </p>
                          </div>
                          {workingReelDraft ? (
                            <div className="actions">
                              <button className="button-secondary" onClick={handleCopyReelCaption} type="button">
                                Copy caption
                              </button>
                              {renderSpec?.shell_commands.length ? (
                                <button className="button-secondary" onClick={handleCopyRenderCommands} type="button">
                                  Copy render commands
                                </button>
                              ) : null}
                              <button
                                className="button-secondary"
                                disabled={!isReelDraftDirty || isSavingReelDraft}
                                onClick={() => void handleApplyReelDraftEdits()}
                                type="button"
                              >
                                {isSavingReelDraft ? "Saving edits..." : "Apply draft edits"}
                              </button>
                              <button
                                className="button-secondary"
                                disabled={!isReelDraftDirty}
                                onClick={resetEditableReelDraft}
                                type="button"
                              >
                                Reset edits
                              </button>
                              <button
                                className="button-secondary"
                                disabled={!renderBackendAvailable || isRenderingReel || isSavingReelDraft}
                                onClick={handleRenderReel}
                                title={
                                  renderBackendAvailable
                                    ? "Render the current reel draft locally."
                                    : "Install ffmpeg locally to enable reel rendering."
                                }
                                type="button"
                              >
                                {isRenderingReel
                                  ? "Rendering..."
                                  : !renderBackendAvailable
                                    ? "ffmpeg required"
                                  : workflowAlbum?.rendered_reel
                                    ? "Re-render reel"
                                    : "Render reel"}
                              </button>
                              <button className="button-primary" onClick={handleDownloadReelDraft} type="button">
                                Download draft JSON
                              </button>
                            </div>
                          ) : null}
                        </div>
                        {workingReelDraft ? (
                          <div className="reel-draft-grid">
                            <div className="meta-card reel-draft-card">
                              <strong>Draft title</strong>
                              <input
                                className="input draft-input"
                                value={workingReelDraft.title}
                                onChange={(event) =>
                                  setEditableReelDraft((current) =>
                                    current
                                      ? {
                                          ...current,
                                          title: event.target.value,
                                        }
                                      : current,
                                  )
                                }
                                type="text"
                              />
                            </div>
                            <div className="meta-card reel-draft-card">
                              <strong>Cover</strong>
                              <select
                                className="input draft-input"
                                value={workingReelDraft.cover_media_id ?? ""}
                                onChange={(event) =>
                                  setEditableReelDraft((current) =>
                                    current
                                      ? {
                                          ...current,
                                          cover_media_id: event.target.value || null,
                                        }
                                      : current,
                                  )
                                }
                              >
                                {workingReelDraft.assets.map((asset) => (
                                  <option key={`cover-option-${asset.media_id}`} value={asset.media_id}>
                                    {asset.original_filename}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="meta-card reel-draft-card">
                              <strong>Audio</strong>
                              <span>{workingReelDraft.audio_strategy}</span>
                            </div>
                            <div className="meta-card reel-draft-card">
                              <strong>Video strategy</strong>
                              <span>{formatVideoStrategy(workingReelDraft.video_strategy)}</span>
                            </div>
                            <div className="meta-card reel-draft-card">
                              <strong>Length</strong>
                              <span>{formatDuration(workingReelDraft.estimated_total_duration_seconds)}</span>
                            </div>
                            <div className="ai-card ai-card-wide">
                              <strong>Caption preview</strong>
                              <textarea
                                className="textarea draft-textarea"
                                value={workingReelDraft.caption}
                                onChange={(event) =>
                                  setEditableReelDraft((current) =>
                                    current
                                      ? {
                                          ...current,
                                          caption: event.target.value,
                                        }
                                      : current,
                                  )
                                }
                              />
                            </div>
                            {isReelDraftDirty ? (
                              <div className="ai-inline-note ai-card-wide">
                                <strong>Draft edits pending</strong>
                                <span>
                                  The step list below is edited locally. Apply the draft edits or render directly to rebuild the
                                  render spec from these changes.
                                </span>
                              </div>
                            ) : null}
                            <div className="ai-card ai-card-wide">
                              <strong>Draft assets</strong>
                              <div className="candidate-list">
                                {workingReelDraft.assets.map((asset) => (
                                  <div className="candidate-row" key={`draft-asset-${asset.media_id}`}>
                                    <div>
                                      <strong>{asset.original_filename}</strong>
                                      <span>
                                        {asset.media_kind} • {asset.content_type}
                                      </span>
                                    </div>
                                    <em>{formatDraftAssetStatus(asset)}</em>
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div className="ai-card ai-card-wide">
                              <strong>Draft steps</strong>
                              <div className="draft-step-list">
                                {workingReelDraft.steps.map((step, stepIndex) => {
                                  const stepMediaItem = getWorkflowMediaItem(step.media_id);
                                  const videoStepLimits =
                                    step.media_kind === "video"
                                      ? getEditableVideoStepLimits(
                                          step,
                                          stepMediaItem,
                                          maxReelClipDurationSeconds,
                                        )
                                      : null;

                                  return (
                                  <div className="draft-step-editor" key={`draft-step-${step.step_number}-${step.media_id}`}>
                                    <div className="draft-step-header">
                                      <div>
                                        <span className="reel-plan-index">Step {stepIndex + 1}</span>
                                        <strong>
                                          {step.role}: {step.original_filename}
                                        </strong>
                                      </div>
                                      <div className="actions">
                                        <button
                                          className="button-secondary button-chip"
                                          disabled={stepIndex === 0}
                                          onClick={() => moveEditableReelStep(stepIndex, -1)}
                                          type="button"
                                        >
                                          Move up
                                        </button>
                                        <button
                                          className="button-secondary button-chip"
                                          disabled={stepIndex === workingReelDraft.steps.length - 1}
                                          onClick={() => moveEditableReelStep(stepIndex, 1)}
                                          type="button"
                                        >
                                          Move down
                                        </button>
                                      </div>
                                    </div>
                                    <div className="draft-step-grid">
                                      <label className="draft-field">
                                        <span>Role</span>
                                        <input
                                          className="input draft-input"
                                          value={step.role}
                                          onChange={(event) => updateEditableReelStepField(stepIndex, "role", event.target.value)}
                                          type="text"
                                        />
                                      </label>
                                      <label className="draft-field">
                                        <span>Asset</span>
                                        <select
                                          className="input draft-input"
                                          value={step.media_id}
                                          onChange={(event) => updateEditableReelStepMedia(stepIndex, event.target.value)}
                                        >
                                          {workflowAlbum.media_items.map((item) => (
                                            <option key={`draft-media-option-${item.id}`} value={item.id}>
                                              {item.original_filename}
                                            </option>
                                          ))}
                                        </select>
                                      </label>
                                      <label className="draft-field">
                                        <span>Duration</span>
                                        <input
                                          className="input draft-input"
                                          value={step.suggested_duration_seconds.toFixed(1)}
                                          onChange={(event) =>
                                            updateEditableReelStepField(stepIndex, "suggested_duration_seconds", event.target.value)
                                          }
                                          max={
                                            step.media_kind === "video"
                                              ? videoStepLimits?.maxStepDurationSeconds.toFixed(1)
                                              : maxReelClipDurationSeconds.toFixed(1)
                                          }
                                          min={step.media_kind === "video" ? "0.3" : "0.5"}
                                          step="0.1"
                                          type="number"
                                        />
                                      </label>
                                      {step.media_kind === "video" ? (
                                        <>
                                          <label className="draft-field">
                                            <span>Clip start</span>
                                            <input
                                              className="input draft-input"
                                              value={step.clip_start_seconds?.toFixed(1) ?? ""}
                                              onChange={(event) =>
                                                updateEditableReelStepField(stepIndex, "clip_start_seconds", event.target.value)
                                              }
                                              min="0"
                                              max={videoStepLimits?.maxClipStartSeconds.toFixed(1)}
                                              step="0.1"
                                              type="number"
                                            />
                                          </label>
                                          <label className="draft-field">
                                            <span>Clip end</span>
                                            <input
                                              className="input draft-input"
                                              value={step.clip_end_seconds?.toFixed(1) ?? ""}
                                              onChange={(event) =>
                                                updateEditableReelStepField(stepIndex, "clip_end_seconds", event.target.value)
                                              }
                                              min={
                                                step.clip_start_seconds !== null
                                                  ? roundToTenth(step.clip_start_seconds + 0.3).toFixed(1)
                                                  : "0.3"
                                              }
                                              max={videoStepLimits?.maxClipEndSeconds.toFixed(1)}
                                              step="0.1"
                                              type="number"
                                            />
                                          </label>
                                        </>
                                      ) : null}
                                    </div>
                                    <div className="draft-step-meta">
                                      <span>
                                        {formatSourceRole(step.source_role)}
                                        {step.selection_mode === "video_clip"
                                          ? ` • ${formatClipWindow(step.clip_start_seconds, step.clip_end_seconds)}`
                                          : ""}
                                      </span>
                                      <em>{formatDuration(step.suggested_duration_seconds)}</em>
                                    </div>
                                  </div>
                                  );
                                })}
                              </div>
                            </div>
                            {renderSpec ? (
                              <div className="ai-card ai-card-wide">
                                <div className="reel-plan-header">
                                  <div>
                                    <strong>Render spec</strong>
                                    <p>
                                      {renderSpec.backend_available
                                        ? `${renderSpec.backend} is available locally.`
                                        : `${renderSpec.backend} commands are ready, but the binary is not installed on this machine.`}
                                    </p>
                                  </div>
                                </div>
                                <div className="reel-draft-grid">
                                  <div className="meta-card reel-draft-card">
                                    <strong>Backend</strong>
                                    <span>{renderSpec.backend}</span>
                                  </div>
                                  <div className="meta-card reel-draft-card">
                                    <strong>Run from</strong>
                                    <span>{renderSpec.working_directory}</span>
                                  </div>
                                  <div className="meta-card reel-draft-card">
                                    <strong>Output file</strong>
                                    <span>{renderSpec.output_relative_path}</span>
                                  </div>
                                  <div className="meta-card reel-draft-card">
                                    <strong>Concat file</strong>
                                    <span>{renderSpec.concat_relative_path}</span>
                                  </div>
                                </div>
                                {!renderBackendAvailable ? (
                                  <div className="render-note-list">
                                    <div className="render-note">
                                      Install `ffmpeg` locally to enable the `Render reel` button and generate a final preview video in this app.
                                    </div>
                                  </div>
                                ) : null}
                                {isReelDraftDirty ? (
                                  <div className="render-note-list">
                                    <div className="render-note">
                                      Render spec details below reflect the last applied draft. Save edits or render directly to rebuild them
                                      from your current step changes.
                                    </div>
                                  </div>
                                ) : null}
                                {renderSpec.notes.length ? (
                                  <div className="render-note-list">
                                    {renderSpec.notes.map((note) => (
                                      <div className="render-note" key={note}>
                                        {note}
                                      </div>
                                    ))}
                                  </div>
                                ) : null}
                                <div className="candidate-list">
                                  {renderSpec.clips.map((clip) => (
                                    <div className="candidate-row" key={`render-clip-${clip.step_number}-${clip.media_id}`}>
                                      <div>
                                        <strong>
                                          Step {clip.step_number}: {clip.role} - {clip.original_filename}
                                        </strong>
                                        <span>
                                          {formatRenderMode(clip.render_mode)}
                                          {clip.media_kind === "video"
                                            ? ` • ${formatClipWindow(clip.clip_start_seconds, clip.clip_end_seconds)}`
                                            : ""}
                                        </span>
                                        <span>
                                          output: {clip.output_relative_path}
                                        </span>
                                      </div>
                                      <em>{formatDuration(clip.output_duration_seconds)}</em>
                                    </div>
                                  ))}
                                </div>
                                <details className="command-details">
                                  <summary>Shell commands</summary>
                                  <pre className="command-block">{renderSpec.shell_commands.join("\n")}</pre>
                                </details>
                              </div>
                            ) : null}
                            {workflowAlbum?.rendered_reel ? (
                              <div className="ai-card ai-card-wide">
                                <div className="reel-plan-header">
                                  <div>
                                    <strong>Rendered reel</strong>
                                    <p>
                                      Ready at {formatDate(workflowAlbum.rendered_reel.rendered_at)} •{" "}
                                      {workflowAlbum.rendered_reel.output_width}x{workflowAlbum.rendered_reel.output_height} •{" "}
                                      {workflowAlbum.rendered_reel.fps} fps •{" "}
                                      {formatDuration(workflowAlbum.rendered_reel.estimated_total_duration_seconds)}
                                    </p>
                                  </div>
                                  <div className="actions">
                                    <button className="button-primary" onClick={handleDownloadRenderedReel} type="button">
                                      Download rendered reel
                                    </button>
                                  </div>
                                </div>
                                <div className="render-preview">
                                  {renderedReelContentUrl ? (
                                    <video
                                      key={renderedReelContentUrl}
                                      controls
                                      preload="metadata"
                                      src={renderedReelContentUrl}
                                    />
                                  ) : null}
                                </div>
                                <p className="render-preview-meta">
                                  {formatBytes(workflowAlbum.rendered_reel.file_size_bytes)} •{" "}
                                  {formatVideoStrategy(workflowAlbum.rendered_reel.video_strategy)}
                                </p>
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <p>No reel draft available yet.</p>
                        )}
                      </div>
                      <div className="ai-card ai-card-wide">
                        <strong>Shot groups</strong>
                        {activeSuggestions.shot_groups.length > 0 ? (
                          <div className="candidate-list">
                            {activeSuggestions.shot_groups.map((group) => (
                              <div className="candidate-row" key={group.group_id}>
                                <div>
                                  <strong>{group.label}</strong>
                                  <span>
                                    {group.item_count} item(s), pick: {getMediaLabel(group.picked_media_id)}
                                  </span>
                                </div>
                                <em>{group.group_id}</em>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p>No duplicate-style groups detected yet.</p>
                        )}
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
                          <img alt="" aria-hidden="true" src={mediaUrl} />
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
                          {item.analysis_frame_count > 0 ? (
                            <div className="meta-card">
                              <strong>AI video frames</strong>
                              <span>{item.analysis_frame_count} sampled</span>
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
