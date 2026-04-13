from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import struct
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUPPORTED_ISO_VIDEO_EXTENSIONS = {".m4v", ".mov", ".mp4", ".qt"}
SUPPORTED_ISO_VIDEO_CONTENT_TYPES = {
    "application/mp4",
    "video/mp4",
    "video/quicktime",
    "video/x-m4v",
}


def build_media_metadata(
    *,
    filename: str,
    content_type: str | None,
    payload: bytes,
) -> dict[str, Any]:
    detected_content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    media_kind = _classify_media_kind(detected_content_type)
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    frame_rate: float | None = None
    video_codec: str | None = None
    captured_at: str | None = None
    source_device: str | None = None
    gps: dict[str, Any] | None = None
    metadata_source = "basic"

    if media_kind == "image":
        width, height = _extract_image_dimensions(payload)
        image_embedded_metadata = _extract_image_embedded_metadata(payload)
        captured_at = image_embedded_metadata.get("captured_at")
        source_device = image_embedded_metadata.get("source_device")
        gps = image_embedded_metadata.get("gps")
        metadata_source = _compose_metadata_source(
            "image_headers" if width and height else "image_basic",
            image_embedded_metadata.get("metadata_source"),
        )
    elif media_kind == "video":
        video_metadata = _extract_video_metadata(
            filename=filename,
            content_type=detected_content_type,
            payload=payload,
        )
        width = video_metadata.get("width")
        height = video_metadata.get("height")
        duration_seconds = video_metadata.get("duration_seconds")
        frame_rate = video_metadata.get("frame_rate")
        video_codec = video_metadata.get("video_codec")
        metadata_source = video_metadata.get("metadata_source", "video_basic")

    media_score, media_score_label = _build_media_score(
        media_kind=media_kind,
        content_type=detected_content_type,
        file_size_bytes=len(payload),
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        frame_rate=frame_rate,
    )

    return {
        "media_kind": media_kind,
        "file_size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "file_extension": Path(filename).suffix.lower(),
        "captured_at": captured_at,
        "source_device": source_device,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds,
        "frame_rate": frame_rate,
        "video_codec": video_codec,
        "gps": gps,
        "metadata_source": metadata_source,
        "thumbnail_relative_path": None,
        "thumbnail_content_type": None,
        "media_score": media_score,
        "media_score_label": media_score_label,
        "detected_at": datetime.now(UTC).isoformat(),
    }


def enrich_saved_media_metadata(media_item: dict[str, Any]) -> dict[str, Any]:
    video_path = Path(media_item.get("stored_path", ""))
    if not video_path.exists():
        return {}

    payload = video_path.read_bytes()
    base_metadata = build_media_metadata(
        filename=str(media_item.get("original_filename") or media_item.get("stored_filename") or video_path.name),
        content_type=str(media_item.get("content_type") or "application/octet-stream"),
        payload=payload,
    )
    updates: dict[str, Any] = {
        key: base_metadata.get(key)
        for key in {
            "file_size_bytes",
            "sha256",
            "file_extension",
            "captured_at",
            "source_device",
            "width",
            "height",
            "duration_seconds",
            "frame_rate",
            "video_codec",
            "gps",
            "metadata_source",
            "media_score",
            "media_score_label",
        }
    }

    if media_item.get("media_kind") == "video":
        ffprobe_metadata = _extract_video_metadata_with_ffprobe(video_path)
        if ffprobe_metadata:
            updates.update(ffprobe_metadata)

        thumbnail_metadata = _generate_video_thumbnail(
            video_path=video_path,
            stored_filename=str(media_item.get("stored_filename", "")),
            storage_root=_resolve_storage_root_from_path(video_path),
        )
        if thumbnail_metadata:
            updates.update(thumbnail_metadata)

    merged_item = {**media_item, **updates}
    media_score, media_score_label = _build_media_score(
        media_kind=str(merged_item.get("media_kind", "unknown")),
        content_type=str(merged_item.get("content_type", "application/octet-stream")),
        file_size_bytes=int(merged_item.get("file_size_bytes") or 0),
        width=_coerce_int(merged_item.get("width")),
        height=_coerce_int(merged_item.get("height")),
        duration_seconds=_coerce_float(merged_item.get("duration_seconds")),
        frame_rate=_coerce_float(merged_item.get("frame_rate")),
    )
    updates["media_score"] = media_score
    updates["media_score_label"] = media_score_label

    if not updates.get("metadata_source") and not merged_item.get("metadata_source"):
        updates["metadata_source"] = "video_basic"

    return updates


