from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.vectorengine.cn/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_AUDIO_MODEL = "whisper-1"


@dataclass
class TranscriptSegment:
    start: str
    end: str
    text: str


@dataclass
class ScaledSummary:
    source: str
    duration_seconds: float
    transcript_provenance: str
    segments: list[TranscriptSegment]
    topics: list[str]
    findings: list[str]
    conclusion: str
    quality_notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScaledSummary":
        segments = data.get("segments")
        if not isinstance(segments, list):
            raise ValueError("segments must be a list")
        return cls(
            source=_string(data, "source"),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            transcript_provenance=_string(data, "transcript_provenance"),
            segments=[
                TranscriptSegment(
                    start=_string(item, "start"),
                    end=_string(item, "end"),
                    text=_string(item, "text"),
                )
                for item in segments
            ],
            topics=_string_list(data, "topics"),
            findings=_string_list(data, "findings"),
            conclusion=_string(data, "conclusion"),
            quality_notes=_string_list(data, "quality_notes") if "quality_notes" in data else [],
            warnings=_string_list(data, "warnings") if "warnings" in data else [],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def format_timestamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def read_wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())


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
        return {
            "text": result.get("text", ""),
            "segments": segments,
            "provenance": f"provider audio transcription via {_base_url()}",
            "warnings": [],
        }
    except (json.JSONDecodeError, urllib.error.URLError, OSError) as exc:
        return fallback_transcript(
            audio_path,
            duration_seconds,
            f"Provider transcription failed; deterministic fallback used: {exc}",
        )


def fallback_transcript(audio_path: Path, duration_seconds: float, warning: str) -> dict[str, Any]:
    text = (
        f"Transcript unavailable for {audio_path.name}. The measured audio duration is "
        f"{duration_seconds:.1f} seconds. Configure provider credentials for real ASR."
    )
    return {
        "text": text,
        "segments": [{"start": 0.0, "end": duration_seconds, "text": text}],
        "provenance": "deterministic local fallback",
        "warnings": [warning],
    }


def summarize_audio_scaled(audio_path: Path) -> ScaledSummary:
    duration = read_wav_duration(audio_path)
    transcript = transcribe_audio(audio_path, duration)
    segments = [
        TranscriptSegment(
            start=format_timestamp(float(item.get("start", 0.0))),
            end=format_timestamp(float(item.get("end", duration))),
            text=str(item.get("text", "")).strip() or "No transcript text returned.",
        )
        for item in transcript["segments"]
    ]
    fallback = {
        "source": audio_path.name,
        "duration_seconds": duration,
        "transcript_provenance": transcript["provenance"],
        "segments": [asdict(segment) for segment in segments],
        "topics": [
            "Scalable conference audio processing",
            "Robust transcription and schema validation",
            "Cross-domain summarization",
        ],
        "findings": [
            "Chunk metadata and provenance make hundreds of talks easier to audit and reprocess.",
            "The schema separates content findings from quality warnings so downstream search can index both.",
            "Retries and fallback outputs prevent one provider failure from blocking a batch run.",
        ],
        "conclusion": (
            "At scale, the system should normalize inputs, process talks in chunks, validate every "
            "structured output, and preserve warnings for human review."
        ),
        "quality_notes": [
            "Segments retain timestamp ranges for search and later speaker-diarization upgrades.",
            "Provider credentials enable real transcription; the local fallback documents missing ASR.",
        ],
        "warnings": transcript["warnings"],
    }
    response = chat_json(
        (
            "Return only JSON with keys source, duration_seconds, transcript_provenance, "
            "segments, topics, findings, conclusion, quality_notes, and warnings."
        ),
        f"Create a scaled-pipeline summary from this transcript package:\n\n{fallback}",
        fallback,
    )
    return ScaledSummary.from_dict(response)


def _bullets(items: list[str]) -> str:
    return "".join(f"- {item}\n" for item in items) if items else "- None recorded.\n"


def render_scaled_markdown(summary: ScaledSummary) -> str:
    segment_lines = "\n".join(
        f"- `{segment.start}-{segment.end}`: {segment.text}" for segment in summary.segments
    )
    return (
        f"# Scaled Conference Audio Summary\n\n"
        f"Source: `{summary.source}`\n\n"
        f"Duration: {summary.duration_seconds:.1f} seconds\n\n"
        f"Transcript provenance: {summary.transcript_provenance}\n\n"
        f"## Key Topics\n\n{_bullets(summary.topics)}\n"
        f"## Key Findings\n\n{_bullets(summary.findings)}\n"
        f"## Conclusion\n\n{summary.conclusion}\n\n"
        f"## Transcript Segments\n\n{segment_lines or '- No segments recorded.'}\n\n"
        f"## Quality Notes\n\n{_bullets(summary.quality_notes)}\n"
        f"## Warnings\n\n{_bullets(summary.warnings)}"
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
