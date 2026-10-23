package org.lychd.voice;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/** One request per direct IPv4 socket; no DNS, proxy, HTTP retries, redirects or pooled connections. */
final class LoopbackTransport implements ControlTransport {
    private final Profile profile;
    private final java.util.Set<SocketChannel> active = ConcurrentHashMap.newKeySet();
    private volatile boolean closed;
    LoopbackTransport(Profile profile) { this.profile = profile; }

    @Override public Response request(String method, String path, byte[] body) throws IOException {
        if (closed || body.length > 2048 || !(method.equals("GET") || method.equals("POST"))
                || !(path.equals("/v1/state") || path.equals("/v1/record") || path.equals("/v1/hold") || path.equals("/v1/release") || path.equals("/v1/stop")
                || path.matches("/v1/operations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"))) {
            throw failure();
        }
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        try (SocketChannel channel = SocketChannel.open(); Selector selector = Selector.open()) {
            active.add(channel);
            try {
                if (closed) throw failure();
                channel.configureBlocking(false);
                SelectionKey key = channel.register(selector, SelectionKey.OP_CONNECT);
                channel.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[] {127, 0, 0, 1}), profile.port));
                while (!channel.finishConnect()) await(selector, key, SelectionKey.OP_CONNECT, deadline);
                String headers = method + " " + path + " HTTP/1.1\r\nHost: 127.0.0.1:" + profile.port
                        + "\r\nAuthorization: Bearer " + profile.token
                        + "\r\nConnection: close\r\nAccept: application/json\r\n"
                        + (method.equals("POST") ? "Content-Type: application/json\r\nContent-Length: " + body.length + "\r\n" : "")
                        + "\r\n";
                byte[] head = headers.getBytes(StandardCharsets.US_ASCII);
                ByteBuffer request = ByteBuffer.allocate(head.length + body.length).put(head).put(body);
                request.flip();
                while (request.hasRemaining()) {
                    if (System.nanoTime() >= deadline) throw failure();
                    if (channel.write(request) == 0) await(selector, key, SelectionKey.OP_WRITE, deadline);
                }
                ByteArrayOutputStream response = new ByteArrayOutputStream();
                ByteBuffer buffer = ByteBuffer.allocate(1024);
                while (true) {
                    if (System.nanoTime() >= deadline) throw failure();
                    int read = channel.read(buffer);
                    if (read == -1) break;
                    if (read == 0) { await(selector, key, SelectionKey.OP_READ, deadline); continue; }
                    buffer.flip(); byte[] next = new byte[buffer.remaining()]; buffer.get(next); buffer.clear();
                    response.write(next);
                    if (response.size() > 8192) throw failure();
                }
                return parseResponse(response.toByteArray());
            } finally { active.remove(channel); }
        } catch (IllegalArgumentException exception) { throw failure(); }
    }

    private static void await(Selector selector, SelectionKey key, int operation, long deadline) throws IOException {
        long left = deadline - System.nanoTime();
        if (left <= 0 || Thread.currentThread().isInterrupted()) throw failure();
        key.interestOps(operation);
        selector.select(Math.max(1, TimeUnit.NANOSECONDS.toMillis(left)));
        selector.selectedKeys().clear();
    }

    static Response parseResponse(byte[] bytes) throws IOException {
        if (bytes.length > 8192) throw failure();
        int boundary = -1;
        for (int i = 0; i + 3 < bytes.length; i++) {
            if (bytes[i] == 13 && bytes[i + 1] == 10 && bytes[i + 2] == 13 && bytes[i + 3] == 10) {
                boundary = i; break;
            }
        }
        if (boundary < 0 || boundary + 4 > 4096) throw failure();
        for (int i = 0; i < boundary; i++) if (bytes[i] < 0 || bytes[i] == 127 || (bytes[i] < 32 && bytes[i] != 13 && bytes[i] != 10)) throw failure();
        String[] lines = new String(bytes, 0, boundary, StandardCharsets.US_ASCII).split("\r\n", -1);
        if (!lines[0].matches("HTTP/1\\.1 [1-5][0-9]{2} [A-Za-z ]{1,64}")) throw failure();
        int status = Integer.parseInt(lines[0].substring(9, 12));
        Map<String, String> headers = new HashMap<>();
        for (int i = 1; i < lines.length; i++) {
            int colon = lines[i].indexOf(':');
            if (colon <= 0 || !lines[i].substring(0, colon).matches("[A-Za-z0-9-]+")) throw failure();
            String name = lines[i].substring(0, colon).toLowerCase(Locale.ROOT);
            String value = lines[i].substring(colon + 1).strip();
            if (headers.putIfAbsent(name, value) != null || value.indexOf('\r') >= 0 || value.indexOf('\n') >= 0) throw failure();
        }
        if (headers.containsKey("transfer-encoding") || headers.containsKey("content-encoding")
                || !"close".equalsIgnoreCase(headers.get("connection"))
                || !"application/json".equalsIgnoreCase(headers.get("content-type"))) throw failure();
        String length = headers.get("content-length");
        if (length == null || !length.matches("0|[1-9][0-9]{0,4}")) throw failure();
        int size = Integer.parseInt(length);
        if (size != bytes.length - boundary - 4) throw failure();
        return new Response(status, java.util.Arrays.copyOfRange(bytes, boundary + 4, bytes.length));
    }

    private static IOException failure() { return new IOException("Local voice control unavailable"); }
    @Override public void close() {
        closed = true;
        for (SocketChannel channel : active) try { channel.close(); } catch (IOException ignored) { }
    }
}
