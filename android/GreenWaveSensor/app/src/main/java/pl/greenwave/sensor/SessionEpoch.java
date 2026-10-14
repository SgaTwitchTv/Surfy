package pl.greenwave.sensor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** In-memory binding of a queued sample to its captured session and credential epoch. */
final class SessionEpoch {
    static String fingerprint(String token) {
        try {
            byte[] hash=MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8));
            StringBuilder result=new StringBuilder();for(byte value:hash)result.append(String.format("%02x",value&255));return result.toString();
        } catch(Exception error) {throw new IllegalStateException("Credential fingerprint unavailable");}
    }
    static boolean belongs(String capturedSession,String capturedCredential,String currentSession,String currentToken) {
        return capturedSession.equals(currentSession)&&capturedCredential.equals(fingerprint(currentToken));
    }
    private SessionEpoch() {}
}
