"""Tests for caption validation and SRT generation."""
# Import the caption engine under test.
from captioning import CaptionEngine
from video_captioning import LiveCaptionSession, VideoCaptionService
from live_controller import LiveCaptionController
from recognizers import VoskSpeechRecognizer
from capture_pipeline import LocalCapturePipeline


def test_caption_text_is_normalized():
    # Create the pure-Python caption engine.
    engine = CaptionEngine()
    # Create a caption with irregular whitespace.
    caption = engine.create_caption(0, 2.5, "  hello\n   world  ")
    # Verify output is suitable for a subtitle line.
    assert caption.text == "hello world"


def test_srt_uses_millisecond_timestamps():
    # Create the pure-Python caption engine.
    engine = CaptionEngine()
    # Create a caption crossing one minute.
    caption = engine.create_caption(61.25, 63.5, "Ready")
    # Verify canonical SRT output.
    assert engine.to_srt([caption]) == "1\n00:01:01,250 --> 00:01:03,500\nReady"


def test_invalid_caption_is_rejected():
    # Create the pure-Python caption engine.
    engine = CaptionEngine()
    # Verify invalid time ranges cannot enter the subtitle stream.
    try:
        engine.create_caption(3, 2, "invalid")
    except ValueError as error:
        assert "timestamps" in str(error)
    else:
        raise AssertionError("Invalid timestamps should raise ValueError")


def test_uploaded_video_generates_srt(tmp_path):
    # Create a fake video path for the recognizer contract test.
    video_path = tmp_path / "movie.mp4"
    video_path.write_bytes(b"video")
    # Provide deterministic speech-recognition segments.
    service = VideoCaptionService(lambda _path: [(0, 1.5, "Hello"), (1.5, 3, "world")])
    # Generate subtitles beside the uploaded video.
    output = service.generate_srt(str(video_path))
    # Verify the generated SRT file and its content.
    assert output == tmp_path / "movie.srt"
    assert "00:00:00,000 --> 00:00:01,500" in output.read_text()


def test_uploaded_video_rejects_network_paths(tmp_path):
    # Create a local video path that would otherwise be valid.
    video_path = tmp_path / "movie.mp4"
    video_path.write_bytes(b"video")
    # Create a service with a deterministic recognizer.
    service = VideoCaptionService(lambda _path: [(0, 1, "Local only")])
    # Verify a remote output destination is blocked before any write occurs.
    try:
        service.generate_srt(str(video_path), "https://example.test/captions.srt")
    except ValueError as error:
        assert "local device paths" in str(error)
    else:
        raise AssertionError("Network subtitle destinations must be rejected")


def test_live_session_requires_permission_and_stops_cleanly():
    # Create a live caption session.
    session = LiveCaptionSession()
    # Verify capture cannot begin without Android consent.
    try:
        session.start(False)
    except PermissionError:
        pass
    else:
        raise AssertionError("Live capture should require permission")
    # Start after consent and accept one recognized result.
    session.start(True)
    session.add_result(0, 1, "Live")
    # Stop capture and remove transient caption data.
    session.stop()
    assert session.active is False
    assert session.captions == []


def test_live_controller_requires_both_permissions_and_cleans_up():
    # Track Android bridge calls without requiring an Android device.
    calls = []
    controller = LiveCaptionController(
        lambda: calls.append("capture") or True,
        lambda: calls.append("overlay") or True,
        lambda: calls.append("start") or True,
        lambda: calls.append("stop"),
    )
    # Request both permissions before a live session can begin.
    assert "Approve Android capture" in controller.request_access()
    assert calls == ["overlay", "capture"]
    # Start only after the system consent result is affirmative.
    assert "running" in controller.start_after_consent(True)
    assert controller.overlay_running is True
    # Stop removes the overlay and clears transient captions.
    controller.stop()
    assert calls[-1] == "stop"
    assert controller.overlay_running is False


def test_vosk_recognizer_requires_a_bundled_local_model(tmp_path):
    # Create an offline recognizer pointed at a missing model directory.
    recognizer = VoskSpeechRecognizer(str(tmp_path / "missing-model"))
    # Verify recognition fails locally instead of attempting a download.
    try:
        list(recognizer.recognize_chunks([b"pcm"]))
    except FileNotFoundError as error:
        assert "Offline Vosk model" in str(error)
    else:
        raise AssertionError("Missing offline models must fail closed")


def test_capture_pipeline_ignores_missing_buffers(tmp_path):
    # Create a pipeline pointed at an empty private capture directory.
    published = []
    pipeline = LocalCapturePipeline(str(tmp_path), str(tmp_path / "model"), published.append)
    # Polling before Android capture starts must be a harmless no-op.
    pipeline.poll(0.5)
    # Verify no caption was published without a local frame or audio buffer.
    assert published == []