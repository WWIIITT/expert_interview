import json
import tempfile
import unittest
from pathlib import Path

from solution.shared.markdown import render_task1_markdown, render_task2_report
from solution.shared.media import format_timestamp, read_wav_duration
from solution.shared.schemas import (
    Slide,
    SlideReport,
    Task1Summary,
    validate_json_file,
)


class CoreBehaviorTests(unittest.TestCase):
    def test_task1_summary_rejects_missing_conclusion(self):
        with self.assertRaises(ValueError):
            Task1Summary.from_dict({"topics": ["AI"], "findings": ["Finding"]})

    def test_markdown_mentions_source_and_sections(self):
        summary = Task1Summary(
            topics=["AI systems"],
            findings=["Chunked processing improves robustness."],
            conclusion="The pipeline produces searchable conference summaries.",
        )

        markdown = render_task1_markdown(summary, source="talk.wav")

        self.assertIn("talk.wav", markdown)
        self.assertIn("## Key Topics", markdown)
        self.assertIn("Chunked processing improves robustness.", markdown)

    def test_task2_report_counts_slides(self):
        report = SlideReport(
            total_slides=1,
            slides=[
                Slide(
                    slide_number=1,
                    start="00:00",
                    end="00:10",
                    slide_summary="Opening title slide.",
                    speaker_notes="The speaker introduces the topic.",
                )
            ],
        )

        markdown = render_task2_report(report, source="video.mp4")

        self.assertIn("video.mp4", markdown)
        self.assertIn("Total slides: 1", markdown)
        self.assertIn("Opening title slide.", markdown)

    def test_validate_json_file_round_trips_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(
                json.dumps(
                    {
                        "topics": ["topic"],
                        "findings": ["finding"],
                        "conclusion": "conclusion",
                    }
                ),
                encoding="utf-8",
            )

            loaded = validate_json_file(path, Task1Summary)

            self.assertEqual(loaded.conclusion, "conclusion")

    def test_wav_duration_and_timestamp_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one_second.wav"
            import wave

            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\0\0" * 8000)

            self.assertAlmostEqual(read_wav_duration(path), 1.0, places=2)
            self.assertEqual(format_timestamp(61.2), "01:01")


if __name__ == "__main__":
    unittest.main()
