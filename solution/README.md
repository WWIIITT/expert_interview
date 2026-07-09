# EAI Technical Assessment Solution

This submission contains three runnable Python pipelines:

- `task1a`: audio transcription plus structured conference-summary generation from `talk.wav`
- `task1b`: a scaled version of the audio pipeline with richer schema and architecture notes
- `task2`: slide-change detection and slide-aligned reporting from `video.mp4`

## Setup

Use Python 3.11 or later.

```powershell
cd D:\GitHub\expert_interview
python -m venv .venv
.\.venv\Scripts\pip install -r solution\requirements.txt
```

Configure an OpenAI-compatible provider with environment variables:

```powershell
$env:LLM_API_KEY="your-api-key"
$env:LLM_BASE_URL="https://api.vectorengine.cn/v1"
$env:LLM_MODEL="gpt-4o-mini"
$env:ASR_MODEL="whisper-1"
```

Recommended model choices:

- `LLM_MODEL`: use `gpt-4o-mini` for a low-cost structured-summary run, or use a stronger chat model exposed by your VectorEngine account if available.
- `ASR_MODEL`: use `whisper-1` first because this code requests `verbose_json`, which is useful for timestamps. If your provider supports newer OpenAI audio models, `gpt-4o-transcribe` or `gpt-4o-mini-transcribe` are also valid transcription model names, but they may not support the exact same verbose timestamp fields.

Secrets are read only from the environment and are not stored in the repository.

## Reproduce the Outputs

Run from the repository root:

```powershell
python solution/task1a/run.py --input talk.wav
python solution/task1b/run.py --input talk.wav
python solution/task2/run.py --input video.mp4
```

Expected generated files:

- `solution/task1a/summary.json`
- `solution/task1a/summary.md`
- `solution/task1b/summary.json`
- `solution/task1b/summary.md`
- `solution/task2/output.json`
- `solution/task2/report.md`

## Approach

Each task directory contains its own pipeline code so the submission follows the requested structure directly. Provider chat calls target an OpenAI-compatible `/chat/completions` endpoint. Audio transcription targets an OpenAI-compatible `/audio/transcriptions` endpoint when credentials are configured.

Task 2 uses `imageio-ffmpeg` to extract audio through a bundled FFmpeg binary and OpenCV to sample frames for slide-change detection. If optional media dependencies or credentials are missing, the scripts still generate deterministic, schema-valid fallback outputs with warnings instead of crashing.

## What Worked

- Keeping transcription, summarization, validation, and rendering as separate stages made the pipeline easy to extend from Task 1a to Task 1b.
- JSON schema validation catches malformed model responses before outputs are written.
- Timestamped segments give the video pipeline a clean alignment point between audio transcript and slide ranges.

## Known Limitations

- The deterministic fallback does not perform real speech recognition; high-quality summaries require configured provider credentials.
- Slide detection is image-difference based, so subtle animations or camera movement can create false positives or missed slide changes.
- The video pipeline does not perform OCR over slide frames; visual slide summaries are based on detected intervals and LLM text summarization.

## What I Would Improve with More Time

- Add speaker diarization for panels and Q&A.
- Add OCR for slide text and combine visual text with transcript notes.
- Store intermediate transcripts and frame thumbnails for audit and reprocessing.
- Add batch orchestration with resumable job state and per-talk retry budgets.

For Task 1b's architectural reasoning, schema design, failure modes, and tradeoff discussion, see `solution/task1b/DESIGN.md`.
