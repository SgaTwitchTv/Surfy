package pl.greenwave.sensor;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.IBinder;
import android.os.Looper;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;
import java.util.UUID;

public final class LocationForegroundService extends Service {
    static final String ACTION_STOP = "pl.greenwave.sensor.STOP";
    private static final String CHANNEL_ID = "greenwave_location";
    private static final int NOTIFICATION_ID = 8765;
    private FusedLocationProviderClient fused;
    private LocationCallback callback;
    private TelemetryTransmitter transmitter;
    private String deviceId;
    private String streamId;
    private long sequence;

    @Override public void onCreate() {
        super.onCreate();
        StatusStore.resetRun();
        StatusStore.running = true;
        deviceId = ConfigStore.deviceId(this);
        streamId = UUID.randomUUID().toString();
        transmitter = new TelemetryTransmitter(this);
        fused = LocationServices.getFusedLocationProviderClient(this);
        createChannel();
        startForeground(NOTIFICATION_ID, notification());
        startUpdates();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) stopSelf();
        return START_STICKY;
    }

    private void startUpdates() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            StatusStore.lastError = "Brak zgody na dokładną lokalizację";
            stopSelf();
            return;
        }
        LocationRequest request = new LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1000)
                .setMinUpdateIntervalMillis(500)
                .setMaxUpdateDelayMillis(1000)
                .setWaitForAccurateLocation(false)
                .build();
        callback = new LocationCallback() {
            @Override public void onLocationResult(LocationResult result) {
                for (android.location.Location location : result.getLocations()) {
                    StatusStore.location(location);
                    transmitter.enqueue(new TelemetrySample(location, deviceId, streamId, sequence++));
                }
            }
        };
        fused.requestLocationUpdates(request, callback, Looper.getMainLooper())
                .addOnFailureListener(error -> StatusStore.lastError = "Fused Location: " + error.getMessage());
    }

    private void createChannel() {
        NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "Pomiary lokalizacji GreenWave",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Stałe pomiary GPS podczas kontrolowanego testu GreenWave");
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    private Notification notification() {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent openIntent = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Intent stop = new Intent(this, LocationForegroundService.class).setAction(ACTION_STOP);
        PendingIntent stopIntent = PendingIntent.getService(this, 1, stop,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Action stopAction = new Notification.Action.Builder(
                android.R.drawable.ic_media_pause, "Zatrzymaj", stopIntent).build();
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setContentTitle("GreenWave zbiera lokalizację")
                .setContentText("Próbki są wysyłane do Surface przez USB")
                .setOngoing(true).setOnlyAlertOnce(true).setContentIntent(openIntent)
                .addAction(stopAction).build();
    }

    @Override public void onDestroy() {
        StatusStore.running = false;
        if (callback != null && fused != null) fused.removeLocationUpdates(callback);
        if (transmitter != null) transmitter.stop();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
