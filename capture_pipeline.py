"""Local bridge from Android capture buffers to offline speech and OCR."""
# Import filesystem support for app-private capture buffers.
from pathlib import Path
# Import the local recognizer adapters.
from recognizers import TesseractOcrRecognizer, VoskSpeechRecognizer


class LocalCapturePipeline:
    """Poll app-private Android buffers and publish local recognition results."""

    def __init__(
        self,
        buffer_dir: str,
        model_dir: str,
        publish_caption,
        record_caption=None,
        enable_frame_ocr: bool = True,
    ):
        # Store the directory written by the Android foreground service.
        self.buffer_dir = Path(buffer_dir)
        # Configure the local Vosk model path.
        self.speech = VoskSpeechRecognizer(model_dir)
        # Configure local Tesseract OCR.
        self.ocr = TesseractOcrRecognizer()
        # Store the callback that updates the overlay text.
        self.publish_caption = publish_caption
        self.record_caption = record_caption
        # Use Android ML Kit for device frames unless a desktop fallback is requested.
        self.enable_frame_ocr = enable_frame_ocr
        # Track how much PCM audio has already been read.
        self.audio_offset = 0
        # Track the last frame modification time to avoid repeated OCR.
        self.last_frame_mtime = 0.0
        # Track caption timing for live subtitle records.
        self.elapsed_seconds = 0.0

    def poll(self, elapsed_seconds: float) -> None:
        self.elapsed_seconds += max(0.0, elapsed_seconds)
        # Process a newly written video frame with local OCR.
        self._poll_frame(self.elapsed_seconds)
        # Process newly appended playback PCM with local Vosk recognition.
        self._poll_audio(self.elapsed_seconds)

    def _poll_frame(self, elapsed_seconds: float) -> None:
        # Skip the Python OCR fallback when Android ML Kit owns frame recognition.
        if not self.enable_frame_ocr:
            return
        # Locate the latest app-private PNG frame.
        frame_path = self.buffer_dir / "frame.png"
        # Skip OCR when Android has not produced a frame or it has not changed.
        try:
            frame_mtime = frame_path.stat().st_mtime
        except FileNotFoundError:
            return
        if frame_mtime <= self.last_frame_mtime:
            return
        # Record the frame version before OCR begins.
        self.last_frame_mtime = frame_mtime
        # Import Pillow only when frame OCR is enabled.
        try:
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Install Pillow to enable local frame OCR.") from error
        # Read the frame locally and run Tesseract without network access.
        with Image.open(frame_path) as image:
            text = self.ocr.recognize(image)
        # Publish non-empty OCR text to the device overlay.
        if text:
            self._publish(text, elapsed_seconds, elapsed_seconds + 0.5)

    def _poll_audio(self, elapsed_seconds: float) -> None:
        # Locate the append-only app-private PCM buffer.
        audio_path = self.buffer_dir / "audio.pcm"
        # Skip recognition until Android has created the audio stream.
        try:
            audio_size = audio_path.stat().st_size
        except FileNotFoundError:
            return
        # Reset the read cursor when the Android service rotates or clears the buffer.
        if audio_size < self.audio_offset:
            self.audio_offset = 0
        # Read only bytes not processed by the previous poll.
        with audio_path.open("rb") as audio_file:
            audio_file.seek(self.audio_offset)
            chunk = audio_file.read()
            self.audio_offset = audio_file.tell()
        # Skip empty polling intervals.
        if not chunk:
            return
        # Send the new PCM bytes through local Vosk recognition.
        chunk_duration = len(chunk) / (2 * self.speech.sample_rate)
        start_seconds = max(0.0, elapsed_seconds - chunk_duration)
        for text in self.speech.recognize_chunks([chunk]):
            self._publish(text, start_seconds, elapsed_seconds)

    def _publish(self, text: str, start_seconds: float, end_seconds: float) -> None:
        if self.record_caption is not None:
            self.record_caption(start_seconds, end_seconds, text)
        self.publish_caption(text)