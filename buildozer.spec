[app]
# Human-readable package name.
title = Caption Companion
# Python package name used by Android.
package.name = captioncompanion
# Reverse-domain package identifier.
package.domain = org.harish19991004
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
requirements = python3,kivy,pyjnius,vosk,pytesseract
# Keep orientation stable for caption overlays.
orientation = portrait
# Do not request microphone, storage, or network permissions by default.
android.permissions = FOREGROUND_SERVICE,FOREGROUND_SERVICE_MEDIA_PROJECTION,SYSTEM_ALERT_WINDOW
# Use a foreground service for visible, user-started capture.
android.add_src = android_src

[buildozer]
# Keep generated build output outside the source tree.
log_level = 2
# Do not warn about an unversioned build directory.
warn_on_root = 1