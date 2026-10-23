package org.lychd.companion.protocol;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.ProtocolTest.*;

class BridgeHttpServerTest {
    private static final String TOKEN = "a".repeat(64);
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2))
            .followRedirects(HttpClient.Redirect.NEVER).build();
    private HttpResponse<String> send(BridgeHttpServer server, String path, String method, String body, boolean authorized) throws Exception {
        var builder = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + server.port() + path)).timeout(Duration.ofSeconds(3));
        if (authorized) builder.header("Authorization", "Bearer " + TOKEN);
        if (method.equals("POST")) builder.header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(body));
        else builder.GET();
        return client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
    }
    @Test void realHttpAuthenticatesStrictlyBoundsBodiesAndUsesOnlyCachedState() throws Exception {
        var inbox = ActionInboxTest.inbox(3);
        try (var server = new BridgeHttpServer(0, TOKEN, inbox)) {
            server.start();
            assertEquals(401, send(server, "/v1/state", "GET", "", false).statusCode());
            var state = send(server, "/v1/state", "GET", "", true);
            assertEquals(200, state.statusCode());
            assertFalse(state.body().contains(TOKEN));
            assertEquals(0, StrictJson.object(state.body()).get("timestamp_ms").getAsLong());
            assertEquals(413, send(server, "/v1/actions", "POST", " ".repeat(8193), true).statusCode());
            assertEquals(400, send(server, "/v1/actions", "POST", "{\"protocol\":1,\"protocol\":1}", true).statusCode());
            assertEquals(404, send(server, "/v1/actions/" + UUID.randomUUID(), "GET", "", true).statusCode());
            assertEquals(400, send(server, "/v1/actions/not-a-uuid", "GET", "", true).statusCode());
            assertEquals(404, send(server, "/v1/console", "POST", "{}", true).statusCode());
        }
    }
    @Test void httpAcknowledgesApplicationOnlyAfterTickAndPriorityStopSurvivesFullRetention() throws Exception {
        var inbox = ActionInboxTest.inbox(1); var actuator = new ActionInboxTest.FakeActuator();
        try (var server = new BridgeHttpServer(0, TOKEN, inbox)) {
            server.start();
            UUID id = UUID.randomUUID();
            String body = action(id, 0, System.currentTimeMillis() + 30_000, "idle", "{}");
            var accepted = send(server, "/v1/actions", "POST", body, true);
            assertEquals(202, accepted.statusCode());
            assertEquals("accepted", StrictJson.object(accepted.body()).get("status").getAsString());
            assertEquals(202, send(server, "/v1/actions", "POST", body, true).statusCode());
            String changed = body.replace("\"idle\"", "\"state\"");
            assertEquals(409, send(server, "/v1/actions", "POST", changed, true).statusCode());
            assertEquals(503, send(server, "/v1/actions", "POST", action(UUID.randomUUID(), 0,
                    System.currentTimeMillis() + 30_000, "state", "{}"), true).statusCode());
            UUID stopId = UUID.randomUUID();
            assertEquals(202, send(server, "/v1/stop", "POST", stop(stopId), true).statusCode());
            inbox.tick(System.currentTimeMillis(), actuator);
            var stopped = send(server, "/v1/actions/" + stopId, "GET", "", true);
            assertEquals("applied", StrictJson.object(stopped.body()).get("status").getAsString());
            assertEquals("cancelled", inbox.find(id).status());
            assertEquals(java.util.List.of("stop"), actuator.effects);
        }
    }
}
