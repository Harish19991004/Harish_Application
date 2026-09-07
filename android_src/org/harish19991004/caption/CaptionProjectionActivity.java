package org.harish19991004.caption;

import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.net.Uri;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import org.kivy.android.PythonActivity;

public final class CaptionProjectionActivity extends PythonActivity {
    private static final int REQUEST_CAPTURE = 9001;
    private static final int REQUEST_EXPORT = 9003;
    private static int resultCode;
    private static Intent resultData;
    private static Uri exportUri;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        if (!getIntent().getBooleanExtra("request_capture", false)) {
            if (getIntent().getBooleanExtra("request_export", false)) {
                requestExport();
            }
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

    public static void startExport(android.content.Context context) {
        Intent intent = new Intent(context, CaptionProjectionActivity.class);
        intent.putExtra("request_export", true);
        context.startActivity(intent);
    }

    private void requestExport() {
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("application/x-subrip");
        intent.putExtra(Intent.EXTRA_TITLE, "captions.srt");
        startActivityForResult(intent, REQUEST_EXPORT);
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
        } else if (requestCode == REQUEST_EXPORT && result == RESULT_OK && data != null) {
            exportUri = data.getData();
        }
        finish();
    }

    public static boolean hasExportDestination() {
        return exportUri != null;
    }

    public static boolean writeExport(android.content.Context context, String content) {
        if (exportUri == null) return false;
        try (OutputStream output = context.getContentResolver().openOutputStream(exportUri, "w")) {
            if (output == null) return false;
            output.write(content.getBytes(StandardCharsets.UTF_8));
            output.flush();
            exportUri = null;
            return true;
        } catch (Exception error) {
            return false;
        }
    }

    public static int getResultCode() {
        return resultCode;
    }

    public static Intent getResultData() {
        return resultData;
    }

    public static boolean hasCaptureResult() {
        return resultCode == RESULT_OK && resultData != null;
    }

    public static void clearResult() {
        resultCode = 0;
        resultData = null;
    }
}