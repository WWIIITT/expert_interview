from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Type, TypeVar


T = TypeVar("T")


def _require_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


@dataclass
class Task1Summary:
    topics: list[str]
    findings: list[str]
    conclusion: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task1Summary":
        return cls(
            topics=_require_string_list(data, "topics"),
            findings=_require_string_list(data, "findings"),
            conclusion=_require_string(data, "conclusion"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSegment:
    start: str
    end: str
    text: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptSegment":
        return cls(
            start=_require_string(data, "start"),
            end=_require_string(data, "end"),
            text=_require_string(data, "text"),
        )


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
            source=_require_string(data, "source"),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            transcript_provenance=_require_string(data, "transcript_provenance"),
            segments=[TranscriptSegment.from_dict(item) for item in segments],
            topics=_require_string_list(data, "topics"),
            findings=_require_string_list(data, "findings"),
            conclusion=_require_string(data, "conclusion"),
            quality_notes=_require_string_list(data, "quality_notes")
            if "quality_notes" in data
            else [],
            warnings=_require_string_list(data, "warnings") if "warnings" in data else [],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Slide:
    slide_number: int
    start: str
    end: str
    slide_summary: str
    speaker_notes: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Slide":
        slide_number = data.get("slide_number")
        if not isinstance(slide_number, int) or slide_number < 1:
            raise ValueError("slide_number must be a positive integer")
        return cls(
            slide_number=slide_number,
            start=_require_string(data, "start"),
            end=_require_string(data, "end"),
            slide_summary=_require_string(data, "slide_summary"),
            speaker_notes=_require_string(data, "speaker_notes"),
        )


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
        parsed_slides = [Slide.from_dict(item) for item in slides]
        if total_slides != len(parsed_slides):
            raise ValueError("total_slides must match the number of slides")
        return cls(total_slides=total_slides, slides=parsed_slides)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_json_file(path: Path, schema: Type[T]) -> T:
    data = json.loads(path.read_text(encoding="utf-8"))
    return schema.from_dict(data)  # type: ignore[attr-defined]


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
