"""Caption companion application entry point."""
# Import the optional Kivy application base when running on a device.
try:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.filechooser import FileChooserListView
    from kivy.uix.label import Label
except ImportError:
    App = None

# Import the application services that are safe to use on every platform.
from android_bridge import AndroidCaptureBridge
from recognizers import WhisperRecognizer
from video_captioning import VideoCaptionService
from live_controller import LiveCaptionController
from capture_pipeline import LocalCapturePipeline


class CaptionRoot(BoxLayout):
    """Small UI that requires explicit user consent before capture starts."""

    def __init__(self, **kwargs):
        # Initialize the vertical layout supplied by Kivy.
        super().__init__(orientation="vertical", padding=24, spacing=16, **kwargs)
        # Create the Android permission adapter.
        self.capture_bridge = AndroidCaptureBridge()
        # Coordinate Android consent and the live overlay lifecycle.
        self.live_controller = LiveCaptionController(
            self.capture_bridge.request_capture_permission,
            self.capture_bridge.request_overlay_permission,
            self.capture_bridge.start_caption_overlay,
            self.capture_bridge.stop_caption_overlay,
        )
        # Create the local buffer-to-recognizer pipeline without network services.
        self.capture_pipeline = LocalCapturePipeline(
            self.capture_bridge.capture_buffer_directory(),
            self.capture_bridge.model_directory(),
            self.capture_bridge.update_caption_overlay,
            enable_frame_ocr=False,
        )
        # Keep the polling event handle so it can be cancelled on stop.
        self.pipeline_event = None
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
        # Create the explicit start button used after Android consent is approved.
        self.start_live_button = Button(text="Start live processing")
        # Connect the start action to local recognizer polling.
        self.start_live_button.bind(on_press=self.start_live_processing)
        # Add the start action to the layout.
        self.add_widget(self.start_live_button)
        # Create a visible stop action that clears the overlay and buffers.
        self.stop_live_button = Button(text="Stop live captions")
        # Connect the stop action to cleanup.
        self.stop_live_button.bind(on_press=self.stop_live_processing)
        # Add the stop action to the layout.
        self.add_widget(self.stop_live_button)
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

    def start_live_processing(self, _button):
        # Start the service and session only after the user approved Android capture.
        try:
            self.status.text = self.live_controller.start_after_consent(
                self.capture_bridge.capture_permission_granted()
            )
        except (PermissionError, RuntimeError) as error:
            self.status.text = str(error)
            return
        # Poll locally captured frame/audio buffers twice per second.
        self.pipeline_event = Clock.schedule_interval(self.poll_live_buffers, 0.5)

    def poll_live_buffers(self, _interval):
        # Feed newly captured buffers to offline OCR and speech recognition.
        try:
            self.capture_pipeline.poll(0.5)
        except (FileNotFoundError, RuntimeError) as error:
            self.status.text = str(error)

    def stop_live_processing(self, _button):
        # Cancel the Python polling loop before stopping Android capture.
        if self.pipeline_event is not None:
            self.pipeline_event.cancel()
            self.pipeline_event = None
        # Stop the service and clear in-memory caption state.
        self.live_controller.stop()
        self.status.text = "Live captions stopped."


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