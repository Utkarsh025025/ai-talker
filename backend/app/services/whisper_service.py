"""
Groq Whisper transcription service.
Transcribes audio/video files using Groq's Whisper endpoint and extracts
topic timestamps via Groq's LLM chat API.
"""

import json
from pathlib import Path
from groq import AsyncGroq
from app.config import get_settings
from app.schemas.document import TimestampEntry

settings = get_settings()

# Shared async Groq client (reused across requests)
_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


class WhisperService:
    """Transcription and timestamp extraction for audio/video media."""

    @staticmethod
    async def transcribe(file_path: str | Path) -> dict:
        """
        Transcribe an audio/video file using Groq's Whisper API.

        Groq supports: whisper-large-v3, whisper-large-v3-turbo,
        distil-whisper-large-v3-en (fastest).

        Returns a dict with:
          - full_text: str
          - language: str | None
          - duration_seconds: float | None
          - segments: list of segment dicts (start, end, text)
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        with open(file_path, "rb") as audio_file:
            response = await _client.audio.transcriptions.create(
                model=settings.GROQ_WHISPER_MODEL,
                file=audio_file,
                response_format="verbose_json",  # returns segments with timestamps
            )

        # Groq returns segments as a list of dicts with 'start', 'end', 'text'
        segments: list[dict] = getattr(response, "segments", None) or []

        # Compute duration from the last segment's end time
        duration: float | None = None
        if segments:
            duration = segments[-1].get("end")

        return {
            "full_text": response.text,
            "language": getattr(response, "language", None),
            "duration_seconds": duration,
            "segments": segments,
        }

    @staticmethod
    async def extract_topic_timestamps(
        full_text: str,
        segments: list[dict],
    ) -> list[TimestampEntry]:
        """
        Use Groq's LLM to identify major topic transitions in the transcript
        and map them to the nearest Whisper segment timestamps.

        Returns a list of TimestampEntry objects sorted by timestamp.
        """
        if not full_text.strip():
            return []

        # Build a compact segment map for the LLM (timestamp → text)
        segment_map = [
            {"t": round(seg.get("start", 0), 1), "text": seg.get("text", "").strip()}
            for seg in segments
        ]
        # Cap at 200 entries to stay within token limits
        segment_json = json.dumps(segment_map[:200], ensure_ascii=False)

        system_prompt = (
            "You are a transcript analyst. Identify the major topic transitions in the transcript below. "
            "For each topic, provide:\n"
            "1. The timestamp (in seconds) of the nearest segment where the topic begins.\n"
            "2. A short topic label (≤ 6 words).\n"
            "3. The first sentence of that segment as 'text'.\n\n"
            "Respond ONLY with a valid JSON object containing a 'topics' array. Example:\n"
            '{"topics": [{"timestamp": 0.0, "topic": "Introduction", "text": "Welcome to the show."}]}\n\n'
            "Identify between 3 and 15 topics."
        )

        user_prompt = (
            f"Segments (timestamp → text):\n{segment_json}\n\n"
            f"Full transcript:\n{full_text[:4000]}"
        )

        response = await _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=1024,
        )

        raw = response.choices[0].message.content or "{}"

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        # Extract the list — could be wrapped in a key like "topics"
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    parsed = v
                    break
            else:
                return []

        entries = [
            TimestampEntry(
                timestamp=float(item.get("timestamp", 0.0)),
                topic=item.get("topic", ""),
                text=item.get("text", ""),
            )
            for item in parsed
            if isinstance(item, dict)
        ]

        return sorted(entries, key=lambda e: e.timestamp)
