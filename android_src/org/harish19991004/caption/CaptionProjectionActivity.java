package org.harish19991004.caption;

import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import org.kivy.android.PythonActivity;

public final class CaptionProjectionActivity extends PythonActivity {
    private static final int REQUEST_CAPTURE = 9001;
    private static int resultCode;
    private static Intent resultData;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        if (!getIntent().getBooleanExtra("request_capture", false)) {
            return;
        }
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M
                && checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 9002);
            return;
        }
        requestProjection();
    }

    private void requestProjection() {
        MediaProjectionManager manager = (MediaProjectionManager)
                getSystemService(MEDIA_PROJECTION_SERVICE);
        startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_CAPTURE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 9002 && results.length > 0
                && results[0] == PackageManager.PERMISSION_GRANTED) {
            requestProjection();
        } else {
            finish();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int result, Intent data) {
        super.onActivityResult(requestCode, result, data);
        if (requestCode == REQUEST_CAPTURE && result == RESULT_OK && data != null) {
            resultCode = result;
            resultData = data;
            CaptionOverlayService.start(this);
        }
        finish();
    }

    public static int getResultCode() {
        return resultCode;
    }

    public static Intent getResultData() {
        return resultData;
    }

    public static void clearResult() {
        resultCode = 0;
        resultData = null;
    }
}