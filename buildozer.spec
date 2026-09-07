[app]
# Human-readable package name.
title = Caption Companion
# Python package name used by Android.
package.name = captioncompanion
# Reverse-domain package identifier.
package.domain = org.harish19991004
# Semantic application version required by Buildozer.
version = 0.1.0
# Source directory containing the application entry point.
source.dir = .
# Include Python and UI source files in the package.
source.include_exts = py,kv,png,jpg,atlas
# Application entry point.
entrypoint = main.py
# Minimum Android version with MediaProjection support.
android.minapi = 26
# Target Android API level.
android.api = 35
# Required runtime Python dependencies.
requirements = python3,kivy,pyjnius,vosk
# Bundle ML Kit's Latin text model for offline frame OCR.
android.gradle_dependencies = com.google.mlkit:text-recognition:16.0.1
# Enable AndroidX required by current ML Kit dependencies.
android.enable_androidx = True
# Enable Java 8 language features used by the Android capture service.
android.add_compile_options = sourceCompatibility = 1.8, targetCompatibility = 1.8
# Keep orientation stable for caption overlays.
orientation = portrait
# Do not request microphone, storage, or network permissions by default.
android.permissions = FOREGROUND_SERVICE,FOREGROUND_SERVICE_MEDIA_PROJECTION,SYSTEM_ALERT_WINDOW,RECORD_AUDIO
# Use a foreground service for visible, user-started capture.
android.add_src = android_src
# Register the native capture service in the generated Android manifest.
p4a.extra_args = --native-service=org.harish19991004.caption.CaptionOverlayService
# Use the PythonActivity subclass so the normal Kivy UI remains the launcher screen.
android.activity_class_name = org.harish19991004.caption.CaptionProjectionActivity

[buildozer]
# Keep generated build output outside the source tree.
log_level = 2
# Do not warn about an unversioned build directory.
warn_on_root = 1