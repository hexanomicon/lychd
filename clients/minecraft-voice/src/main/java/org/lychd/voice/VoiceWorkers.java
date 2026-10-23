package org.lychd.voice;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/** Ordinary HTTP can never consume the reserved stop worker or its one-entry queue. */
final class VoiceWorkers implements AutoCloseable {
    private final ThreadPoolExecutor ordinary = worker("lychd-voice-control");
    private final ThreadPoolExecutor finish = worker("lychd-voice-finish");
    private final ThreadPoolExecutor stop = worker("lychd-voice-stop");
    private final ControlTransport transport;
    VoiceWorkers(ControlTransport transport) { this.transport = transport; }
    VoiceController.Lane ordinary() { return task -> offer(ordinary, task); }
    VoiceController.Lane finish() { return task -> offer(finish, task); }
    VoiceController.Lane stop() { return task -> offer(stop, task); }
    private static ThreadPoolExecutor worker(String name) {
        return new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(1), work -> {
            Thread thread = new Thread(work, name); thread.setDaemon(true); return thread;
        }, new ThreadPoolExecutor.AbortPolicy());
    }
    private static boolean offer(ThreadPoolExecutor executor, Runnable task) {
        try { executor.execute(task); return true; }
        catch (java.util.concurrent.RejectedExecutionException exception) { return false; }
    }
    @Override public void close() {
        ordinary.shutdownNow(); finish.shutdownNow(); stop.shutdown();
        boolean interrupted = false;
        try { stop.awaitTermination(2200, TimeUnit.MILLISECONDS); }
        catch (InterruptedException exception) { interrupted = true; }
        transport.close(); stop.shutdownNow();
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(300);
        for (ThreadPoolExecutor worker : new ThreadPoolExecutor[] {ordinary, finish, stop}) {
            try { worker.awaitTermination(Math.max(1, deadline - System.nanoTime()), TimeUnit.NANOSECONDS); }
            catch (InterruptedException exception) { interrupted = true; }
        }
        if (interrupted) Thread.currentThread().interrupt();
        // Timeout is deliberately not projected as a device-off or applied-stop acknowledgement.
    }
}
