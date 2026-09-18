package pl.greenwave.sensor;

import android.content.Context;
import android.location.Location;
import android.os.SystemClock;
import java.util.Locale;

final class StatusStore {
    static volatile boolean running;
    static volatile int produced;
    static volatile int acknowledged;
    static volatile int pending;
    static volatile int dropped;
    static volatile long lastLocationElapsedMs;
    static volatile float accuracyM = Float.NaN;
    static volatile float speedMps = Float.NaN;
    static volatile float speedAccuracyMps = Float.NaN;
    static volatile String provider = "—";
    static volatile String lastError = "";
    static volatile String lastAck = "—";

    static void resetRun() {
        produced = acknowledged = pending = dropped = 0;
        lastLocationElapsedMs = 0;
        accuracyM = speedMps = speedAccuracyMps = Float.NaN;
        provider = "—";
        lastError = "";
        lastAck = "—";
    }

    static void location(Location location) {
        produced++;
        lastLocationElapsedMs = SystemClock.elapsedRealtime();
        accuracyM = location.hasAccuracy() ? location.getAccuracy() : Float.NaN;
        speedMps = location.hasSpeed() ? location.getSpeed() : Float.NaN;
        speedAccuracyMps = location.hasSpeedAccuracy() ? location.getSpeedAccuracyMetersPerSecond() : Float.NaN;
        provider = location.getProvider();
    }

    static String snapshot(Context context) {
        boolean paired = !ConfigStore.token(context).isEmpty();
        double age = lastLocationElapsedMs == 0 ? Double.NaN : (SystemClock.elapsedRealtime() - lastLocationElapsedMs) / 1000.0;
        return String.format(Locale.US,
                "Połączenie: %s\nUsługa GPS: %s\nŹródło Androida: %s\n" +
                "Próbki utworzone: %d\nPotwierdzone przez Surface: %d\nW kolejce: %d\nOdrzucone z pełnej kolejki: %d\n" +
                "Wiek ostatniej lokalizacji: %s s\nDokładność: %s m\nPrędkość urządzenia: %s km/h\nDokładność prędkości: %s km/h\n" +
                "Ostatnie potwierdzenie: %s\nOstatni błąd: %s",
                paired ? "sparowane" : "brak parowania", running ? "DZIAŁA" : "zatrzymana", provider,
                produced, acknowledged, pending, dropped, number(age), number(accuracyM),
                number(Float.isNaN(speedMps) ? Double.NaN : speedMps * 3.6),
                number(Float.isNaN(speedAccuracyMps) ? Double.NaN : speedAccuracyMps * 3.6),
                lastAck, lastError.isEmpty() ? "brak" : lastError);
    }

    private static String number(double value) { return Double.isNaN(value) ? "—" : String.format(Locale.US, "%.1f", value); }
    private StatusStore() {}
}
