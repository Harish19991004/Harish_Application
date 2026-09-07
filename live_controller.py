"""Permission-gated lifecycle for live captions over another Android app."""
# Import callback typing for the UI and Android bridge hooks.
from collections.abc import Callable
# Import the live session that owns transient caption data.
from video_captioning import LiveCaptionSession


class LiveCaptionController:
    """Coordinate consent, overlay state, and local live-caption cleanup."""

    def __init__(
        self,
        request_capture: Callable[[], bool],
        request_overlay: Callable[[], bool],
        start_overlay: Callable[[], bool],
        stop_overlay: Callable[[], None],
    ):
        # Store the Android MediaProjection consent request.
        self.request_capture = request_capture
        # Store the Android overlay permission request.
        self.request_overlay = request_overlay
        # Store the overlay-service start callback.
        self.start_overlay = start_overlay
        # Store the overlay-service stop callback.
        self.stop_overlay = stop_overlay
        self._publish_overlay = lambda _text: None
        # Keep all recognized live caption text in the session object only.
        self.session = LiveCaptionSession()
        # Track whether the Android capture request has been launched.
        self.capture_requested = False
        # Track whether the visible caption overlay is running.
        self.overlay_running = False

    def request_access(self) -> str:
        # Ask for the overlay capability needed to draw above MX Player.
        overlay_ready = self.request_overlay()
        # Ask for the system-managed screen/audio capture consent dialog.
        capture_requested = self.request_capture()
        # Remember that the user must still approve Android's capture dialog.
        self.capture_requested = capture_requested
        # Return a user-facing state instead of claiming capture already works.
        if overlay_ready and capture_requested:
            return "Approve Android capture, then return here to start live captions."
        return "Overlay or screen capture permission could not be requested."

    def start_after_consent(self, permission_granted: bool) -> str:
        # Require both Android consent and a successful overlay service start.
        self.session.start(permission_granted)
        # Start the local overlay service after consent has actually been granted.
        if not self.start_overlay():
            self.session.stop()
            raise RuntimeError("The Android caption overlay could not be started.")
        # Mark the live overlay active.
        self.overlay_running = True
        # Return a status suitable for the application UI.
        return "Live captions are running on this device."

    def publish_caption(self, text: str) -> None:
        """Publish already-recognized text through the service callback."""
        self._publish_overlay(text)

    def record_caption(self, start_seconds: float, end_seconds: float, text: str) -> None:
        """Validate and retain one live result before displaying it."""
        self.session.add_result(start_seconds, end_seconds, text)

    def set_overlay_publisher(self, publish_overlay: Callable[[str], None]) -> None:
        self._publish_overlay = publish_overlay

    def live_srt(self) -> str:
        if not self.session.captions:
            raise ValueError("No live captions are available to export.")
        return self.session.engine.to_srt(self.session.captions)

    def stop(self) -> None:
        # Stop the Android overlay before clearing caption state.
        self.stop_overlay()
        # Clear all transient caption data from memory.
        self.session.stop()
        # Reset lifecycle state so a later run requires fresh consent.
        self.capture_requested = False
        self.overlay_running = False