package pl.greenwave.sensor;

import java.util.ArrayDeque;

final class TelemetryQueue<T> {
    private final int capacity;
    private final ArrayDeque<T> values = new ArrayDeque<>();
    private int dropped;

    TelemetryQueue(int capacity) {
        if (capacity < 1) throw new IllegalArgumentException("capacity must be positive");
        this.capacity = capacity;
    }

    synchronized void offer(T value) {
        if (values.size() == capacity) { values.removeFirst(); dropped++; }
        values.addLast(value);
    }
    synchronized T peek() { return values.peekFirst(); }
    synchronized T poll() { return values.pollFirst(); }
    synchronized int size() { return values.size(); }
    synchronized int dropped() { return dropped; }
}
