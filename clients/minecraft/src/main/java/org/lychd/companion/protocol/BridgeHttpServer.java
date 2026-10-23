package org.lychd.companion.protocol;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import static org.lychd.companion.protocol.Protocol.*;

/** Literal IPv4 loopback only; handlers read cached state and never touch the live game. */
public final class BridgeHttpServer implements AutoCloseable {
    private final HttpServer server;
    private final ThreadPoolExecutor workers;
    private final byte[] authorization;
    private final ActionInbox inbox;

    public BridgeHttpServer(int port, String token, ActionInbox inbox) throws IOException {
        if (!token.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("invalid private bridge token");
        // JDK HttpServer exposes these limits process-wide, not per server. Set finite defaults
        // before its first initialization in this opt-in dedicated-server profile.
        System.setProperty("sun.net.httpserver.maxReqTime", "5");
        System.setProperty("sun.net.httpserver.maxRspTime", "5");
        System.setProperty("jdk.httpserver.maxConnections", "32");
        System.setProperty("sun.net.httpserver.maxIdleConnections", "4");
        System.setProperty("sun.net.httpserver.maxReqHeaders", "32");
        System.setProperty("sun.net.httpserver.maxReqHeaderSize", "8192");
        this.inbox = inbox;
        this.authorization = ("Bearer " + token).getBytes(StandardCharsets.US_ASCII);
        this.server = HttpServer.create(new InetSocketAddress(InetAddress.getByAddress(new byte[]{127, 0, 0, 1}), port), 16);
        this.workers = new ThreadPoolExecutor(2, 2, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(16), r -> {
            Thread thread = new Thread(r, "lychd-bridge-http"); thread.setDaemon(true); return thread;
        }, new ThreadPoolExecutor.AbortPolicy());
        server.setExecutor(workers);
        server.createContext("/", this::handle);
    }
    public void start() { server.start(); }
    public int port() { return server.getAddress().getPort(); }
    private void handle(HttpExchange exchange) throws IOException {
        try {
            List<String> auth = exchange.getRequestHeaders().get("Authorization");
            if (auth == null || auth.size() != 1 || !MessageDigest.isEqual(authorization, auth.getFirst().getBytes(StandardCharsets.UTF_8)))
                throw new Rejection(401, "unauthorized");
            if (exchange.getRequestURI().getRawQuery() != null) throw new Rejection(400, "query not supported");
            String path = exchange.getRequestURI().getRawPath();
            String method = exchange.getRequestMethod();
            if (method.equals("GET") && path.equals("/v1/state")) send(exchange, 200, inbox.state());
            else if (method.equals("GET") && path.startsWith("/v1/actions/")) {
                var id = StrictJson.uuid(path.substring("/v1/actions/".length()));
                var record = inbox.find(id);
                if (record == null) throw new Rejection(404, "unknown action identity");
                send(exchange, 200, record);
            } else if (method.equals("POST") && (path.equals("/v1/actions") || path.equals("/v1/stop"))) {
                String body = body(exchange);
                ActionRecord record = path.equals("/v1/stop")
                        ? inbox.stop(StrictJson.stop(body), body)
                        : inbox.submit(StrictJson.action(body), body, System.currentTimeMillis());
                send(exchange, 202, record);
            } else throw new Rejection(404, "unknown endpoint");
        } catch (Rejection e) { send(exchange, e.status(), Map.of("detail", e.getMessage())); }
        catch (RuntimeException e) { send(exchange, 500, Map.of("detail", "bridge handler failure")); }
        finally { exchange.close(); }
    }
    private String body(HttpExchange exchange) throws IOException {
        if (exchange.getRequestHeaders().containsKey("Content-Encoding")) throw new Rejection(400, "content encoding not supported");
        var types = exchange.getRequestHeaders().get("Content-Type");
        if (types == null || types.size() != 1 || !types.getFirst().matches("(?i)application/json(?:;\\s*charset=utf-8)?"))
            throw new Rejection(400, "expected application/json UTF-8");
        var lengths = exchange.getRequestHeaders().get("Content-Length");
        if (lengths != null) {
            try {
                if (lengths.size() != 1 || Long.parseLong(lengths.getFirst()) > MAX_REQUEST_BYTES) throw new Rejection(413, "request too large");
            } catch (NumberFormatException e) { throw new Rejection(400, "invalid content length"); }
        }
        byte[] bytes = exchange.getRequestBody().readNBytes(MAX_REQUEST_BYTES + 1);
        if (bytes.length > MAX_REQUEST_BYTES) throw new Rejection(413, "request too large");
        return StrictJson.utf8(bytes);
    }
    private void send(HttpExchange exchange, int status, Object value) throws IOException {
        byte[] bytes = StrictJson.GSON.toJson(value).getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_RESPONSE_BYTES) {
            status = 503;
            bytes = "{\"detail\":\"response bound exceeded\"}".getBytes(StandardCharsets.UTF_8);
        }
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
    }
    @Override public void close() { server.stop(0); workers.shutdownNow(); }
}
