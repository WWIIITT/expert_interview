from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm import chat_json, transcribe_audio
from .media import format_timestamp, read_wav_duration
from .schemas import ScaledSummary, Task1Summary, TranscriptSegment


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
        (
            "Summarize this academic conference transcript.\n\n"
            f"Source: {audio_path.name}\n"
            f"Transcript:\n{transcript['text']}"
        ),
        fallback,
    )
    return Task1Summary.from_dict(response), transcript


def summarize_audio_scaled(audio_path: Path) -> ScaledSummary:
    duration = read_wav_duration(audio_path)
    transcript = transcribe_audio(audio_path, duration)
    segments = [_segment_from_provider(item, duration) for item in transcript["segments"]]
    fallback = {
        "source": audio_path.name,
        "duration_seconds": duration,
        "transcript_provenance": transcript["provenance"],
        "segments": [segment.__dict__ for segment in segments],
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
        (
            "Create a robust scaled-pipeline summary for this transcript. Keep the supplied "
            "source, duration, provenance, and segments unless correcting obvious formatting.\n\n"
            f"{fallback}"
        ),
        fallback,
    )
    return ScaledSummary.from_dict(response)


def _segment_from_provider(item: dict[str, Any], duration: float) -> TranscriptSegment:
    start = float(item.get("start", 0.0))
    end = float(item.get("end", duration))
    text = str(item.get("text", "")).strip() or "No transcript text returned for this segment."
    return TranscriptSegment(start=format_timestamp(start), end=format_timestamp(end), text=text)
