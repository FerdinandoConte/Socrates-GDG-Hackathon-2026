import pytest
from agent.speech import _extract_pauses, format_voice_metadata

def test_extract_pauses_no_pauses():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        {"text": "world", "start": 0.5, "end": 1.0},
    ]
    pauses = _extract_pauses(words, threshold=2.0)
    assert len(pauses) == 0

def test_extract_pauses_with_pauses():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.5},
        # 2.5 second gap
        {"text": "world", "start": 3.0, "end": 3.5},
    ]
    pauses = _extract_pauses(words, threshold=2.0)
    assert len(pauses) == 1
    assert pauses[0]["after_word"] == "hello"
    assert pauses[0]["before_word"] == "world"
    assert pauses[0]["duration_seconds"] == 2.5

def test_format_voice_metadata():
    transcription = {
        "text": "hello world",
        "detected_pauses": [
            {"after_word": "hello", "before_word": "world", "duration_seconds": 2.5}
        ],
        "low_confidence_words": [
            {"text": "world", "confidence": 0.4}
        ]
    }
    output = format_voice_metadata(transcription)
    assert "Transcription: hello world" in output
    assert "2.5s pause between \"hello\" and \"world\"" in output
    assert "Low-confidence words: \"world\" (confidence: 0.40)" in output

def test_format_voice_metadata_clean():
    transcription = {
        "text": "perfect sentence",
        "detected_pauses": [],
        "low_confidence_words": []
    }
    output = format_voice_metadata(transcription)
    assert "Transcription: perfect sentence" in output
    assert "Detected pauses: none" in output
    assert "Low-confidence words: none" in output
