package pl.greenwave.sensor;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private EditText serverUrl;
    private EditText pairingCode;
    private TextView status;
    private final Runnable refresh = new Runnable() {
        @Override public void run() {
            status.setText(StatusStore.snapshot(MainActivity.this));
            handler.postDelayed(this, 500);
        }
    };
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        serverUrl = findViewById(R.id.serverUrl);
        pairingCode = findViewById(R.id.pairingCode);
        status = findViewById(R.id.status);
        serverUrl.setText(ConfigStore.serverUrl(this));
        findViewById(R.id.pair).setOnClickListener(view -> pair());
        findViewById(R.id.start).setOnClickListener(view -> requestAndStart());
        findViewById(R.id.stop).setOnClickListener(view -> stopService(new Intent(this, LocationForegroundService.class)));
        findViewById(R.id.battery).setOnClickListener(view -> {
            Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName()));
            startActivity(intent);
        });
    }

    private void pair() {
        String url = serverUrl.getText().toString();
        String code = pairingCode.getText().toString();
        if (code.length() != 6) { StatusStore.lastError = "Wpisz sześciocyfrowy kod parowania"; return; }
        StatusStore.lastError = "Parowanie…";
        worker.execute(() -> {
            try {
                String version = PairingClient.pair(this, url, code);
                StatusStore.lastError = "";
                StatusStore.lastAck = "Sparowano z " + version;
            } catch (Exception error) {
                StatusStore.lastError = "Parowanie: " + error.getMessage();
            }
        });
    }

    private void requestAndStart() {
        if (ConfigStore.token(this).isEmpty()) { StatusStore.lastError = "Najpierw sparuj aplikację"; return; }
        ArrayList<String> missing = new ArrayList<>();
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.ACCESS_FINE_LOCATION);
            missing.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        }
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            missing.add(Manifest.permission.POST_NOTIFICATIONS);
        if (missing.isEmpty()) startMeasurements();
        else requestPermissions(missing.toArray(new String[0]), 100);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 100 && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
            startMeasurements();
        else StatusStore.lastError = "Wymagana jest dokładna lokalizacja (Precise location)";
    }

    private void startMeasurements() {
        startForegroundService(new Intent(this, LocationForegroundService.class));
    }

    @Override protected void onStart() { super.onStart(); handler.post(refresh); }
    @Override protected void onStop() { handler.removeCallbacks(refresh); super.onStop(); }
    @Override protected void onDestroy() { worker.shutdownNow(); super.onDestroy(); }
}
