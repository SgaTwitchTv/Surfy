package pl.greenwave.sensor;

import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class HttpJson {
    static Response post(String url, JSONObject body, String token) throws Exception {
        HttpURLConnection connection = open(url);
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        if (token != null && !token.isEmpty()) connection.setRequestProperty("X-GreenWave-Token", token);
        byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(bytes.length);
        try (OutputStream stream = connection.getOutputStream()) { stream.write(bytes); }
        return response(connection);
    }

    static Response get(String url) throws Exception {
        HttpURLConnection connection = open(url);
        connection.setRequestMethod("GET");
        return response(connection);
    }

    private static HttpURLConnection open(String url) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setConnectTimeout(4000);
        connection.setReadTimeout(4000);
        connection.setUseCaches(false);
        return connection;
    }

    private static Response response(HttpURLConnection connection) throws Exception {
        int status = connection.getResponseCode();
        InputStream raw = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
        StringBuilder text = new StringBuilder();
        if (raw != null) try (BufferedReader reader = new BufferedReader(new InputStreamReader(raw, StandardCharsets.UTF_8))) {
            String line; while ((line = reader.readLine()) != null) text.append(line);
        }
        connection.disconnect();
        JSONObject json = text.length() == 0 ? new JSONObject() : new JSONObject(text.toString());
        return new Response(status, json);
    }

    static final class Response {
        final int status;
        final JSONObject json;
        Response(int status, JSONObject json) { this.status = status; this.json = json; }
    }
    private HttpJson() {}
}
