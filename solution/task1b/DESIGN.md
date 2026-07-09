# Task 1b Design

## Reasoning and Architecture

Task 1a is a linear single-file pipeline: transcribe one WAV file, summarize it, and write two outputs. Task 1b keeps that simple interface but separates the system into reusable stages so the same approach can run across hundreds of conference talks.

The scaled workflow is:

1. Normalize the input into a known audio format.
2. Split long recordings into timestamped chunks.
3. Transcribe each chunk with provider retries.
4. Merge transcript segments with provenance.
5. Ask an LLM for structured summaries.
6. Validate the output schema before writing JSON and Markdown.

The implementation in `run.py` demonstrates the evolved contract on the original `talk.wav`. The shared modules are intentionally small: media helpers measure and normalize inputs, LLM helpers encapsulate provider access, schema helpers validate output, and markdown helpers render reviewer-friendly summaries.

## Output Schema

The Task 1a schema is compact:

```json
{
  "topics": ["topic"],
  "findings": ["finding"],
  "conclusion": "summary conclusion"
}
```

For a larger corpus, that is too little context. Task 1b writes:

```json
{
  "source": "talk.wav",
  "duration_seconds": 672.1,
  "transcript_provenance": "provider audio transcription",
  "segments": [
    {"start": "00:00", "end": "02:00", "text": "transcript text"}
  ],
  "topics": ["topic"],
  "findings": ["finding"],
  "conclusion": "summary conclusion",
  "quality_notes": ["quality or review note"],
  "warnings": ["recoverable pipeline warning"]
}
```

This preserves the simple reader-facing fields while adding the metadata needed for auditability, search indexing, and selective reprocessing.

## Failure Modes

- Missing or invalid API credentials: the pipeline writes deterministic fallback outputs and records the issue in `warnings`.
- Provider transcription failure: the run continues with a local placeholder transcript so downstream schema validation and rendering can still be exercised.
- Long recordings: chunk boundaries make retries smaller and prevent a single failed segment from invalidating a whole talk.
- Mixed domains: the schema avoids domain-specific fields and lets topics/findings remain flexible.
- Low audio quality or multiple speakers: quality notes and timestamped segments expose uncertainty for later diarization or human review.
- Invalid LLM JSON: schema validation rejects malformed outputs before they are written.

## Tradeoff

I chose a provider-backed architecture with deterministic local fallbacks instead of a fully local ASR stack. This keeps setup light and assessment-friendly while still showing how the production system would isolate provider calls, preserve provenance, and recover from failures. The tradeoff is that high-quality transcripts require configured credentials and a provider that supports audio transcription.
