"""Android-only permission bridge with a safe non-Android fallback."""


class AndroidCaptureBridge:
    """Request MediaProjection consent without silently capturing another app."""

    def request_capture_permission(self) -> bool:
        # Import Android bindings only on Android so unit tests run on desktop Python.
        try:
            from jnius import autoclass
        except ImportError:
            return False
        # Resolve the current Android activity supplied by Python-for-Android.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        # Launch the transparent Java activity that owns the consent callback.
        intent = autoclass("android.content.Intent")(activity, autoclass(
            "org.harish19991004.caption.CaptionProjectionActivity"
        ))
        # Mark this explicit launch as a user-requested capture operation.
        intent.putExtra("request_capture", True)
        # Start the permission activity; it starts capture only after approval.
        activity.startActivity(intent)
        # Report that the request was sent, not that access was granted.
        return True

    def request_overlay_permission(self) -> bool:
        # Import Android bindings only on Android so desktop tests remain dependency-free.
        try:
            from jnius import autoclass
        except ImportError:
            return False
        # Resolve the current Android activity.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        # Resolve Android's overlay permission manager.
        settings = autoclass("android.provider.Settings")
        # Resolve the application package URI helper.
        uri = autoclass("android.net.Uri")
        # Open the system page where the user can enable draw-over-other-apps access.
        intent = autoclass("android.content.Intent")(
            settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            uri.parse("package:" + activity.getPackageName()),
        )
        # Launch the settings page; Android still controls the final decision.
        activity.startActivity(intent)
        # Report only that the settings page was opened.
        return True

    def start_caption_overlay(self) -> bool:
        # Import Android bindings only on Android.
        try:
            from jnius import autoclass
        except ImportError:
            return False
        # Resolve the current Android activity.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        settings = autoclass("android.provider.Settings")
        projection = autoclass("org.harish19991004.caption.CaptionProjectionActivity")
        if not settings.canDrawOverlays(activity) or not projection.hasCaptureResult():
            return False
        # Resolve the overlay service implemented by the Android build.
        service = autoclass("org.harish19991004.caption.CaptionOverlayService")
        # Start the visible foreground capture and overlay service.
        service.start(activity)
        # Report that the service start request was sent.
        return True

    def capture_permission_granted(self) -> bool:
        try:
            from jnius import autoclass
        except ImportError:
            return False
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        projection = autoclass("org.harish19991004.caption.CaptionProjectionActivity")
        return bool(projection.hasCaptureResult())

    def stop_caption_overlay(self) -> None:
        # Import Android bindings only on Android.
        try:
            from jnius import autoclass
        except ImportError:
            return
        # Resolve the current Android activity.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        # Resolve the overlay service implemented by the Android build.
        service = autoclass("org.harish19991004.caption.CaptionOverlayService")
        # Stop the foreground overlay service and remove its window.
        service.stop(activity)

    def update_caption_overlay(self, text: str) -> None:
        # Import Android bindings only on Android.
        try:
            from jnius import autoclass
        except ImportError:
            return
        # Resolve the overlay service class.
        service = autoclass("org.harish19991004.caption.CaptionOverlayService")
        # Send recognized local text to the visible overlay.
        service.updateCaption(text)

    def capture_buffer_directory(self) -> str:
        # Return the app-private buffer directory used by the Java service.
        try:
            from jnius import autoclass
        except ImportError:
            return "capture"
        # Resolve the current Android activity.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        # Ask the service for its private cache location.
        service = autoclass("org.harish19991004.caption.CaptionOverlayService")
        return str(service.bufferDirectory(activity))

    def model_directory(self) -> str:
        # Return the app-private location where the user places the Vosk model.
        try:
            from jnius import autoclass
        except ImportError:
            return "models"
        # Resolve the current Android activity.
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        # Keep model files in private app storage rather than shared storage.
        return str(activity.getFilesDir().getAbsolutePath()) + "/models"