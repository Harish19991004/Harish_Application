package org.harish19991004.caption;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.pm.ServiceInfo;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Bitmap;
import android.media.AudioFormat;
import android.media.AudioPlaybackCaptureConfiguration;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.IBinder;
import android.os.Handler;
import android.os.HandlerThread;
import android.media.Image;
import android.media.ImageReader;
import android.provider.Settings;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.TextView;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.util.concurrent.atomic.AtomicBoolean;

public final class CaptionOverlayService extends Service {
    private static final String CHANNEL_ID = "caption_overlay";
    private static CaptionOverlayService instance;
    private WindowManager windowManager;
    private TextView captionView;
    private MediaProjection projection;
    private ImageReader imageReader;
    private android.hardware.display.VirtualDisplay virtualDisplay;
    private HandlerThread captureThread;
    private Handler captureHandler;
    private AudioRecord audioRecord;
    private Thread audioThread;
    private volatile boolean capturing;
    private TextRecognizer textRecognizer;
    private final AtomicBoolean ocrInFlight = new AtomicBoolean(false);
    private static final int MAX_OVERLAY_TEXT = 2000;
    private static final long MAX_AUDIO_BYTES = 20L * 1024L * 1024L;

    public static void start(Context context) {
        if (!Settings.canDrawOverlays(context) || !CaptionProjectionActivity.hasCaptureResult()) {
            return;
        }
        Intent intent = new Intent(context, CaptionOverlayService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }
    }

    public static void stop(Context context) {
        context.stopService(new Intent(context, CaptionOverlayService.class));
    }

    public static void updateCaption(String text) {
        if (instance != null && instance.captionView != null) {
            String safeText = text == null ? "" : text.substring(0, Math.min(text.length(), MAX_OVERLAY_TEXT));
            instance.captionView.post(() -> instance.captionView.setText(safeText));
        }
    }

    public static String bufferDirectory(Context context) {
        return new File(context.getFilesDir(), "capture").getAbsolutePath();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createNotificationChannel();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(42, buildNotification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(42, buildNotification());
        }
        textRecognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        if (Settings.canDrawOverlays(this)) {
            showCaptionWindow();
        }
        startCapturePipeline();
    }

