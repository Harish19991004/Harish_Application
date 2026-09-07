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
        # Resolve the Android media projection manager.
        media_projection = activity.getSystemService("media_projection")
        # Create the system consent intent for screen capture.
        intent = media_projection.createScreenCaptureIntent()
        # Launch the Android consent dialog; the user must approve it.
        activity.startActivityForResult(intent, 9001)
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
        # Resolve the overlay service implemented by the Android build.
        service = autoclass("org.harish19991004.caption.CaptionOverlayService")
        # Start the visible foreground overlay service.
        service.start(activity)
        # Report that the service start request was sent.
        return True

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