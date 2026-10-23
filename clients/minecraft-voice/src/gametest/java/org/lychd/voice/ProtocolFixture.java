package org.lychd.voice;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;

/** Raw local v1 fixture: synthetic client ingress/projection, never native game or audio evidence. */
final class ProtocolFixture {
    static final int PORT = 18186;
    static final long INSTRUCTION_TIMEOUT = 10000;
    static final String CONTEXT_ONE = "1".repeat(64);
    static final String CONTEXT_TWO = "2".repeat(64);
    private final HttpServer server;
    private final ThreadPoolExecutor executor;
    private final String token;
    private final String session = UUID.randomUUID().toString();
    private final long startedAt = System.currentTimeMillis();
    private final long sessionExpiry = startedAt + 120000;
    private final Map<String, byte[]> operations = new LinkedHashMap<>();
    private final Map<Integer, String> recordIds = new LinkedHashMap<>();
    private final Map<Integer, String> holdIds = new LinkedHashMap<>();
    private final Map<String, Map<String, Object>> holdEnvelopes = new LinkedHashMap<>();
    private final java.util.Set<String> releasedHolds = new java.util.HashSet<>();
    private final Map<Integer, String> stopIds = new LinkedHashMap<>();
    private final AtomicReference<String> failure = new AtomicReference<>();
    private String context = CONTEXT_ONE;
    private long generation = 1;
    private byte[] lastRecord, lastStop;
    private String pendingRecord, pendingPhase = "recording_pending";
    private int records, stops, stateReads, holds, releases, heldStops;
    private boolean blockNext, pendingNext, closed;
    private volatile Gate gate;

    static final class Gate {
        private final CountDownLatch release = new CountDownLatch(1);
        volatile long enteredAt, releasedAt;
        volatile boolean stopBeforeRelease;
        void release() { release.countDown(); }
    }

    ProtocolFixture(Profile profile) throws IOException {
        FixtureObservation.check(profile.port == PORT && profile.serverAddress.equals("localhost:25573"),
                "synthetic profile target");
        token = profile.token;
        executor = new ThreadPoolExecutor(3, 3, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(8), work -> {
            Thread thread = new Thread(work, "lychd-fixture-http");
            thread.setDaemon(true);
            return thread;
        }, new ThreadPoolExecutor.AbortPolicy());
        server = HttpServer.create(new InetSocketAddress(InetAddress.getByAddress(new byte[] {127, 0, 0, 1}), PORT), 8);
        server.setExecutor(executor);
        server.createContext("/", this::exchange);
        server.start();
    }

