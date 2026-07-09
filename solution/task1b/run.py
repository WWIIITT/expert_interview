from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solution.shared.markdown import render_scaled_markdown
from solution.shared.pipeline import summarize_audio_scaled
from solution.shared.schemas import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the scaled conference-audio pipeline.")
    parser.add_argument("--input", default="talk.wav", help="Path to the input WAV file.")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    audio_path = Path(args.input).resolve()
    out_dir = Path(args.out_dir).resolve()
    summary = summarize_audio_scaled(audio_path)

    write_json(out_dir / "summary.json", summary.to_dict())
    (out_dir / "summary.md").write_text(
        render_scaled_markdown(summary),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'summary.json'}")
    print(f"Wrote {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
