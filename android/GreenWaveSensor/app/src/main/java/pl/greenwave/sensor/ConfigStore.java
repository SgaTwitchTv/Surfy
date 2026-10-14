package pl.greenwave.sensor;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.UUID;

final class ConfigStore {
    private static volatile long sessionBoundaryNanos;
    static long sessionBoundaryNanos() {return sessionBoundaryNanos;}
    private static final String PREFS = "greenwave_sensor";

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static String serverUrl(Context context) {
        return prefs(context).getString("server_url", "https://localhost:8770").replaceAll("/+$", "");
    }

    static String token(Context context) { prefs(context).edit().remove("token").apply();return CredentialVault.read(context); }
    static String sessionId(Context context) { return prefs(context).getString("session_id", ""); }

    static String deviceId(Context context) {
        SharedPreferences prefs = prefs(context);
        String value = prefs.getString("device_id", "");
        if (value.isEmpty()) {
            value = UUID.randomUUID().toString();
            prefs.edit().putString("device_id", value).apply();
        }
        return value;
    }

    static void savePairing(Context context, String url, String token, String sessionId) {
        prefs(context).edit().putString("server_url", url.replaceAll("/+$", ""))
                .remove("token").putString("session_id", sessionId).apply();
        CredentialVault.write(context, token);sessionBoundaryNanos=android.os.SystemClock.elapsedRealtimeNanos();
    }

    static void clearPairing(Context context) { CredentialVault.write(context, "");prefs(context).edit().remove("session_id").remove("token").apply(); }

    static void saveSession(Context context, String sessionId) {
        if (!sessionId.equals(sessionId(context))) sessionBoundaryNanos=android.os.SystemClock.elapsedRealtimeNanos();
        prefs(context).edit().putString("session_id", sessionId).apply();
    }

    private ConfigStore() {}
}
