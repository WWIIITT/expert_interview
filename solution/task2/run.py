from __future__ import annotations

import argparse
from pathlib import Path

from pipeline import (
    SlideReport,
    chat_json,
    clean_generated_text,
    detect_slide_ranges,
    extract_audio_with_bundled_ffmpeg,
    format_timestamp,
    read_mp4_duration,
    render_task2_report,
    temporary_wav_path,
    transcribe_audio,
    write_json,
)


def _segment_text_for_range(transcript: dict, start_seconds: float, end_seconds: float) -> str:
    pieces: list[str] = []
    for segment in transcript.get("segments", []):
        segment_start = float(segment.get("start", 0.0))
        segment_end = float(segment.get("end", end_seconds))
        if segment_end >= start_seconds and segment_start <= end_seconds:
            text = str(segment.get("text", "")).strip()
            if text:
                pieces.append(text)
    return " ".join(pieces).strip() or str(transcript.get("text", "")).strip()


def build_slide_report(video_path: Path) -> SlideReport:
    duration = read_mp4_duration(video_path)
    ranges = detect_slide_ranges(video_path)
    audio_path = temporary_wav_path()
    extracted, extraction_message = extract_audio_with_bundled_ffmpeg(video_path, audio_path)
    transcript = (
        transcribe_audio(audio_path, duration)
        if extracted
        else {
            "text": f"Audio extraction unavailable for {video_path.name}: {extraction_message}",
            "segments": [
                {
                    "start": 0.0,
                    "end": duration,
                    "text": f"Audio extraction unavailable for {video_path.name}: {extraction_message}",
                }
            ],
            "provenance": "deterministic local fallback",
            "warnings": [extraction_message],
        }
    )

    slides = []
    for index, slide_range in enumerate(ranges, start=1):
        speaker_text = _segment_text_for_range(
            transcript,
            slide_range.start_seconds,
            slide_range.end_seconds,
        )
        fallback = {
            "slide_number": index,
            "start": format_timestamp(slide_range.start_seconds),
            "end": format_timestamp(slide_range.end_seconds),
            "slide_summary": (
                f"Detected slide interval {index} from {slide_range.start} to {slide_range.end}. "
                "Visual OCR is not performed in the deterministic fallback."
            ),
            "speaker_notes": speaker_text
            or "No speaker transcript was available for this slide interval.",
        }
        response = chat_json(
            (
                "Return only JSON with keys slide_number, start, end, "
                "slide_summary, and speaker_notes."
            ),
            (
                "Summarize this slide interval for a slide-by-slide report.\n\n"
                f"Video: {video_path.name}\n"
                f"Slide number: {index}\n"
                f"Timestamp range: {fallback['start']} to {fallback['end']}\n"
                f"Speaker transcript for this interval:\n{speaker_text}"
            ),
            fallback,
        )
        response["slide_number"] = index
        response["start"] = fallback["start"]
        response["end"] = fallback["end"]
        response["slide_summary"] = clean_generated_text(str(response["slide_summary"]))
        response["speaker_notes"] = clean_generated_text(str(response["speaker_notes"]))
        slides.append(response)

    return SlideReport.from_dict({"total_slides": len(slides), "slides": slides})


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a slide-aligned video summary.")
    parser.add_argument("--input", default="video.mp4", help="Path to the input MP4 file.")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    video_path = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    report = build_slide_report(video_path)

    write_json(out_dir / "output.json", report.to_dict())
    (out_dir / "report.md").write_text(
        render_task2_report(report, source=video_path.name),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'output.json'}")
    print(f"Wrote {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
