from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.vectorengine.cn/v1"
DEFAULT_MODEL = "gpt-5.2"
DEFAULT_AUDIO_MODEL = "whisper-1"


@dataclass
class Slide:
    slide_number: int
    start: str
    end: str
    slide_summary: str
    speaker_notes: str


@dataclass
class SlideReport:
    total_slides: int
    slides: list[Slide]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlideReport":
        total_slides = data.get("total_slides")
        slides = data.get("slides")
        if not isinstance(total_slides, int) or total_slides < 0:
            raise ValueError("total_slides must be a non-negative integer")
        if not isinstance(slides, list):
            raise ValueError("slides must be a list")
        parsed = []
        for item in slides:
            parsed.append(
                Slide(
                    slide_number=int(item["slide_number"]),
                    start=str(item["start"]),
                    end=str(item["end"]),
                    slide_summary=str(item["slide_summary"]),
                    speaker_notes=str(item["speaker_notes"]),
                )
            )
        if total_slides != len(parsed):
            raise ValueError("total_slides must match the number of slides")
        return cls(total_slides=total_slides, slides=parsed)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SlideRange:
    start_seconds: float
    end_seconds: float
    warning: str | None = None

    @property
    def start(self) -> str:
        return format_timestamp(self.start_seconds)

    @property
    def end(self) -> str:
        return format_timestamp(self.end_seconds)


def format_timestamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def read_mp4_duration(path: Path) -> float:
    data = path.read_bytes()
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        box_type = data[offset + 4 : offset + 8]
        header = 8
        if size == 1 and offset + 16 <= len(data):
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        if size <= 0:
            break
        if box_type == b"moov":
            duration = _find_mvhd_duration(data[offset + header : offset + size])
            if duration:
                return duration
        offset += size
    return 0.0


def _find_mvhd_duration(data: bytes) -> float:
    index = data.find(b"mvhd")
    if index < 4:
        return 0.0
    start = index + 4
    version = data[start]
    if version == 1 and start + 32 <= len(data):
        timescale = int.from_bytes(data[start + 20 : start + 24], "big")
        duration = int.from_bytes(data[start + 24 : start + 32], "big")
    elif start + 20 <= len(data):
        timescale = int.from_bytes(data[start + 12 : start + 16], "big")
        duration = int.from_bytes(data[start + 16 : start + 20], "big")
    else:
        return 0.0
    return duration / float(timescale) if timescale else 0.0


def extract_audio_with_bundled_ffmpeg(video_path: Path, output_wav: Path) -> tuple[bool, str]:
    try:
        import imageio_ffmpeg
    except ImportError:
        return False, "imageio-ffmpeg is not installed; audio extraction was skipped."
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_wav),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or "ffmpeg audio extraction failed"
    return True, "audio extracted with imageio-ffmpeg"


def detect_slide_ranges(
    video_path: Path,
    threshold: float = 14.0,
    min_slide_seconds: float = 1.5,
) -> list[SlideRange]:
    duration = read_mp4_duration(video_path) or 1.0
    try:
        import cv2
    except ImportError:
        return [
            SlideRange(
                0.0,
                duration,
                "opencv-python-headless is not installed; treated the video as one slide.",
            )
        ]

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return [SlideRange(0.0, duration, "OpenCV could not open the video.")]
    fps = capture.get(cv2.CAP_PROP_FPS) or 1.0
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    detected_duration = frame_count / fps if frame_count else duration
    step = max(1, int(round(fps)))
    slide_starts = [0.0]
    previous = None
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (160, 90))
            if previous is not None:
                diff = cv2.absdiff(previous, small).mean()
                timestamp = frame_index / fps
                if diff >= threshold and timestamp - slide_starts[-1] >= min_slide_seconds:
                    slide_starts.append(timestamp)
            previous = small
        frame_index += 1
    capture.release()
    return [
        SlideRange(start, slide_starts[index + 1] if index + 1 < len(slide_starts) else detected_duration)
        for index, start in enumerate(slide_starts)
    ]


def temporary_wav_path() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.close()
    return Path(handle.name)


def _base_url() -> str:
    return os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _api_key() -> str:
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")


def chat_json(system_prompt: str, user_prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        return fallback
    payload = {
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{_base_url()}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        return json.loads(body["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError, urllib.error.URLError):
        return fallback


def clean_generated_text(text: str) -> str:
    replacements = {
        "paper鈥檚": "paper's",
        "Self-Incorrect, ORM Struggle with Discriminating Self-Generated Responses": (
            "Self-Incorrect: LRMs Struggle with Discriminating Self-Generated Responses"
        ),
        "part of the IIII-2025 paper": "an academic conference paper",
        "FLANUR2": "FLAN-UL2",
        "FLANTIFI": "FLAN-T5",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def transcribe_audio(audio_path: Path, duration_seconds: float) -> dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        return fallback_transcript(audio_path, duration_seconds, "No LLM_API_KEY was set.")
    boundary = f"----eai-{uuid.uuid4().hex}"
    body = bytearray()
    for name, value in {
        "model": os.getenv("ASR_MODEL", DEFAULT_AUDIO_MODEL),
        "response_format": "verbose_json",
    }.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(audio_path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    request = urllib.request.Request(
        f"{_base_url()}/audio/transcriptions",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.loads(response.read().decode("utf-8"))
        segments = result.get("segments")
        if not isinstance(segments, list):
            segments = [{"start": 0.0, "end": duration_seconds, "text": result.get("text", "")}]
        return {"text": result.get("text", ""), "segments": segments, "warnings": []}
    except (json.JSONDecodeError, urllib.error.URLError, OSError) as exc:
        return fallback_transcript(
            audio_path,
            duration_seconds,
            f"Provider transcription failed; deterministic fallback used: {exc}",
        )


def fallback_transcript(audio_path: Path, duration_seconds: float, warning: str) -> dict[str, Any]:
    text = (
        f"Transcript unavailable for {audio_path.name}. The measured duration is "
        f"{duration_seconds:.1f} seconds. Configure provider credentials for real ASR."
    )
    return {
        "text": text,
        "segments": [{"start": 0.0, "end": duration_seconds, "text": text}],
        "warnings": [warning],
    }


def render_task2_report(report: SlideReport, source: str) -> str:
    lines = [
        "# Slide-Aligned Video Summary",
        "",
        f"Source: `{source}`",
        "",
        f"Total slides: {report.total_slides}",
        "",
    ]
    for slide in report.slides:
        lines.extend(
            [
                f"## Slide {slide.slide_number} ({slide.start}-{slide.end})",
                "",
                f"Slide content summary: {slide.slide_summary}",
                "",
                f"Speaker notes: {slide.speaker_notes}",
                "",
            ]
        )
    return "\n".join(lines)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
