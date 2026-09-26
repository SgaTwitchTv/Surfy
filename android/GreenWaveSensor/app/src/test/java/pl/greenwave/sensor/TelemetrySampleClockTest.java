package pl.greenwave.sensor;

import org.junit.Test;
import static org.junit.Assert.*;

public class TelemetrySampleClockTest {
    @Test public void captureAgeIsMeasuredOnTheSameMonotonicClock() {
        assertEquals(250_000_000L,
                TelemetrySample.captureAgeNanos(1_000_000_000L, 1_250_000_000L));
    }

    @Test(expected = IllegalArgumentException.class)
    public void sendTimeBeforeCaptureIsRejected() {
        TelemetrySample.captureAgeNanos(2_000_000_000L, 1_999_999_999L);
    }
}
