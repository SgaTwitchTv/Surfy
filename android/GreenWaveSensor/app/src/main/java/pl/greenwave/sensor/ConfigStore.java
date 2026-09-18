package pl.greenwave.sensor;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.UUID;

final class ConfigStore {
    private static final String PREFS = "greenwave_sensor";

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static String serverUrl(Context context) {
        return prefs(context).getString("server_url", "http://localhost:8765").replaceAll("/+$", "");
    }

    static String token(Context context) { return prefs(context).getString("token", ""); }
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
                .putString("token", token).putString("session_id", sessionId).apply();
    }

    static void saveSession(Context context, String sessionId) {
        prefs(context).edit().putString("session_id", sessionId).apply();
    }

    private ConfigStore() {}
}
