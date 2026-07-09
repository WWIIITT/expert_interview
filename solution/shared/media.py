from __future__ import annotations

import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


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


def read_wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return frames / float(rate) if rate else 0.0


def read_mp4_duration(path: Path) -> float:
    data = path.read_bytes()
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        box_type = data[offset + 4 : offset + 8]
        if size == 1 and offset + 16 <= len(data):
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        else:
            header = 8
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
    if version == 1 and start + 28 <= len(data):
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
    command = [
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
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return False, result.stderr.strip() or "ffmpeg audio extraction failed"
    return True, "audio extracted with imageio-ffmpeg"


def detect_slide_ranges(
    video_path: Path,
    threshold: float = 28.0,
    min_slide_seconds: float = 4.0,
    sample_every_seconds: float = 1.0,
) -> list[SlideRange]:
    duration = read_mp4_duration(video_path)
    fallback_duration = duration if duration > 0 else 1.0
    try:
        import cv2
    except ImportError:
        return [
            SlideRange(
                0.0,
                fallback_duration,
                "opencv-python-headless is not installed; treated the video as one slide.",
            )
        ]

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return [SlideRange(0.0, fallback_duration, "OpenCV could not open the video.")]

    fps = capture.get(cv2.CAP_PROP_FPS) or 1.0
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    detected_duration = frame_count / fps if frame_count else fallback_duration
    step = max(1, int(round(fps * sample_every_seconds)))
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

    ranges: list[SlideRange] = []
    for index, start in enumerate(slide_starts):
        end = slide_starts[index + 1] if index + 1 < len(slide_starts) else detected_duration
        if end > start:
            ranges.append(SlideRange(start, end))
    return ranges or [SlideRange(0.0, fallback_duration, "No readable frames were found.")]


def temporary_wav_path() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.close()
    return Path(handle.name)
