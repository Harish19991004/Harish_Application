"""Uploaded-video caption orchestration with replaceable speech/OCR engines."""
# Import callable typing for dependency-injected recognition functions.
from collections.abc import Callable, Iterable
# Import filesystem paths for safe output handling.
from pathlib import Path
# Import URL parsing to reject network destinations explicitly.
from urllib.parse import urlparse
# Import the validated caption model and SRT formatter.
from captioning import Caption, CaptionEngine


class VideoCaptionService:
    """Turn recognized video segments into an SRT file."""

    def __init__(self, recognizer: Callable[[str], Iterable[tuple[float, float, str]]]):
        # Store the speech/OCR adapter supplied by the desktop or Android integration.
        self.recognizer = recognizer
        # Reuse the central validation and SRT formatting rules.
        self.engine = CaptionEngine()

    def generate_srt(self, video_path: str, output_path: str | None = None) -> Path:
        # Resolve the input path without modifying the user's original video.
        self._require_local_path(video_path)
        source = Path(video_path).expanduser()
        # Reject missing or non-file inputs before invoking a recognizer.
        if not source.is_file():
            raise FileNotFoundError(f"Video file not found: {source}")
        # Convert every recognizer segment into a validated caption.
        captions = [
            self.engine.create_caption(start, end, text)
            for start, end, text in self.recognizer(str(source))
        ]
        # Refuse to create an apparently successful empty subtitle file.
        if not captions:
            raise ValueError("The recognizer returned no caption segments.")
        # Place the SRT beside the video unless the caller selected an output path.
        destination = Path(output_path).expanduser() if output_path else source.with_suffix(".srt")
        # Permit only a local device destination selected by the user or defaulted beside the video.
        self._require_local_path(str(destination))
        # Keep generated subtitles in a normal file and never overwrite the source video.
        if destination.resolve() == source.resolve():
            raise ValueError("Subtitle output must be different from the video input.")
        # Write standard UTF-8 SRT content.
        destination.write_text(self.engine.to_srt(captions), encoding="utf-8")
        # Return the generated subtitle path to the caller.
        return destination

    def _require_local_path(self, path: str) -> None:
        # Parse the value as a URL so network schemes cannot be treated as filenames.
        parsed = urlparse(path)
        # Reject URLs such as https://, ftp://, content://, and data:.
        if parsed.scheme or parsed.netloc:
            raise ValueError("Only local device paths are allowed; network destinations are blocked.")


class LiveCaptionSession:
    """Hold live captions only while an approved capture session is active."""

    def __init__(self, engine: CaptionEngine | None = None):
        # Use the shared caption validation logic.
        self.engine = engine or CaptionEngine()
        # Start in the stopped state until Android grants capture access.
        self.active = False
        # Keep live captions in memory for the current session only.
        self.captions: list[Caption] = []

    def start(self, permission_granted: bool) -> None:
        # Refuse to start if the Android system consent result was not affirmative.
        if not permission_granted:
            raise PermissionError("Android capture permission is required.")
        # Mark the live session active after explicit user consent.
        self.active = True

    def add_result(self, start_seconds: float, end_seconds: float, text: str) -> Caption:
        # Prevent OCR or speech results from arriving after capture stops.
        if not self.active:
            raise RuntimeError("Live caption session is not active.")
        # Validate and retain one recognized caption.
        caption = self.engine.create_caption(start_seconds, end_seconds, text)
        self.captions.append(caption)
        # Return the caption so a UI overlay can display it immediately.
        return caption

    def stop(self) -> None:
        # Stop accepting new results and release the in-memory session state.
        self.active = False
        self.captions.clear()