"""Speech-to-Text integration via ElevenLabs Scribe API."""

import os
import requests


def transcribe_audio(audio_bytes: bytes) -> dict:
    """Transcribe audio using ElevenLabs Speech-to-Text API.

    Returns a dict with:
        - text: full transcription string
        - words: list of word-level dicts [{text, start, end, confidence}, ...]
        - detected_pauses: pauses > 2s between words
        - low_confidence_words: words with confidence < 0.7
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set in environment")

    response = requests.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": api_key},
        files={"file": ("recording.webm", audio_bytes, "audio/webm")},
        data={"model_id": "scribe_v1", "timestamps_granularity": "word"},
    )
    response.raise_for_status()
    result = response.json()

    words = result.get("words", [])
    return {
        "text": result.get("text", ""),
        "words": words,
        "detected_pauses": _extract_pauses(words, threshold=2.0),
        "low_confidence_words": [
            w for w in words if w.get("confidence", 1.0) < 0.7
        ],
    }


def _extract_pauses(words: list[dict], threshold: float = 2.0) -> list[dict]:
    """Detect long pauses (> threshold seconds) between consecutive words."""
    pauses = []
    for i in range(1, len(words)):
        prev_end = words[i - 1].get("end", 0)
        curr_start = words[i].get("start", 0)
        gap = curr_start - prev_end
        if gap >= threshold:
            pauses.append({
                "after_word": words[i - 1].get("text", ""),
                "before_word": words[i].get("text", ""),
                "duration_seconds": round(gap, 1),
            })
    return pauses


def format_voice_metadata(transcription: dict) -> str:
    """Format voice metadata for inclusion in LLM evaluation prompts."""
    parts = [f"Transcription: {transcription['text']}"]

    pauses = transcription.get("detected_pauses", [])
    if pauses:
        pause_strs = [
            f"  - {p['duration_seconds']}s pause between \"{p['after_word']}\" and \"{p['before_word']}\""
            for p in pauses
        ]
        parts.append("Detected pauses (> 2s):\n" + "\n".join(pause_strs))
    else:
        parts.append("Detected pauses: none")

    low_conf = transcription.get("low_confidence_words", [])
    if low_conf:
        words_str = ", ".join(
            f"\"{w.get('text', '')}\" (confidence: {w.get('confidence', 0):.2f})"
            for w in low_conf[:10]
        )
        parts.append(f"Low-confidence words: {words_str}")
    else:
        parts.append("Low-confidence words: none")

    return "\n\n".join(parts)
