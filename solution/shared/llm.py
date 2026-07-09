from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.vectorengine.cn/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_AUDIO_MODEL = "whisper-1"


def _base_url() -> str:
    return os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _api_key() -> str:
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")


def chat_json(
    system_prompt: str,
    user_prompt: str,
    fallback: dict[str, Any],
    max_retries: int = 2,
) -> dict[str, Any]:
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
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_error = ""
    for _ in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, json.JSONDecodeError, urllib.error.URLError) as exc:
            last_error = str(exc)

    enriched = dict(fallback)
    warnings = enriched.setdefault("warnings", [])
    if isinstance(warnings, list):
        warnings.append(f"LLM request failed; deterministic fallback used: {last_error}")
    return enriched


def transcribe_audio(audio_path: Path, duration_seconds: float) -> dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        return fallback_transcript(audio_path, duration_seconds, "No LLM_API_KEY was set.")

    boundary = f"----codex-{uuid.uuid4().hex}"
    fields = {
        "model": os.getenv("ASR_MODEL", DEFAULT_AUDIO_MODEL),
        "response_format": "verbose_json",
    }
    body = bytearray()
    for name, value in fields.items():
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
        text = result.get("text", "")
        segments = result.get("segments")
        if not isinstance(segments, list):
            segments = [{"start": 0.0, "end": duration_seconds, "text": text}]
        return {
            "text": text,
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
        f"Transcript unavailable for {audio_path.name}. The pipeline measured an audio "
        f"duration of {duration_seconds:.1f} seconds and preserved the source for "
        "provider-based transcription when credentials are configured."
    )
    return {
        "text": text,
        "segments": [{"start": 0.0, "end": duration_seconds, "text": text}],
        "provenance": "deterministic local fallback",
        "warnings": [warning],
    }