def get_media_tooling_status() -> dict[str, bool]:
    return {
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "ffprobe_available": shutil.which("ffprobe") is not None,
        "iso_video_parser_available": True,
    }


def _classify_media_kind(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    return "unknown"


def _extract_image_dimensions(payload: bytes) -> tuple[int | None, int | None]:
    if len(payload) < 24:
        return None, None

    png_signature = b"\x89PNG\r\n\x1a\n"
    if payload.startswith(png_signature):
        width, height = struct.unpack(">II", payload[16:24])
        return int(width), int(height)

    if payload[:3] == b"GIF":
        width, height = struct.unpack("<HH", payload[6:10])
        return int(width), int(height)

    if payload[:2] == b"\xff\xd8":
        return _extract_jpeg_dimensions(payload)

    return None, None


def _extract_image_embedded_metadata(payload: bytes) -> dict[str, Any]:
    if payload[:2] != b"\xff\xd8":
        return {}

    exif_payload = _extract_jpeg_exif_payload(payload)
    if exif_payload is None:
        return {}

    return _parse_tiff_exif_payload(exif_payload)


def _extract_jpeg_exif_payload(payload: bytes) -> memoryview | None:
    index = 2
    payload_length = len(payload)

    while index < payload_length:
        if payload[index] != 0xFF:
            index += 1
            continue

        while index < payload_length and payload[index] == 0xFF:
            index += 1

        if index >= payload_length:
            break

        marker = payload[index]
        index += 1

        if marker in {0xD8, 0xD9}:
            continue

        if index + 1 >= payload_length:
            break

        segment_length = struct.unpack(">H", payload[index : index + 2])[0]
        segment_start = index + 2
        segment_end = index + segment_length
        if segment_length < 2 or segment_end > payload_length:
            break

        if marker == 0xE1 and payload[segment_start : segment_start + 6] == b"Exif\x00\x00":
            return memoryview(payload[segment_start + 6 : segment_end])

        index += segment_length

    return None


def _parse_tiff_exif_payload(payload: memoryview) -> dict[str, Any]:
    if len(payload) < 8:
        return {}

    byte_order_marker = bytes(payload[:2])
    if byte_order_marker == b"II":
        endian = "little"
    elif byte_order_marker == b"MM":
        endian = "big"
    else:
        return {}

    magic = int.from_bytes(payload[2:4], endian)
    if magic != 42:
        return {}

    first_ifd_offset = int.from_bytes(payload[4:8], endian)
    root_ifd = _parse_tiff_ifd(payload, first_ifd_offset, endian)
    if not root_ifd:
        return {}

    exif_ifd = _parse_tiff_ifd(payload, _coerce_int(root_ifd.get(0x8769)), endian)
    gps_ifd = _parse_tiff_ifd(payload, _coerce_int(root_ifd.get(0x8825)), endian)

    make = _coerce_text(root_ifd.get(0x010F))
    model = _coerce_text(root_ifd.get(0x0110))
    source_device = " ".join(part for part in [make, model] if part) or None

    captured_at = _normalize_exif_datetime(
        _coerce_text(exif_ifd.get(0x9003))
        or _coerce_text(exif_ifd.get(0x9004))
        or _coerce_text(root_ifd.get(0x0132))
    )
    gps = _build_gps_payload(gps_ifd)

    if not any([captured_at, source_device, gps]):
        return {}

    return {
        "captured_at": captured_at,
        "source_device": source_device,
        "gps": gps,
        "metadata_source": "image_exif",
    }


def _parse_tiff_ifd(payload: memoryview, offset: int | None, endian: str) -> dict[int, Any]:
    if offset is None or offset < 0 or offset + 2 > len(payload):
        return {}

    entry_count = int.from_bytes(payload[offset : offset + 2], endian)
    entries_offset = offset + 2
    entries: dict[int, Any] = {}

    for index in range(entry_count):
        entry_offset = entries_offset + index * 12
        if entry_offset + 12 > len(payload):
            break

        tag = int.from_bytes(payload[entry_offset : entry_offset + 2], endian)
        value_type = int.from_bytes(payload[entry_offset + 2 : entry_offset + 4], endian)
        value_count = int.from_bytes(payload[entry_offset + 4 : entry_offset + 8], endian)
        value_or_offset = payload[entry_offset + 8 : entry_offset + 12]
        entries[tag] = _read_tiff_value(
            payload=payload,
            endian=endian,
            value_type=value_type,
            value_count=value_count,
            value_or_offset=value_or_offset,
        )

    return entries


def _read_tiff_value(
    *,
    payload: memoryview,
    endian: str,
    value_type: int,
    value_count: int,
    value_or_offset: memoryview,
) -> Any:
    type_sizes = {
        1: 1,  # BYTE
        2: 1,  # ASCII
        3: 2,  # SHORT
        4: 4,  # LONG
        5: 8,  # RATIONAL
        7: 1,  # UNDEFINED
        9: 4,  # SLONG
        10: 8,  # SRATIONAL
    }
    unit_size = type_sizes.get(value_type)
    if unit_size is None or value_count <= 0:
        return None

    total_size = unit_size * value_count
    if total_size <= 4:
        raw = bytes(value_or_offset[:total_size])
    else:
        data_offset = int.from_bytes(value_or_offset, endian)
        if data_offset < 0 or data_offset + total_size > len(payload):
            return None
        raw = bytes(payload[data_offset : data_offset + total_size])

    if value_type == 2:
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip() or None
    if value_type == 1:
        values = list(raw)
        return values[0] if value_count == 1 else values
    if value_type == 3:
        values = [int.from_bytes(raw[index : index + 2], endian) for index in range(0, len(raw), 2)]
        return values[0] if value_count == 1 else values
    if value_type == 4:
        values = [int.from_bytes(raw[index : index + 4], endian) for index in range(0, len(raw), 4)]
        return values[0] if value_count == 1 else values
    if value_type == 5:
        values = [_read_rational(raw[index : index + 8], endian, signed=False) for index in range(0, len(raw), 8)]
        return values[0] if value_count == 1 else values
    if value_type == 7:
        return raw
    if value_type == 9:
        values = [int.from_bytes(raw[index : index + 4], endian, signed=True) for index in range(0, len(raw), 4)]
        return values[0] if value_count == 1 else values
    if value_type == 10:
        values = [_read_rational(raw[index : index + 8], endian, signed=True) for index in range(0, len(raw), 8)]
        return values[0] if value_count == 1 else values
    return None


def _read_rational(raw: bytes, endian: str, *, signed: bool) -> float | None:
    if len(raw) != 8:
        return None

    numerator = int.from_bytes(raw[:4], endian, signed=signed)
    denominator = int.from_bytes(raw[4:], endian, signed=signed)
    if denominator == 0:
        return None
    return numerator / denominator


def _build_gps_payload(gps_ifd: dict[int, Any]) -> dict[str, Any] | None:
    latitude = _convert_gps_coordinate(gps_ifd.get(2), _coerce_text(gps_ifd.get(1)))
    longitude = _convert_gps_coordinate(gps_ifd.get(4), _coerce_text(gps_ifd.get(3)))
    altitude = _coerce_float(gps_ifd.get(6))
    altitude_ref = _coerce_int(gps_ifd.get(5))

    if altitude is not None and altitude_ref == 1:
        altitude *= -1

    if latitude is None or longitude is None:
        return None

    result: dict[str, Any] = {
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
    }
    if altitude is not None:
        result["altitude_meters"] = round(altitude, 2)
    return result


def _convert_gps_coordinate(value: Any, reference: str | None) -> float | None:
    if not isinstance(value, list) or len(value) < 3:
        return None

    degrees = _coerce_float(value[0])
    minutes = _coerce_float(value[1])
    seconds = _coerce_float(value[2])
    if degrees is None or minutes is None or seconds is None:
        return None

    coordinate = degrees + (minutes / 60) + (seconds / 3600)
    if reference and reference.upper() in {"S", "W"}:
        coordinate *= -1
    return coordinate


def _normalize_exif_datetime(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip()
    for format_string in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, format_string).isoformat()
        except ValueError:
            continue
    return normalized or None


def _compose_metadata_source(*parts: Any) -> str:
    seen: list[str] = []
    for part in parts:
        text = str(part).strip() if part is not None else ""
        if not text or text in seen:
            continue
        seen.append(text)
    return "+".join(seen) if seen else "basic"


def _coerce_text(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value).strip() or None


def _extract_video_metadata(
    *,
    filename: str,
    content_type: str,
    payload: bytes,
) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_ISO_VIDEO_EXTENSIONS and content_type not in SUPPORTED_ISO_VIDEO_CONTENT_TYPES:
        return {"metadata_source": "video_basic"}

    parsed_track = _parse_iso_video_track(memoryview(payload))
    if not parsed_track:
        return {"metadata_source": "video_basic"}

    timescale = _coerce_int(parsed_track.get("timescale"))
    duration_units = _coerce_int(parsed_track.get("duration_units"))
    duration_seconds = None
    if timescale and duration_units and timescale > 0:
        duration_seconds = round(duration_units / timescale, 3)

    sample_count = _coerce_int(parsed_track.get("sample_count"))
    frame_rate = None
    if sample_count and duration_seconds and duration_seconds > 0:
        frame_rate = round(sample_count / duration_seconds, 3)

    return {
        "width": _coerce_int(parsed_track.get("width")),
        "height": _coerce_int(parsed_track.get("height")),
        "duration_seconds": duration_seconds,
        "frame_rate": frame_rate,
        "video_codec": parsed_track.get("video_codec"),
        "metadata_source": "video_mp4_parser",
    }


def _extract_video_metadata_with_ffprobe(video_path: Path) -> dict[str, Any] | None:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        return None

    command = [
        ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    streams = payload.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not isinstance(video_stream, dict):
        return None

    format_data = payload.get("format") or {}
    duration_seconds = _coerce_float(video_stream.get("duration")) or _coerce_float(format_data.get("duration"))
    if duration_seconds is not None:
        duration_seconds = round(duration_seconds, 3)

    return {
        "width": _coerce_int(video_stream.get("width")),
        "height": _coerce_int(video_stream.get("height")),
        "duration_seconds": duration_seconds,
        "frame_rate": _parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        "video_codec": str(video_stream.get("codec_name", "")).strip() or None,
        "metadata_source": "video_ffprobe",
    }


def _generate_video_thumbnail(
    *,
    video_path: Path,
    stored_filename: str,
    storage_root: Path | None,
) -> dict[str, Any] | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None or storage_root is None:
        return None

    thumbnail_path = video_path.with_name(f"{Path(stored_filename).stem}-thumb.jpg")
    if not thumbnail_path.exists():
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(thumbnail_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=45,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0 or not thumbnail_path.exists():
            return None

    return {
        "thumbnail_relative_path": str(thumbnail_path.resolve().relative_to(storage_root)),
        "thumbnail_content_type": "image/jpeg",
    }


def _parse_iso_video_track(payload: memoryview) -> dict[str, Any] | None:
    moov_payload = None
    for atom_type, data_start, data_end in _iter_atoms(payload):
        if atom_type == "moov":
            moov_payload = payload[data_start:data_end]
            break

    if moov_payload is None:
        return None

    for atom_type, data_start, data_end in _iter_atoms(moov_payload):
        if atom_type != "trak":
            continue
        track_info = _parse_iso_track(moov_payload[data_start:data_end])
        if track_info.get("handler_type") == "vide":
            return track_info

    return None


def _parse_iso_track(payload: memoryview) -> dict[str, Any]:
    track_info: dict[str, Any] = {}
    for atom_type, data_start, data_end in _iter_atoms(payload):
        atom_payload = payload[data_start:data_end]
        if atom_type == "tkhd":
            track_info.update(_parse_track_header(atom_payload))
        elif atom_type == "mdia":
            track_info.update(_parse_media_container(atom_payload))
    return track_info


def _parse_media_container(payload: memoryview) -> dict[str, Any]:
    media_info: dict[str, Any] = {}
    for atom_type, data_start, data_end in _iter_atoms(payload):
        atom_payload = payload[data_start:data_end]
        if atom_type == "hdlr":
            media_info["handler_type"] = _parse_handler_reference(atom_payload)
        elif atom_type == "mdhd":
            media_info.update(_parse_media_header(atom_payload))
        elif atom_type == "minf":
            media_info.update(_parse_media_information(atom_payload))
    return media_info


def _parse_media_information(payload: memoryview) -> dict[str, Any]:
    media_info: dict[str, Any] = {}
    for atom_type, data_start, data_end in _iter_atoms(payload):
        if atom_type != "stbl":
            continue
        media_info.update(_parse_sample_table(payload[data_start:data_end]))
    return media_info


def _parse_sample_table(payload: memoryview) -> dict[str, Any]:
    sample_info: dict[str, Any] = {}
    for atom_type, data_start, data_end in _iter_atoms(payload):
        atom_payload = payload[data_start:data_end]
        if atom_type == "stsd":
            sample_info["video_codec"] = _parse_sample_description(atom_payload)
        elif atom_type == "stts":
            sample_info["sample_count"] = _parse_time_to_sample(atom_payload)
        elif atom_type == "stsz" and not sample_info.get("sample_count"):
            sample_info["sample_count"] = _parse_sample_size_table(atom_payload)
    return sample_info


def _parse_track_header(payload: memoryview) -> dict[str, Any]:
    if len(payload) < 8:
        return {}
    return {
        "width": _fixed_point_16_16_to_int(int.from_bytes(payload[-8:-4], "big")),
        "height": _fixed_point_16_16_to_int(int.from_bytes(payload[-4:], "big")),
    }


def _parse_media_header(payload: memoryview) -> dict[str, Any]:
    if len(payload) < 24:
        return {}

    version = payload[0]
    if version == 1:
        if len(payload) < 32:
            return {}
        timescale = int.from_bytes(payload[20:24], "big")
        duration_units = int.from_bytes(payload[24:32], "big")
    else:
        timescale = int.from_bytes(payload[12:16], "big")
        duration_units = int.from_bytes(payload[16:20], "big")

    return {"timescale": timescale, "duration_units": duration_units}


def _parse_handler_reference(payload: memoryview) -> str | None:
    if len(payload) < 12:
        return None
    return bytes(payload[8:12]).decode("latin1", errors="ignore").strip() or None


def _parse_sample_description(payload: memoryview) -> str | None:
    if len(payload) < 16:
        return None
    entry_count = int.from_bytes(payload[4:8], "big")
    if entry_count < 1:
        return None
    return bytes(payload[12:16]).decode("latin1", errors="ignore").strip() or None


def _parse_time_to_sample(payload: memoryview) -> int | None:
    if len(payload) < 8:
        return None
    entry_count = int.from_bytes(payload[4:8], "big")
    offset = 8
    total_sample_count = 0

    for _ in range(entry_count):
        if offset + 8 > len(payload):
            break
        total_sample_count += int.from_bytes(payload[offset : offset + 4], "big")
        offset += 8

    return total_sample_count or None


def _parse_sample_size_table(payload: memoryview) -> int | None:
    if len(payload) < 12:
        return None
    return int.from_bytes(payload[8:12], "big") or None


def _iter_atoms(payload: memoryview):
    offset = 0
    payload_length = len(payload)

    while offset + 8 <= payload_length:
        size = int.from_bytes(payload[offset : offset + 4], "big")
        header_size = 8

        if size == 1:
            if offset + 16 > payload_length:
                return
            size = int.from_bytes(payload[offset + 8 : offset + 16], "big")
            header_size = 16
        elif size == 0:
            size = payload_length - offset

        if size < header_size or offset + size > payload_length:
            return

        atom_type = bytes(payload[offset + 4 : offset + 8]).decode("latin1", errors="ignore")
        yield atom_type, offset + header_size, offset + size
        offset += size


def _build_media_score(
    *,
    media_kind: str,
    content_type: str,
    file_size_bytes: int,
    width: int | None,
    height: int | None,
    duration_seconds: float | None,
    frame_rate: float | None,
) -> tuple[float, str]:
    score = 18.0

    if width and height:
        megapixels = (width * height) / 1_000_000
        score += min(megapixels * 10, 42)
    else:
        score += 4

    if media_kind == "image":
        if file_size_bytes >= 250_000:
            score += 8
        if file_size_bytes >= 1_500_000:
            score += 6
        if content_type in {"image/jpeg", "image/png", "image/webp"}:
            score += 6
    elif media_kind == "video":
        if duration_seconds is not None:
            if duration_seconds <= 60:
                score += 18
            elif duration_seconds <= 180:
                score += 12
            else:
                score += 7
        if frame_rate is not None:
            if 23 <= frame_rate <= 60:
                score += 9
            elif frame_rate >= 15:
                score += 5
        if file_size_bytes >= 3_000_000:
            score += 8
        if content_type in {"video/mp4", "video/quicktime", "video/x-m4v"}:
            score += 5

    score = round(min(score, 100.0), 1)

    if score >= 80:
        label = "strong"
    elif score >= 60:
        label = "good"
    elif score >= 40:
        label = "review"
    else:
        label = "low"

    return score, label


def _fixed_point_16_16_to_int(value: int) -> int | None:
    if value <= 0:
        return None
    return int(round(value / 65536))


def _parse_fraction(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text == "0/0":
        return None

    if "/" in text:
        numerator_text, denominator_text = text.split("/", 1)
        numerator = _coerce_float(numerator_text)
        denominator = _coerce_float(denominator_text)
        if numerator is None or denominator in {None, 0}:
            return None
        return round(numerator / denominator, 3)

    parsed = _coerce_float(text)
    if parsed is None:
        return None
    return round(parsed, 3)


def _resolve_storage_root_from_path(video_path: Path) -> Path | None:
    resolved_path = video_path.resolve()
    parts = resolved_path.parts
    if "albums" not in parts:
        return None

    albums_index = parts.index("albums")
    if albums_index == 0:
        return None

    return Path(*parts[:albums_index])


def _coerce_float(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    try:
        if value in {None, ""}:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_jpeg_dimensions(payload: bytes) -> tuple[int | None, int | None]:
    index = 2
    payload_length = len(payload)

    while index < payload_length:
        if payload[index] != 0xFF:
            index += 1
            continue

        while index < payload_length and payload[index] == 0xFF:
            index += 1

        if index >= payload_length:
            break

        marker = payload[index]
        index += 1

        if marker in {0xD8, 0xD9}:
            continue

        if index + 1 >= payload_length:
            break

        segment_length = struct.unpack(">H", payload[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > payload_length:
            break

        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if index + 7 >= payload_length:
                break
            height = struct.unpack(">H", payload[index + 3 : index + 5])[0]
            width = struct.unpack(">H", payload[index + 5 : index + 7])[0]
            return int(width), int(height)

        index += segment_length

    return None, None
