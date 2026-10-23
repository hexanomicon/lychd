package org.lychd.voice;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class VoiceWorkersTest {
    @Test void ordinaryBlockCannotConsumeStopWorkerAndQueuesAreBounded() throws Exception {
        ControlTransport noNetwork = new ControlTransport() {
            @Override public Response request(String method, String path, byte[] body) { throw new AssertionError("No network expected"); }
            @Override public void close() { }
        };
        CountDownLatch ordinaryEntered = new CountDownLatch(1), finishEntered = new CountDownLatch(1),
                stopEntered = new CountDownLatch(1), release = new CountDownLatch(1);
        try (VoiceWorkers workers = new VoiceWorkers(noNetwork)) {
            assertTrue(workers.ordinary().offer(() -> {
                ordinaryEntered.countDown();
                try { release.await(); } catch (InterruptedException exception) { Thread.currentThread().interrupt(); }
            }));
            assertTrue(ordinaryEntered.await(1, TimeUnit.SECONDS));
            assertTrue(workers.ordinary().offer(() -> { }));
            assertFalse(workers.ordinary().offer(() -> { }));
            assertTrue(workers.finish().offer(() -> {
                finishEntered.countDown();
                try { release.await(); } catch (InterruptedException exception) { Thread.currentThread().interrupt(); }
            }));
            assertTrue(finishEntered.await(1, TimeUnit.SECONDS));
            assertTrue(workers.finish().offer(() -> { }));
            assertFalse(workers.finish().offer(() -> { }));
            assertTrue(workers.stop().offer(stopEntered::countDown));
            assertTrue(stopEntered.await(1, TimeUnit.SECONDS));
        } finally { release.countDown(); }
    }
}
