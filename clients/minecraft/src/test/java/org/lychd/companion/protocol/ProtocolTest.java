package org.lychd.companion.protocol;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.protocol.Protocol.*;

class ProtocolTest {
    static final UUID BOOT = UUID.fromString("00000000-0000-4000-8000-000000000001");
    static final UUID ACTOR = UUID.fromString("00000000-0000-4000-8000-000000000002");
    static final UUID RUN = UUID.fromString("00000000-0000-4000-8000-000000000003");
    static String action(UUID id, long generation, long expiry, String kind, String args) {
        return "{\"protocol\":1,\"boot_id\":\"" + BOOT + "\",\"generation\":" + generation
                + ",\"actor_id\":\"" + ACTOR + "\",\"run_id\":\"" + RUN + "\",\"action_id\":\"" + id
                + "\",\"expires_at_ms\":" + expiry + ",\"kind\":\"" + kind + "\",\"args\":" + args + "}";
    }
    static String stop(UUID id) {
        return "{\"protocol\":1,\"boot_id\":\"" + BOOT + "\",\"actor_id\":\"" + ACTOR
                + "\",\"run_id\":\"" + RUN + "\",\"action_id\":\"" + id + "\"}";
    }
    @Test void acceptsOnlyTypedActions() {
        var action = StrictJson.action(action(UUID.randomUUID(), 0, 50_000, "goto", "{\"x\":1.5,\"y\":64,\"z\":2}"));
        assertEquals(new Point(1.5, 64, 2), action.point());
        assertThrows(Rejection.class, () -> StrictJson.action(action(UUID.randomUUID(), 0, 500, "console", "{}")));
        assertThrows(Rejection.class, () -> StrictJson.action(action(UUID.randomUUID(), 0, 500, "say", "{\"text\":\" /op player\"}")));
        assertThrows(Rejection.class, () -> StrictJson.action(action(UUID.randomUUID(), 0, 500, "say", "{\"text\":\"line\\nline\"}")));
    }
    @Test void rejectsDuplicateUnknownNonfiniteAndMalformedValues() {
        String good = action(UUID.randomUUID(), 0, 500, "state", "{}");
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace("\"protocol\":1", "\"protocol\":1,\"protocol\":1")));
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace("\"args\":{}", "\"args\":{\"extra\":true}")));
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace("\"protocol\":1", "\"protocol\":true")));
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace("\"protocol\":1", "\"protocol\":1.0")));
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace(BOOT.toString(), "0-0-4-8-1")));
        assertThrows(Rejection.class, () -> StrictJson.action(action(UUID.randomUUID(), 0, 500, "look", "{\"x\":1e999,\"y\":0,\"z\":0}")));
        assertThrows(Rejection.class, () -> StrictJson.object("{\"nested\":{\"a\":1,\"a\":2}}"));
        assertThrows(Rejection.class, () -> StrictJson.object("{\"x\":NaN}"));
        assertThrows(Rejection.class, () -> StrictJson.object("{\"x\":1} trailing"));
        assertThrows(Rejection.class, () -> StrictJson.utf8(new byte[] {(byte)0xc0, (byte)0xaf}));
    }
    @Test void generationAndDeadlineRemainExactIntegers() {
        String good = action(UUID.randomUUID(), Long.MAX_VALUE, 1_792_630_000_000L, "state", "{}");
        assertEquals(Long.MAX_VALUE, StrictJson.action(good).generation());
        assertEquals(1_792_630_000_000L, StrictJson.action(good).expiresAtMs());
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace(Long.toString(Long.MAX_VALUE), "9223372036854775808")));
        assertThrows(Rejection.class, () -> StrictJson.action(good.replace("\"generation\":" + Long.MAX_VALUE, "\"generation\":0.5")));
    }
}