    private void startCapturePipeline() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.LOLLIPOP) return;
        Intent data = CaptionProjectionActivity.getResultData();
        if (data == null || !CaptionProjectionActivity.hasCaptureResult()) {
            stopSelf();
            return;
        }
        MediaProjectionManager manager = (MediaProjectionManager)
                getSystemService(MEDIA_PROJECTION_SERVICE);
        projection = manager.getMediaProjection(CaptionProjectionActivity.getResultCode(), data);
        if (projection == null) {
            stopSelf();
            return;
        }
        File directory = new File(bufferDirectory(this));
        deleteRecursively(directory);
        directory.mkdirs();
        captureThread = new HandlerThread("caption-capture");
        captureThread.start();
        captureHandler = new Handler(captureThread.getLooper());
        projection.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {
                stopSelf();
            }
        }, captureHandler);
        imageReader = ImageReader.newInstance(720, 1280, android.graphics.PixelFormat.RGBA_8888, 2);
        imageReader.setOnImageAvailableListener(reader -> writeLatestFrame(reader), captureHandler);
        virtualDisplay = projection.createVirtualDisplay("CaptionCompanion",
                720, 1280, getResources().getDisplayMetrics().densityDpi,
                android.hardware.display.DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(), null, captureHandler);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) startPlaybackCapture(directory);
    }

    private void writeLatestFrame(ImageReader reader) {
        Image image = reader.acquireLatestImage();
        if (image == null) return;
        try {
                Image.Plane plane = image.getPlanes()[0];
                ByteBuffer buffer = plane.getBuffer();
                int width = image.getWidth();
                int height = image.getHeight();
                int pixelStride = plane.getPixelStride();
                int rowStride = plane.getRowStride();
                int rowPadding = rowStride - pixelStride * width;
                Bitmap bitmap = Bitmap.createBitmap(
                    width + rowPadding / pixelStride, height, Bitmap.Config.ARGB_8888);
                bitmap.copyPixelsFromBuffer(buffer);
                bitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height);
            File output = new File(bufferDirectory(this), "frame.png");
            File temporary = new File(bufferDirectory(this), "frame.png.tmp");
            try (FileOutputStream stream = new FileOutputStream(temporary)) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 80, stream);
            }
            if (!temporary.renameTo(output)) {
                deleteFile(temporary);
                bitmap.recycle();
                return;
            }
            Bitmap ocrBitmap = bitmap.copy(Bitmap.Config.ARGB_8888, false);
            runLocalOcr(ocrBitmap);
            bitmap.recycle();
        } catch (Exception ignored) {
            // A transient frame must not stop the foreground capture service.
        } finally {
            image.close();
        }
    }

    private void runLocalOcr(Bitmap bitmap) {
        if (!ocrInFlight.compareAndSet(false, true)) {
            bitmap.recycle();
            return;
        }
        InputImage input = InputImage.fromBitmap(bitmap, 0);
        textRecognizer.process(input)
                .addOnSuccessListener(result -> {
                    String text = result.getText().trim();
                    if (!text.isEmpty()) updateCaption(text);
                    bitmap.recycle();
                    ocrInFlight.set(false);
                })
                .addOnFailureListener(error -> {
                    bitmap.recycle();
                    ocrInFlight.set(false);
                });
    }

    private void startPlaybackCapture(File directory) {
        AudioPlaybackCaptureConfiguration configuration = new AudioPlaybackCaptureConfiguration.Builder(projection)
                .addMatchingUsage(android.media.AudioAttributes.USAGE_MEDIA)
                .build();
        AudioFormat format = new AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setSampleRate(16000)
                .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                .build();
        audioRecord = new AudioRecord.Builder()
                .setAudioFormat(format)
                .setAudioPlaybackCaptureConfig(configuration)
                .setBufferSizeInBytes(32000)
                .build();
        if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
            audioRecord.release();
            return;
        }
        capturing = true;
        audioThread = new Thread(() -> {
            byte[] audio = new byte[16000];
            audioRecord.startRecording();
            while (capturing) {
                int count = audioRecord.read(audio, 0, audio.length);
                if (count > 0) {
                    File audioFile = new File(directory, "audio.pcm");
                    if (audioFile.length() >= MAX_AUDIO_BYTES) {
                        deleteFile(audioFile);
                    }
                    try (FileOutputStream output = new FileOutputStream(audioFile, true)) {
                        output.write(audio, 0, count);
                    } catch (Exception ignored) {
                        // A transient audio write must not crash the service.
                    }
                }
            }
            audioRecord.stop();
            audioRecord.release();
        }, "caption-audio");
        audioThread.start();
    }

    private void showCaptionWindow() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        captionView = new TextView(this);
        captionView.setText("Live captions starting...");
        captionView.setTextColor(Color.WHITE);
        captionView.setTextSize(20);
        captionView.setBackgroundColor(0xAA000000);
        captionView.setPadding(24, 12, 24, 12);
        int windowType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                windowType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.BOTTOM;
        windowManager.addView(captionView, params);
    }

    private Notification buildNotification() {
        return new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("Caption Companion")
                .setContentText("Live captions are active on this device")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Live captions", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    @Override
    public void onDestroy() {
        capturing = false;
        if (audioThread != null) {
            audioThread.interrupt();
            try {
                audioThread.join(1000);
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }
        if (virtualDisplay != null) virtualDisplay.release();
        if (imageReader != null) imageReader.close();
        if (projection != null) projection.stop();
        if (captureThread != null) captureThread.quitSafely();
        if (textRecognizer != null) textRecognizer.close();
        if (windowManager != null && captionView != null) {
            windowManager.removeView(captionView);
        }
        deleteRecursively(new File(bufferDirectory(this)));
        CaptionProjectionActivity.clearResult();
        instance = null;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private static void deleteFile(File file) {
        if (file.exists()) file.delete();
    }

    private static void deleteRecursively(File file) {
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) deleteRecursively(child);
            }
        }
        deleteFile(file);
    }
}