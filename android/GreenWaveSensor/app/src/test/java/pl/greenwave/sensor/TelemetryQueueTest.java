package pl.greenwave.sensor;

import org.junit.Test;
import static org.junit.Assert.*;

public class TelemetryQueueTest {
    @Test public void preservesOrder() {
        TelemetryQueue<Integer> queue = new TelemetryQueue<>(3);
        queue.offer(1); queue.offer(2);
        assertEquals(Integer.valueOf(1), queue.poll());
        assertEquals(Integer.valueOf(2), queue.poll());
    }

    @Test public void dropsOldestWhenBoundedBufferIsFull() {
        TelemetryQueue<Integer> queue = new TelemetryQueue<>(2);
        queue.offer(1); queue.offer(2); queue.offer(3);
        assertEquals(1, queue.dropped());
        assertEquals(Integer.valueOf(2), queue.poll());
        assertEquals(Integer.valueOf(3), queue.poll());
    }
}
