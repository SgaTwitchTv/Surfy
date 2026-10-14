package pl.greenwave.sensor;

import android.content.Context;
import android.os.SystemClock;
import org.json.JSONObject;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

final class TelemetryTransmitter {
    private final Context context;
    private final TelemetryQueue<TelemetrySample> queue = new TelemetryQueue<>(300);
    private final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor();
    private final AtomicBoolean drainQueued = new AtomicBoolean();
    private volatile boolean stopped;
    private int consecutiveFailures;

    TelemetryTransmitter(Context context) { this.context = context.getApplicationContext(); }

    void enqueue(TelemetrySample sample) {
        queue.offer(sample);
        updateQueueStatus();
        schedule(0);
    }

    void stop() { stopped = true; worker.shutdownNow(); }

    private void schedule(long delayMs) {
        if (stopped || !drainQueued.compareAndSet(false, true)) return;
        worker.schedule(() -> {
            drainQueued.set(false);
            drain();
        }, delayMs, TimeUnit.MILLISECONDS);
    }

    private void drain() {
        if (stopped) return;
        TelemetrySample sample = queue.peek();
        if (sample == null) return;
        String token = ConfigStore.token(context);
        if (token.isEmpty()) { StatusStore.lastError = "Brak parowania z serwerem"; return; }
        try {
            String base = ConfigStore.serverUrl(context);
            if (ConfigStore.sessionId(context).isEmpty()) { refreshSession(base); queue.clear();updateQueueStatus();return; }
            if (!SessionEpoch.belongs(sample.appSessionId,sample.credentialEpoch,ConfigStore.sessionId(context),token)) {queue.clear();updateQueueStatus();return;}
            HttpJson.Response response = HttpJson.post(base + "/school/api/v1/device/position",
                    sample.toJson(ConfigStore.sessionId(context), SystemClock.elapsedRealtimeNanos()), token);
            if (response.status == 409 && refreshSession(base)) {
                queue.clear();updateQueueStatus();
                schedule(0);
                return;
            }
            if (response.status != 200) {
                if (response.status == 403) {ConfigStore.clearPairing(context);queue.clear();updateQueueStatus();StatusStore.lastError = "Parowanie cofnięte lub nowy boot. Sparuj ponownie.";}
                else retry("HTTP " + response.status + ": " + response.json.optString("error", "błąd serwera"));
                return;
            }
            queue.poll();
            consecutiveFailures = 0;
            StatusStore.acknowledged++;
            StatusStore.lastAck = String.format("seq %d @ %.1f s", sample.sequence, SystemClock.elapsedRealtime() / 1000.0);
            StatusStore.lastError = "";
            updateQueueStatus();
            if (queue.peek() != null) schedule(0);
        } catch (Exception error) {
            retry("Błąd transportu: " + error.getClass().getSimpleName());
        }
    }

    private boolean refreshSession(String base) {
        try {
            HttpJson.Response response = HttpJson.get(base + "/school/api/v1/device/session", ConfigStore.token(context));
            if (response.status == 403) { ConfigStore.clearPairing(context); queue.clear();updateQueueStatus();StatusStore.lastError="Sparuj ponownie";return false;}
            if (response.status != 200) return false;
            JSONObject data=response.json.getJSONObject("data");
            ConfigStore.saveSession(context, data.isNull("app_session_id") ? "" : data.getString("app_session_id"));
            queue.clear();updateQueueStatus();
            StatusStore.lastError = "Sesja serwera została odświeżona";
            return true;
        } catch (Exception error) {
            retry("Nie udało się odświeżyć sesji: " + error.getMessage());
            return false;
        }
    }

    private void retry(String message) {
        consecutiveFailures++;
        StatusStore.lastError = message;
        long delay = Math.min(30_000, 500L << Math.min(6, consecutiveFailures - 1));
        schedule(delay);
    }

    private void updateQueueStatus() {
        StatusStore.pending = queue.size();
        StatusStore.dropped = queue.dropped();
    }
}
