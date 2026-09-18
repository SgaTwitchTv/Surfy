package pl.greenwave.sensor;

import android.content.Context;
import org.json.JSONObject;

final class PairingClient {
    static String pair(Context context, String url, String code) throws Exception {
        String normalized = url.trim().replaceAll("/+$", "");
        if (!normalized.startsWith("http://") && !normalized.startsWith("https://"))
            throw new IllegalArgumentException("Adres musi zaczynać się od http:// lub https://");
        JSONObject request = new JSONObject().put("code", code.trim());
        HttpJson.Response response = HttpJson.post(normalized + "/api/pair", request, null);
        if (response.status != 200) throw new IllegalStateException(response.json.optString("error", "HTTP " + response.status));
        String token = response.json.getString("token");
        String sessionId = response.json.getString("session_id");
        ConfigStore.savePairing(context, normalized, token, sessionId);
        return response.json.optString("server_version", "GreenWave");
    }
    private PairingClient() {}
}
