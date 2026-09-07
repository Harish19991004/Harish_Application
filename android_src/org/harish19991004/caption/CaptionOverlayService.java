package org.harish19991004.caption;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.provider.Settings;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.TextView;

public final class CaptionOverlayService extends Service {
    private static final String CHANNEL_ID = "caption_overlay";
    private static CaptionOverlayService instance;
    private WindowManager windowManager;
    private TextView captionView;

    public static void start(Context context) {
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
            instance.captionView.post(() -> instance.captionView.setText(text));
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createNotificationChannel();
        startForeground(42, buildNotification());
        if (Settings.canDrawOverlays(this)) {
            showCaptionWindow();
        }
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
        if (windowManager != null && captionView != null) {
            windowManager.removeView(captionView);
        }
        instance = null;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}