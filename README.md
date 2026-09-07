# Caption Companion

Caption Companion is a Python/Kivy Android starter application for generating
captions from video that the user explicitly chooses to share. It uses Android's
MediaProjection consent dialog, so another app is never captured silently.

## Current scope

- `main.py` provides the mobile UI and explicit capture-consent entry point.
- `android_bridge.py` requests Android MediaProjection access through `pyjnius`.
- `captioning.py` validates caption timing, normalizes recognized text, and exports SRT.
- `video_captioning.py` supports uploaded-video SRT generation and in-memory live sessions.
- `recognizers.py` provides an optional local Whisper adapter for uploaded videos.
- `recognizers.py` also provides local Vosk speech and Tesseract OCR adapters.
- `security.py` stores consent fail-closed with authenticated local data and owner-only permissions.
- `tests/` covers caption formatting and tamper-resistant consent behavior.

The caption engine is deliberately isolated from capture. There are two workflows:

1. **Uploaded video:** select an MP4, MKV, WebM, or MOV file. An injected speech/OCR
	recognizer returns `(start_seconds, end_seconds, text)` segments, and the app writes
	an SRT beside the source video. To use the included desktop adapter, install
	`requirements-desktop.txt`; the first run downloads the selected Whisper model.
2. **Live captions:** tap the capture button, approve Android's MediaProjection dialog,
	then feed recognized frame/audio segments into `LiveCaptionSession`. Captions remain
	in memory and are cleared when the session stops.

The live mode now requests Android's **Display over other apps** permission and starts a
visible foreground overlay service. This is the required Android mechanism for showing
captions above MX Player or another video app. The current overlay service is the secure
display/lifecycle foundation. After approving Android capture, tap **Start live processing**;
the Java service captures frames and playback PCM into private app buffers, and Python polls
those buffers through the local Tesseract/Vosk adapters before updating the overlay. Tap
**Stop live captions** to terminate capture and clear transient caption data.

On Android, ML Kit handles frame OCR inside the foreground service and Vosk handles
playback PCM through the local Python bridge; desktop Tesseract remains an optional
fallback for non-Android frame processing.

The Android capture service includes the bundled ML Kit Latin text model for offline
frame OCR. The repository also includes offline speech/OCR adapters. Install the Python runtimes with
`requirements-offline.txt`, then place a Vosk model under the app-private `models/`
directory. The model itself must be downloaded separately because Vosk model archives
are large binary assets; after placement, recognition runs locally without network
access. Tesseract also requires its local native `tesseract` binary. The app never
uploads video, captions, or telemetry. Subtitle output is restricted to local device
paths; sharing or downloading the SRT outside the device is always separate and user
controlled.

For Android deployment, only `python3`, Kivy, PyJNIus, and the supported Vosk recipe
are packaged. ML Kit is added as a Gradle dependency for device OCR. Tesseract and
Pillow remain desktop-only fallback dependencies, avoiding unsupported native packages
in the APK.

Vosk speech recognition needs PCM audio supplied by Android playback capture. Android
requires the `RECORD_AUDIO` runtime permission for this API; the app requests it only
when live capture starts and uses playback capture, not microphone input. MX Player
and Android must allow playback capture for the selected content; otherwise the app can
still use the bundled ML Kit OCR on visible video frames. The app does not request
microphone input and does not silently record the microphone.

## Security protocols

1. Capture starts only after the Android system consent dialog is accepted.
2. No storage or network permission is requested; playback audio requires explicit Android runtime consent.
3. Capture must run as a visible foreground service with a persistent notification.
4. Consent is denied when missing or tampered with; it is never assumed.
5. Settings files use an app-private directory and mode `0600` on supported systems.
6. Keep OCR and subtitle processing on-device unless the user separately opts in.
7. A release build should replace the fallback process key with Android Keystore-backed
	key material and enable Play App Signing.
8. Network URL destinations are rejected by the subtitle service.
9. No `INTERNET` permission is declared in the Android build configuration.
10. Raw frame/audio buffers are app-private, capped, and deleted when capture stops.
11. The MediaProjection token is cleared when the foreground service is destroyed.
12. OCR work is throttled to prevent unbounded memory growth from fast frame input.

## Run tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Build for Android

Install the Android SDK, Java 17, Buildozer, and platform tools on a Linux host.
On Ubuntu/Debian, also install the native build prerequisites before the first
Buildozer run:

```bash
sudo apt update
sudo apt install -y build-essential autoconf automake libtool libtool-bin m4 pkg-config \
	zip unzip git openjdk-17-jdk
```

Then run:

```bash
python -m pip install buildozer
buildozer android debug
buildozer android deploy run
```

The Buildozer configuration registers the PythonActivity subclass and native capture
service through supported python-for-android options, so the generated manifest does
not depend on manually copying XML. `android_src/AndroidManifest.xml` documents the
same permissions and component declarations for inspection.

The current development container has Java and Gradle but no Android SDK/ADB, so
the APK build must be performed on a configured Android build host. The container
also lacks a complete native Android build toolchain; its attempted build reached
python-for-android but stopped while rebuilding libffi because the host libtool
macros are incomplete.

## Privacy boundary

Android only grants the capture token after a visible user action. The app must
stop capture when the user presses stop, when the token is revoked, or when the
foreground service is destroyed. Do not add accessibility or notification-listener
permissions as a workaround; those permissions are broader than this feature needs.
