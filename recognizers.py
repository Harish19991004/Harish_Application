"""Optional speech-recognition adapters for caption generation."""
# Import iterable typing for recognizer segment output.
from collections.abc import Iterable
import json
from pathlib import Path


class WhisperRecognizer:
    """Lazy local Whisper adapter; install faster-whisper separately to enable it."""

    def __init__(self, model_size: str = "base"):
        # Store the model choice without downloading anything during app startup.
        self.model_size = model_size
        # Delay model construction until a video is actually selected.
        self._model = None

    def __call__(self, video_path: str) -> Iterable[tuple[float, float, str]]:
        # Import the optional package only when upload processing is requested.
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "Install faster-whisper to generate uploaded-video captions."
            ) from error
        # Load the local model once and reuse it for later uploads.
        if self._model is None:
            self._model = WhisperModel(self.model_size, compute_type="int8")
        # Transcribe locally without sending video or audio to a service.
        segments, _info = self._model.transcribe(video_path, vad_filter=True)
        # Yield only the fields required by VideoCaptionService.
        for segment in segments:
            yield segment.start, segment.end, segment.text


class VoskSpeechRecognizer:
    """Offline Vosk recognizer for PCM audio chunks and bundled local models."""

    def __init__(self, model_path: str, sample_rate: int = 16_000):
        # Store the model directory selected from app-private bundled assets.
        self.model_path = Path(model_path)
        # Store the PCM sample rate expected by the Vosk recognizer.
        self.sample_rate = sample_rate
        # Delay loading the native model until recognition is requested.
        self._recognizer = None

    def recognize_chunks(self, chunks: Iterable[bytes]) -> Iterable[str]:
        # Reject missing models instead of falling back to a network service.
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Offline Vosk model not found: {self.model_path}")
        # Import Vosk only when the user starts local recognition.
        try:
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            raise RuntimeError("Install vosk and bundle a local Vosk model.") from error
        # Load the model once for the current app process.
        if self._recognizer is None:
            self._recognizer = KaldiRecognizer(Model(str(self.model_path)), self.sample_rate)
        # Process every PCM chunk locally and yield only final recognized text.
        for chunk in chunks:
            if self._recognizer.AcceptWaveform(chunk):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    yield text


class TesseractOcrRecognizer:
    """Offline OCR adapter for captured video frames."""

    def recognize(self, image) -> str:
        # Import pytesseract only when OCR is enabled.
        try:
            import pytesseract
        except ImportError as error:
            raise RuntimeError("Install pytesseract and the local Tesseract engine.") from error
        # Run OCR against the frame without network access.
        return pytesseract.image_to_string(image).strip()