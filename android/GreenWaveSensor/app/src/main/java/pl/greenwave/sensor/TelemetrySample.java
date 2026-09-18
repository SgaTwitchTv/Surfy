package pl.greenwave.sensor;

import android.location.Location;
import android.os.Build;
import org.json.JSONException;
import org.json.JSONObject;

final class TelemetrySample {
    final Location location;
    final String deviceId;
    final String streamId;
    final long sequence;

    TelemetrySample(Location location, String deviceId, String streamId, long sequence) {
        this.location = new Location(location);
        this.deviceId = deviceId;
        this.streamId = streamId;
        this.sequence = sequence;
    }

    JSONObject toJson(String sessionId) throws JSONException {
        JSONObject json = new JSONObject();
        json.put("session_id", sessionId);
        json.put("timestamp_seconds", location.getTime() / 1000.0);
        json.put("elapsed_realtime_nanos", location.getElapsedRealtimeNanos());
        json.put("latitude", location.getLatitude());
        json.put("longitude", location.getLongitude());
        json.put("gps_accuracy_m", location.hasAccuracy() ? location.getAccuracy() : JSONObject.NULL);
        json.put("speed_mps", location.hasSpeed() ? location.getSpeed() : JSONObject.NULL);
        json.put("speed_accuracy_mps", location.hasSpeedAccuracy() ? location.getSpeedAccuracyMetersPerSecond() : JSONObject.NULL);
        json.put("heading_deg", location.hasBearing() ? location.getBearing() : JSONObject.NULL);
        json.put("heading_accuracy_deg", location.hasBearingAccuracy() ? location.getBearingAccuracyDegrees() : JSONObject.NULL);
        json.put("altitude_m", location.hasAltitude() ? location.getAltitude() : JSONObject.NULL);
        json.put("vertical_accuracy_m", location.hasVerticalAccuracy() ? location.getVerticalAccuracyMeters() : JSONObject.NULL);
        json.put("is_mock", Build.VERSION.SDK_INT >= 31 ? location.isMock() : location.isFromMockProvider());
        json.put("source", "ANDROID_FUSED");
        json.put("device_id", deviceId);
        json.put("stream_id", streamId);
        json.put("sample_sequence", sequence);
        return json;
    }
}
