package pl.greenwave.sensor;
import org.junit.Test;
import static org.junit.Assert.*;
public class SessionEpochTest {
 @Test public void oldSessionIsNeverRetaggedToNewRun() {assertFalse(SessionEpoch.belongs("old",SessionEpoch.fingerprint("synthetic-token"),"new","synthetic-token"));}
 @Test public void rePairingInvalidatesQueuedCredentialEpoch() {assertFalse(SessionEpoch.belongs("same",SessionEpoch.fingerprint("old-synthetic-token"),"same","new-synthetic-token"));assertTrue(SessionEpoch.belongs("same",SessionEpoch.fingerprint("new-synthetic-token"),"same","new-synthetic-token"));}
}