    private void exchange(HttpExchange exchange) throws IOException {
        try (exchange) {
            try {
                String method = exchange.getRequestMethod();
                String path = exchange.getRequestURI().getRawPath();
                boolean post = method.equals("POST");
                FixtureObservation.check(method.equals("GET") || post, "HTTP method");
                FixtureObservation.check(exchange.getRequestURI().getRawQuery() == null, "HTTP query");
                Set<String> headers = exchange.getRequestHeaders().keySet().stream()
                        .map(name -> name.toLowerCase(Locale.ROOT)).collect(Collectors.toSet());
                Set<String> expected = post
                        ? Set.of("host", "authorization", "connection", "accept", "content-type", "content-length")
                        : Set.of("host", "authorization", "connection", "accept");
                FixtureObservation.check(headers.equals(expected), "closed HTTP headers");
                requireHeader(exchange, "Host", "127.0.0.1:" + PORT);
                requireHeader(exchange, "Authorization", "Bearer " + token);
                requireHeader(exchange, "Connection", "close");
                requireHeader(exchange, "Accept", "application/json");
                if (post) requireHeader(exchange, "Content-Type", "application/json");
                byte[] request = exchange.getRequestBody().readNBytes(2049);
                FixtureObservation.check(request.length <= 2048 && (post || request.length == 0), "bounded HTTP body");
                if (post) requireHeader(exchange, "Content-Length", Integer.toString(request.length));
                if (method.equals("GET") && path.equals("/v1/state")) {
                    byte[] response;
                    synchronized (this) { stateReads++; response = stateBytes(); }
                    send(exchange, 200, response);
                } else if (method.equals("GET") && path.startsWith("/v1/operations/")) {
                    String id = path.substring("/v1/operations/".length());
                    FixtureObservation.check(UUID.fromString(id).toString().equals(id), "operation UUID");
                    byte[] response;
                    synchronized (this) { response = operations.get(id); }
                    FixtureObservation.check(response != null, "lookup was not an owned operation");
                    send(exchange, 200, response);
                } else if (post && path.equals("/v1/hold")) {
                    byte[] response;
                    synchronized (this) {
                        Map<String, Object> body = Json.object(request, 2048);
                        String id = validateGesture(body, true);
                        FixtureObservation.check(operations.size() < 16 && !operations.containsKey(id)
                                && pendingRecord == null, "unique finite held ingress");
                        holds++; holdIds.put(holds, id); holdEnvelopes.put(id, Map.copyOf(body));
                        response = ascii(raw(operation(id, "record", true)).replace("recording_pending", "recording"));
                        operations.put(id, response); lastRecord = response;
                        pendingRecord = id; pendingPhase = "recording";
                    }
                    send(exchange, 202, response);
                } else if (post && path.equals("/v1/release")) {
                    byte[] response;
                    synchronized (this) {
                        String id = validateRelease(Json.object(request, 2048));
                        FixtureObservation.check(id.equals(pendingRecord) && releasedHolds.add(id), "one owned held release");
                        releases++;
                        response = operation(id, "record", false);
                        operations.put(id, response); lastRecord = response; pendingRecord = null;
                    }
                    send(exchange, 202, response);
                } else if (post && (path.equals("/v1/record") || path.equals("/v1/stop"))) {
                    boolean record = path.equals("/v1/record");
                    Gate held;
                    byte[] response;
                    synchronized (this) {
                        String id = validateGesture(Json.object(request, 2048), record);
                        FixtureObservation.check(operations.size() < 16 && !operations.containsKey(id), "unique finite ingress");
                        if (record) {
                            records++; recordIds.put(records, id);
                            boolean pending = pendingNext;
                            pendingNext = false;
                            response = operation(id, "record", pending);
                            lastRecord = response;
                            pendingRecord = pending ? id : null; pendingPhase = "recording_pending";
                            held = blockNext ? new Gate() : null;
                            blockNext = false;
                            if (held != null) { held.enteredAt = System.nanoTime(); gate = held; }
                        } else {
                            stops++; stopIds.put(stops, id);
                            if (pendingRecord != null) {
                                if (holdEnvelopes.containsKey(pendingRecord)) heldStops++;
                                byte[] cancelled = ascii(raw(operation(pendingRecord, "record", false))
                                        .replace("\"game_kind\":\"no_action\"", "\"game_kind\":\"cancelled\""));
                                operations.put(pendingRecord, cancelled); lastRecord = cancelled; pendingRecord = null;
                            }
                            response = operation(id, "stop", false);
                            lastStop = response;
                            held = null;
                            Gate current = gate;
                            if (current != null && current.enteredAt > 0 && current.releasedAt == 0)
                                current.stopBeforeRelease = true;
                        }
                        operations.put(id, response);
                    }
                    if (held != null) {
                        try {
                            // The real client deadline remains two seconds. Never hold a request indefinitely.
                            if (!held.release.await(1800, TimeUnit.MILLISECONDS)) failure.compareAndSet(null, "ordinary gate timeout");
                        } catch (InterruptedException exception) {
                            Thread.currentThread().interrupt(); failure.compareAndSet(null, "ordinary gate interrupted");
                        } finally { held.releasedAt = System.nanoTime(); }
                    }
                    send(exchange, 202, response);
                } else {
                    throw new AssertionError("Client control fixture: closed HTTP path");
                }
            } catch (RuntimeException | AssertionError exception) {
                failure.compareAndSet(null, "protocol validation failed");
                send(exchange, 400, ascii("{\"protocol\":1,\"status\":\"refused\"}"));
            }
        }
    }

    private static void requireHeader(HttpExchange exchange, String name, String expected) {
        var values = exchange.getRequestHeaders().get(name);
        FixtureObservation.check(values != null && values.size() == 1 && values.getFirst().equals(expected), "HTTP field");
    }

