from __future__ import annotations

import argparse
from pathlib import Path

from pipeline import render_task1_markdown, summarize_audio_basic, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a structured summary for talk audio.")
    parser.add_argument("--input", default="talk.wav", help="Path to the input WAV file.")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    audio_path = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    summary, _transcript = summarize_audio_basic(audio_path)

    write_json(out_dir / "summary.json", summary.to_dict())
    (out_dir / "summary.md").write_text(
        render_task1_markdown(summary, source=audio_path.name),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'summary.json'}")
    print(f"Wrote {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
