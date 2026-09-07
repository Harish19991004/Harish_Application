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
display/lifecycle foundation; connect its captured frames or playback audio to an offline
ML Kit, Vosk, or Whisper adapter to populate recognized text.

The repository includes offline speech/OCR adapters. Install the Python runtimes with
`requirements-offline.txt`, then place a Vosk model under the app-private `models/`
directory. The model itself must be downloaded separately because Vosk model archives
are large binary assets; after placement, recognition runs locally without network
access. Tesseract also requires its local native `tesseract` binary. The app never
uploads video, captions, or telemetry. Subtitle output is restricted to local device
paths; sharing or downloading the SRT outside the device is always separate and user
controlled.

Vosk speech recognition needs PCM audio supplied by Android playback capture. MX Player
and Android must allow playback capture for the selected content; otherwise the app can
still use Tesseract OCR on visible video frames. The app does not request microphone
access and does not silently record the microphone.

## Security protocols

1. Capture starts only after the Android system consent dialog is accepted.
2. No microphone, storage, or network permission is requested by default.
3. Capture must run as a visible foreground service with a persistent notification.
4. Consent is denied when missing or tampered with; it is never assumed.
5. Settings files use an app-private directory and mode `0600` on supported systems.
6. Keep OCR and subtitle processing on-device unless the user separately opts in.
7. A release build should replace the fallback process key with Android Keystore-backed
	key material and enable Play App Signing.
8. Network URL destinations are rejected by the subtitle service.
9. No `INTERNET` permission is declared in the Android build configuration.

## Run tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Build for Android

Install the Android SDK, Java 17, Buildozer, and platform tools on a Linux host.
Then run:

```bash
python -m pip install buildozer
buildozer android debug
buildozer android deploy run
```

The current development container has Java and Gradle but no Android SDK/ADB, so
the APK build must be performed on a configured Android build host.

## Privacy boundary

Android only grants the capture token after a visible user action. The app must
stop capture when the user presses stop, when the token is revoked, or when the
foreground service is destroyed. Do not add accessibility or notification-listener
permissions as a workaround; those permissions are broader than this feature needs.