    private String validateGesture(Map<String, Object> body, boolean record) {
        if (record) Protocol.keys(body, "protocol", "session_id", "request_id", "created_at_ms", "admit_before_ms",
                "context_id", "generation", "expires_at_ms");
        else Protocol.keys(body, "protocol", "session_id", "request_id", "created_at_ms", "admit_before_ms");
        Protocol.integer(body, "protocol", 1, 1);
        FixtureObservation.check(Protocol.uuid(body, "session_id").equals(session), "original session");
        String id = Protocol.uuid(body, "request_id");
        long now = System.currentTimeMillis();
        long created = Protocol.integer(body, "created_at_ms", startedAt, now + 1000);
        long admit = Protocol.integer(body, "admit_before_ms", 1, Long.MAX_VALUE);
        FixtureObservation.check(admit == created + 3000 && now < admit, "original admission time");
        if (record) {
            FixtureObservation.check(Protocol.hex(body, "context_id").equals(context), "original context");
            FixtureObservation.check(Protocol.integer(body, "generation", 0, Integer.MAX_VALUE) == generation, "original generation");
            long expires = Protocol.integer(body, "expires_at_ms", 1, Long.MAX_VALUE);
            FixtureObservation.check(expires == created + INSTRUCTION_TIMEOUT && expires <= sessionExpiry, "original expiry");
        }
        return id;
    }

    private String validateRelease(Map<String, Object> body) {
        Protocol.keys(body, "protocol", "session_id", "request_id", "created_at_ms", "admit_before_ms",
                "context_id", "generation", "expires_at_ms", "released_at_ms", "release_before_ms");
        String id = Protocol.uuid(body, "request_id");
        Map<String, Object> original = holdEnvelopes.get(id);
        FixtureObservation.check(original != null, "release owns original hold");
        original.forEach((key, value) -> FixtureObservation.check(value.equals(body.get(key)), "unchanged release envelope"));
        long now = System.currentTimeMillis();
        long expiry = (Long) original.get("expires_at_ms");
        long released = Protocol.integer(body, "released_at_ms", (Long) original.get("created_at_ms"), now + 1000);
        long before = Protocol.integer(body, "release_before_ms", 1, Long.MAX_VALUE);
        FixtureObservation.check(before == Math.min(released + 3000, expiry) && now < before && now < expiry,
                "original release forwarding deadline");
        return id;
    }

    private byte[] operation(String id, String kind, boolean pending) {
        String stop = kind.equals("stop") ? "\"" + UUID.randomUUID() + "\"" : "null";
        String response = "{\"request_id\":\"" + id + "\",\"operation\":\"" + kind
                + "\",\"status\":\"" + (pending ? "pending" : "known")
                + "\",\"phase\":" + (pending ? "\"recording_pending\"" : "null")
                + ",\"game_kind\":" + (pending ? "null" : "\"no_action\"")
                + ",\"feedback\":" + (pending ? "null" : "{\"language\":\"en\",\"text\":\"synthetic fixture result\"}")
                + ",\"native_evidence_status\":" + (pending ? "null" : "\"not_requested\"")
                + ",\"reply_status\":" + (pending ? "null" : "\"not_attempted\"")
                + ",\"playback\":" + (pending ? "null" : "\"not_attempted\"")
                + ",\"reply_evidence_status\":null,\"reply_failure\":null,\"server_stop_id\":" + stop + "}";
        if (!pending && kind.equals("record")) {
            if (records == 1) response = response.replace("synthetic fixture result", "Fixture: " + "W".repeat(391))
                    .replace("\"game_kind\":\"no_action\"", "\"game_kind\":\"applied\"")
                    .replace("\"native_evidence_status\":\"not_requested\"", "\"native_evidence_status\":\"failed\"")
                    .replace("\"reply_status\":\"not_attempted\"", "\"reply_status\":\"failed\"")
                    .replace("\"reply_evidence_status\":null", "\"reply_evidence_status\":\"failed\"")
                    .replace("\"reply_failure\":null", "\"reply_failure\":\"synthesis_failed\"");
            if (records == 2) response = response.replace("\"reply_status\":\"not_attempted\"", "\"reply_status\":\"cancelled_server_work_unknown\"")
                    .replace("\"playback\":\"not_attempted\"", "\"playback\":\"settlement_unknown\"")
                    .replace("\"reply_evidence_status\":null", "\"reply_evidence_status\":\"failed\"")
                    .replace("\"reply_failure\":null", "\"reply_failure\":\"playback_unsettled\"");
            if (records == 3) response = response.replace("\"reply_status\":\"not_attempted\"", "\"reply_status\":\"generated\"")
                    .replace("\"playback\":\"not_attempted\"", "\"playback\":\"player_exited\"")
                    .replace("\"reply_evidence_status\":null", "\"reply_evidence_status\":\"recorded\"");
        }
        byte[] bytes = ascii(response);
        Protocol.Operation checked = Protocol.operation(bytes);
        FixtureObservation.check(checked.requestId().equals(id) && (pending || checked.settled()), "typed fixture operation");
        FixtureObservation.check(!kind.equals("stop") || !checked.serverStopId().equals(id), "distinct synthetic server stop");
        return bytes;
    }

