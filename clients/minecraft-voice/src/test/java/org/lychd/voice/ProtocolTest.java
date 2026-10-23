package org.lychd.voice;

import org.junit.jupiter.api.Test;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class ProtocolTest {
    static final String SESSION = "b21b6664-4979-49e5-851d-0475dca7c799";
    static final String REQUEST = "cb31ca92-4c94-47e3-bedd-c83a0e151600";
    static byte[] bytes(String text) { return text.getBytes(StandardCharsets.UTF_8); }
    static String operation(String id, String kind, String status) {
        return "{\"request_id\":\"" + id + "\",\"operation\":\"" + kind + "\",\"status\":\"" + status
                + "\",\"phase\":null,\"game_kind\":null,\"feedback\":null,\"native_evidence_status\":null,"
                + "\"reply_status\":null,\"playback\":null,\"reply_evidence_status\":null,\"reply_failure\":null,\"server_stop_id\":null}";
    }
    static String state(String context, long generation) {
        return "{\"protocol\":1,\"session_id\":\"" + SESSION + "\",\"context_id\":\"" + context
                + "\",\"generation\":" + generation + ",\"session_expires_at_ms\":200000,\"instruction_timeout_ms\":10000,"
                + "\"can_record\":true,\"stopping\":false,\"audio_blocked\":false,\"voice\":null,\"last_record\":null,\"last_stop\":null}";
    }
    static String profile(String endpoint) {
        return "{\"protocol\":1,\"endpoint\":\"" + endpoint + "\",\"token\":\"" + "a".repeat(64)
                + "\",\"server_address\":\"127.0.0.1:25572\",\"player_id\":\"" + SESSION + "\",\"record_seconds\":3}";
    }
    @Test void strictJsonRejectsDuplicateKeysAndAmbiguousTypes() {
        for (String text : new String[] {"{\"a\":null,\"a\":1}", "{\"a\":1.0}", "{\"a\":01}",
                "{\"a\":[]}", "{\"a\":NaN}", "{\"a\":\"\\ud800\"}", "{\"a\":1}false"}) {
            assertThrows(IllegalArgumentException.class, () -> Json.object(bytes(text), 8192));
        }
        assertEquals("žluťoučký", Json.object(bytes("{\"a\":\"žluťoučký\"}"), 8192).get("a"));
        assertThrows(IllegalArgumentException.class, () -> Json.object(new byte[] {(byte) 0xff}, 8192));
    }
    @Test void profileNeverTurnsContextAddressIntoTransportRoute() {
        Profile accepted = Profile.parse(bytes(profile("http://127.0.0.1:18186")));
        assertEquals(18186, accepted.port);
        assertEquals("127.0.0.1:25572", accepted.serverAddress);
        for (String endpoint : new String[] {"http://localhost:18186", "http://127.1:18186", "http://[::1]:18186",
                "https://127.0.0.1:18186", "http://127.0.0.1:18186/", "http://127.0.0.1:18186?x=1",
                "http://127.0.0.1:0", "http://127.0.0.1:65536", "http://127.0.0.1:018186", "http://127.0.0.1:18186@evil"}) {
            assertThrows(IllegalArgumentException.class, () -> Profile.parse(bytes(profile(endpoint))));
        }
        assertFalse(accepted.toString().contains("a".repeat(64)));
        assertThrows(IllegalArgumentException.class, () -> Profile.parse(bytes(
                profile("http://127.0.0.1:18186").replace("127.0.0.1:25572", "private address"))));
    }
    @Test void exactStateAndClosedOperationsRefuseUnrecognizedFields() {
        String valid = state("b".repeat(64), 7);
        assertEquals(7, Protocol.state(bytes(valid)).generation());
        assertThrows(IllegalArgumentException.class, () -> Protocol.state(bytes(valid.replace("\"voice\":null", "\"voice\":null,\"transcript\":\"private\""))));
        String operation = operation(REQUEST, "record", "pending");
        assertEquals("pending", Protocol.operation(bytes(operation)).status());
        assertThrows(IllegalArgumentException.class, () -> Protocol.operation(bytes(operation.replace("\"phase\":null", "\"phase\":\"microphone_active\""))));
        assertThrows(IllegalArgumentException.class, () -> Protocol.operation(bytes(operation.replace("\"feedback\":null", "\"feedback\":{\"language\":\"en\",\"text\":\"\\u00a7cunsafe\"}"))));
    }
    @Test void gesturePreservesOriginalIdentityContextAndDeadline() {
        Protocol.State view = Protocol.state(bytes(state("b".repeat(64), 7)));
        Protocol.Gesture record = Protocol.gesture("record", view, 1234, 9, REQUEST);
        Map<String, Object> body = Json.object(record.bytes(), 2048);
        assertEquals(1234L, body.get("created_at_ms"));
        assertEquals(4234L, body.get("admit_before_ms"));
        assertEquals(11234L, body.get("expires_at_ms"));
        assertEquals(REQUEST, body.get("request_id"));
        assertEquals(7L, body.get("generation"));
        assertEquals("b".repeat(64), body.get("context_id"));
        Map<String, Object> stop = Json.object(Protocol.gesture("stop", view, 1300, 9, SESSION).bytes(), 2048);
        assertEquals(java.util.Set.of("protocol", "session_id", "request_id", "created_at_ms", "admit_before_ms"), stop.keySet());
        assertFalse(stop.containsKey("server_stop_id"));
    }
    @Test void hudSeparatesKnownGameFromReplyFailureAndNeverClaimsHearing() {
        String wire = operation(REQUEST, "record", "known").replace("\"game_kind\":null", "\"game_kind\":\"applied\"")
                .replace("\"reply_status\":null", "\"reply_status\":\"failed\"")
                .replace("\"reply_failure\":null", "\"reply_failure\":\"synthesis_failed\"");
        VoiceController.Hud hud = new VoiceController.Hud(REQUEST, "record", "known", null, Protocol.operation(bytes(wire)));
        String en = HudText.render(hud, "en_us");
        assertTrue(en.contains("game: applied")); assertTrue(en.contains("reply: failed"));
        assertTrue(en.contains("synthesis failed")); assertTrue(en.contains(REQUEST.substring(0, 8)));
        assertTrue(HudText.render(hud, "sk_sk").contains("hra: vykonané"));
        assertTrue(HudText.render(hud, "cs_cz").contains("hra: provedeno"));
        assertFalse(en.contains("heard")); assertFalse(en.contains("microphone active"));
    }
    @Test void releaseRetainsEveryOriginalFieldAndFreezesItsOwnForwardingDeadline() {
        Protocol.State view = Protocol.state(bytes(state("b".repeat(64), 7)));
        Protocol.Gesture original = Protocol.gesture("record", view, 1234, 9, REQUEST);
        Protocol.Release release = Protocol.release(original, 5234);
        Map<String, Object> start = Json.object(original.bytes(), 2048);
        Map<String, Object> finish = Json.object(release.bytes(), 2048);
        start.forEach((key, value) -> assertEquals(value, finish.get(key), key));
        assertEquals(start.size() + 2, finish.size());
        assertEquals(5234L, finish.get("released_at_ms"));
        assertEquals(8234L, finish.get("release_before_ms"));
        assertArrayEquals(release.bytes(), release.bytes());
        assertEquals(11234, Protocol.release(original, 11000).releaseBefore());
        assertThrows(IllegalArgumentException.class, () -> Protocol.release(original, 11234));
        assertThrows(IllegalArgumentException.class, () -> Protocol.release(original, 1000));
        for (String phase : new String[] {"recording", "finishing"}) {
            assertEquals(phase, Protocol.operation(bytes(operation(REQUEST, "record", "pending")
                    .replace("\"phase\":null", "\"phase\":\"" + phase + "\""))).phase());
        }
        for (String locale : new String[] {"en_us", "sk_sk", "cs_cz"}) {
            assertFalse(HudText.render(new VoiceController.Hud(REQUEST, "record", "hold_requested", "recording", null), locale)
                    .contains("unknown"));
            assertFalse(HudText.render(new VoiceController.Hud(REQUEST, "record", "release_requested", "finishing", null), locale)
                    .contains("unknown"));
        }
    }
}
