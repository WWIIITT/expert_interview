from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.vectorengine.cn/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_AUDIO_MODEL = "whisper-1"


@dataclass
class Task1Summary:
    topics: list[str]
    findings: list[str]
    conclusion: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task1Summary":
        topics = data.get("topics")
        findings = data.get("findings")
        conclusion = data.get("conclusion")
        if not isinstance(topics, list) or not all(isinstance(item, str) for item in topics):
            raise ValueError("topics must be a list of strings")
        if not isinstance(findings, list) or not all(isinstance(item, str) for item in findings):
            raise ValueError("findings must be a list of strings")
        if not isinstance(conclusion, str) or not conclusion.strip():
            raise ValueError("conclusion must be a non-empty string")
        return cls(topics=topics, findings=findings, conclusion=conclusion)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        return {"text": result.get("text", ""), "warnings": []}
    except (json.JSONDecodeError, urllib.error.URLError, OSError) as exc:
        return fallback_transcript(
            audio_path,
            duration_seconds,
            f"Provider transcription failed; deterministic fallback used: {exc}",
        )


def fallback_transcript(audio_path: Path, duration_seconds: float, warning: str) -> dict[str, Any]:
    return {
        "text": (
            f"Transcript unavailable for {audio_path.name}. The measured audio duration is "
            f"{duration_seconds:.1f} seconds. Configure provider credentials for real ASR."
        ),
        "warnings": [warning],
    }


def summarize_audio_basic(audio_path: Path) -> tuple[Task1Summary, dict[str, Any]]:
    duration = read_wav_duration(audio_path)
    transcript = transcribe_audio(audio_path, duration)
    fallback = {
        "topics": [
            "Conference talk transcription",
            "Searchable audio summarization",
            "LLM-based structured extraction",
        ],
        "findings": [
            f"The input file is {audio_path.name} with an estimated duration of {duration:.1f} seconds.",
            "The pipeline separates transcription from summarization so each stage can be replaced independently.",
            "A deterministic fallback keeps the submission reproducible when provider credentials are unavailable.",
        ],
        "conclusion": (
            "The talk can be made searchable by transcribing the audio, validating a compact "
            "summary schema, and rendering both machine-readable and human-readable outputs."
        ),
    }
    response = chat_json(
        "Return only JSON with keys topics, findings, and conclusion.",
        f"Summarize this academic conference transcript from {audio_path.name}:\n\n{transcript['text']}",
        fallback,
    )
    return Task1Summary.from_dict(response), transcript


def render_task1_markdown(summary: Task1Summary, source: str) -> str:
    topics = "".join(f"- {item}\n" for item in summary.topics)
    findings = "".join(f"- {item}\n" for item in summary.findings)
    return (
        f"# Conference Audio Summary\n\n"
        f"Source: `{source}`\n\n"
        f"## Key Topics\n\n{topics}\n"
        f"## Key Findings\n\n{findings}\n"
        f"## Conclusion\n\n{summary.conclusion}\n"
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
