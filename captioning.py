"""Caption extraction and subtitle formatting primitives."""
# Import dataclass support for immutable caption records.
from dataclasses import dataclass
# Import regular expressions for whitespace normalization.
import re


@dataclass(frozen=True)
class Caption:
    """A caption recognized from a video frame."""

    # Store the caption start time in seconds.
    start_seconds: float
    # Store the caption end time in seconds.
    end_seconds: float
    # Store the visible caption text.
    text: str


class CaptionEngine:
    """Normalize recognized text and export standard SRT subtitles."""

    def normalize_text(self, text: str) -> str:
        # Collapse line breaks and repeated whitespace before displaying text.
        return re.sub(r"\s+", " ", text).strip()

    def create_caption(self, start_seconds: float, end_seconds: float, text: str) -> Caption:
        # Reject invalid timestamps so malformed subtitles are never emitted.
        if start_seconds < 0 or end_seconds <= start_seconds:
            raise ValueError("Caption timestamps must be increasing and non-negative.")
        # Normalize the text before creating the immutable caption record.
        normalized = self.normalize_text(text)
        # Reject empty OCR or speech-recognition results.
        if not normalized:
            raise ValueError("Caption text cannot be empty.")
        # Return a validated caption record.
        return Caption(start_seconds, end_seconds, normalized)

    def to_srt(self, captions: list[Caption]) -> str:
        # Convert every caption into the numbered SRT block format.
        blocks = []
        # Enumerate captions using the one-based numbering required by SRT.
        for number, caption in enumerate(captions, start=1):
            # Build one subtitle block with timestamps and text.
            blocks.append(
                f"{number}\n{self._srt_time(caption.start_seconds)} --> "
                f"{self._srt_time(caption.end_seconds)}\n{caption.text}"
            )
        # Separate subtitle blocks with blank lines as required by SRT.
        return "\n\n".join(blocks)

    def _srt_time(self, seconds: float) -> str:
        # Convert fractional seconds to milliseconds without floating drift.
        milliseconds = round(seconds * 1000)
        # Split milliseconds into whole hours, minutes, seconds, and remainder.
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, millis = divmod(remainder, 1000)
        # Return the canonical SRT timestamp representation.
        return f"{hours:02}:{minutes:02}:{whole_seconds:02},{millis:03}"