package pl.greenwave.sensor;

import android.content.Context;
import org.json.JSONObject;

final class PairingClient {
    static String pair(Context context, String url, String code) throws Exception {
        String normalized = url.trim().replaceAll("/+$", "");
        if (!normalized.startsWith("https://"))
            throw new IllegalArgumentException("Portal szkolny wymaga HTTPS i zaufanego certyfikatu");
        java.net.URI endpoint = new java.net.URI(normalized);
        if (endpoint.getHost() == null || endpoint.getUserInfo() != null || endpoint.getQuery() != null || endpoint.getFragment() != null || (endpoint.getPath() != null && !endpoint.getPath().isEmpty()))
            throw new IllegalArgumentException("Podaj główny adres HTTPS, bez ścieżki i danych logowania");
        if (!code.trim().matches("[0-9]{6}")) throw new IllegalArgumentException("Kod musi mieć sześć cyfr ASCII");
        String label = android.os.Build.MODEL == null ? "Android GPS" : android.os.Build.MODEL;
        if (label.length() > 80) label = label.substring(0,80);
        JSONObject request = new JSONObject().put("code", code.trim()).put("client_device_id", ConfigStore.deviceId(context)).put("label", label);
        HttpJson.Response response = HttpJson.post(normalized + "/school/api/v1/device/pair", request, null);
        if (response.status != 200) throw new IllegalStateException(response.json.optString("error", "HTTP " + response.status));
        JSONObject data = response.json.getJSONObject("data");
        String token = data.getString("device_token");
        String sessionId = data.isNull("app_session_id") ? "" : data.getString("app_session_id");
        ConfigStore.savePairing(context, normalized, token, sessionId);
        return data.optString("server_version", "GreenWave");
    }
    private PairingClient() {}
}
