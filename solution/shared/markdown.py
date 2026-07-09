from __future__ import annotations

from .schemas import ScaledSummary, SlideReport, Task1Summary


def _bullets(items: list[str]) -> str:
    if not items:
        return "- None recorded.\n"
    return "".join(f"- {item}\n" for item in items)


def render_task1_markdown(summary: Task1Summary, source: str) -> str:
    return (
        f"# Conference Audio Summary\n\n"
        f"Source: `{source}`\n\n"
        f"## Key Topics\n\n{_bullets(summary.topics)}\n"
        f"## Key Findings\n\n{_bullets(summary.findings)}\n"
        f"## Conclusion\n\n{summary.conclusion}\n"
    )


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
