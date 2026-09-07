"""Caption companion application entry point."""
# Import the optional Kivy application base when running on a device.
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.filechooser import FileChooserListView
    from kivy.uix.label import Label
except ImportError:
    App = None

# Import the application services that are safe to use on every platform.
from captioning import CaptionEngine
from security import SecureSettings
from android_bridge import AndroidCaptureBridge
from recognizers import WhisperRecognizer
from video_captioning import VideoCaptionService
from live_controller import LiveCaptionController


class CaptionRoot(BoxLayout):
    """Small UI that requires explicit user consent before capture starts."""

    def __init__(self, **kwargs):
        # Initialize the vertical layout supplied by Kivy.
        super().__init__(orientation="vertical", padding=24, spacing=16, **kwargs)
        # Create secure local settings storage.
        self.settings = SecureSettings()
        # Create the Android permission adapter.
        self.capture_bridge = AndroidCaptureBridge()
        # Coordinate Android consent and the live overlay lifecycle.
        self.live_controller = LiveCaptionController(
            self.capture_bridge.request_capture_permission,
            self.capture_bridge.request_overlay_permission,
            self.capture_bridge.start_caption_overlay,
            self.capture_bridge.stop_caption_overlay,
        )
        # Create the local caption engine.
        self.caption_engine = CaptionEngine()
        # Configure lazy local Whisper recognition for uploaded videos.
        self.video_service = VideoCaptionService(WhisperRecognizer())
        # Show the current state to the user.
        self.status = Label(text="Ready. Capture is off.")
        # Add the status label to the layout.
        self.add_widget(self.status)
        # Create the consent button.
        self.capture_button = Button(text="Grant access and start captions")
        # Connect the button to the consent flow.
        self.capture_button.bind(on_press=self.request_capture)
        # Add the button to the layout.
        self.add_widget(self.capture_button)
        # Create a video picker for the offline uploaded-video workflow.
        self.video_picker = FileChooserListView(filters=["*.mp4", "*.mkv", "*.webm", "*.mov"])
        # Add the picker to the layout.
        self.add_widget(self.video_picker)
        # Create the upload processing button.
        self.upload_button = Button(text="Generate SRT from selected video")
        # Connect the upload button to the offline generation workflow.
        self.upload_button.bind(on_press=self.generate_uploaded_srt)
        # Add the upload button to the layout.
        self.add_widget(self.upload_button)

    def request_capture(self, _button):
        # Request overlay and Android screen-capture permissions.
        self.status.text = self.live_controller.request_access()

    def generate_uploaded_srt(self, _button):
        # Require exactly one selected video before starting generation.
        if not self.video_picker.selection:
            self.status.text = "Select a video first."
            return
        # Generate the subtitle file beside the selected video.
        try:
            output = self.video_service.generate_srt(self.video_picker.selection[0])
        except RuntimeError as error:
            # Tell the user how to enable the optional local speech engine.
            self.status.text = str(error)
            return
        # Show the generated file path to the user.
        self.status.text = f"SRT created: {output.name}"


class CaptionApp(App):
    """Kivy application container."""

    def build(self):
        # Return the root widget for the Kivy event loop.
        return CaptionRoot()


if __name__ == "__main__":
    # Start the mobile application when this module is executed directly.
    if App is None:
        raise SystemExit("Install Kivy to run the mobile UI.")
    # Run the Kivy application event loop.
    CaptionApp().run()