    private byte[] stateBytes() {
        String voice = pendingRecord == null ? "null"
                : "{\"request_id\":\"" + pendingRecord + "\",\"phase\":\"" + pendingPhase + "\"}";
        byte[] bytes = ascii("{\"protocol\":1,\"session_id\":\"" + session + "\",\"context_id\":\"" + context
                + "\",\"generation\":" + generation + ",\"session_expires_at_ms\":" + sessionExpiry
                + ",\"instruction_timeout_ms\":" + INSTRUCTION_TIMEOUT
                + ",\"can_record\":true,\"stopping\":false,\"audio_blocked\":false,\"voice\":" + voice
                + ",\"last_record\":" + raw(lastRecord) + ",\"last_stop\":" + raw(lastStop) + "}");
        Protocol.state(bytes);
        return bytes;
    }

    private static byte[] ascii(String text) { return text.getBytes(StandardCharsets.US_ASCII); }
    private static String raw(byte[] bytes) { return bytes == null ? "null" : new String(bytes, StandardCharsets.US_ASCII); }
    private static void send(HttpExchange exchange, int status, byte[] bytes) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.getResponseHeaders().set("Connection", "close");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }
    synchronized int records() { return records; }
    synchronized int holds() { return holds; }
    synchronized int releases() { return releases; }
    synchronized int heldStops() { return heldStops; }
    synchronized String holdId(int index) { return holdIds.get(index); }
    synchronized Protocol.Operation holdResult(int index) { return Protocol.operation(operations.get(holdIds.get(index))); }
    synchronized int stops() { return stops; }
    synchronized int stateReads() { return stateReads; }
    boolean healthy() { return failure.get() == null; }
    synchronized String recordId(int index) { return recordIds.get(index); }
    synchronized String stopId(int index) { return stopIds.get(index); }
    synchronized Protocol.Operation recordResult(int index) { return Protocol.operation(operations.get(recordIds.get(index))); }
    synchronized boolean ownsHud(String text) {
        return operations.keySet().stream().anyMatch(id -> text.contains("[" + id.substring(0, 8) + "]"));
    }
    synchronized void changeContext() { context = CONTEXT_TWO; generation = 2; }
    synchronized void blockNextRecord() { blockNext = true; }
    synchronized void pendingNextRecord() { pendingNext = true; }
    Gate gate() { return gate; }
    boolean closeAndAudit() {
        boolean retire;
        synchronized (this) {
            retire = !closed;
            closed = true;
        }
        if (retire) {
            Gate current = gate;
            if (current != null) current.release();
            server.stop(0);
            executor.shutdownNow();
        }
        try {
            return executor.awaitTermination(500, TimeUnit.MILLISECONDS)
                    && Thread.getAllStackTraces().keySet().stream().noneMatch(thread -> thread.isAlive()
                    && thread.getName().startsWith("lychd-fixture-"));
        }
        catch (InterruptedException exception) { Thread.currentThread().interrupt(); return false; }
    }
}
