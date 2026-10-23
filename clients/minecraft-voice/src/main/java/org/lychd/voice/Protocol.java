package org.lychd.voice;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Exact local v1 wire vocabulary. This client accepts no diagnostic or transcript fields. */
final class Protocol {
    private Protocol() { }
    record State(String sessionId, String contextId, long generation, long sessionExpiresAt,
                 long instructionTimeout, boolean canRecord, boolean stopping, boolean audioBlocked,
                 String voiceRequestId, String voicePhase, Operation lastRecord, Operation lastStop) { }
    record Operation(String requestId, String operation, String status, String phase, String gameKind,
                     String feedbackLanguage, String feedback, String nativeEvidence, String replyStatus,
                     String playback, String replyEvidence, String replyFailure, String serverStopId) {
        boolean terminal() { return !status.equals("pending"); }
        boolean settled() {
            if (status.equals("refused") || status.equals("unknown")) return true;
            return status.equals("known") && !"pending".equals(nativeEvidence) && replyStatus != null && playback != null
                    && (!replyStatus.equals("generated") || replyEvidence != null || replyFailure != null);
        }
    }
    record Gesture(String operation, String requestId, String sessionId, String contextId,
                   long generation, long createdAt, long admitBefore, long expiresAt, long epoch) {
        byte[] bytes() {
            String base = "{\"protocol\":1,\"session_id\":\"" + sessionId
                    + "\",\"request_id\":\"" + requestId + "\",\"created_at_ms\":" + createdAt
                    + ",\"admit_before_ms\":" + admitBefore;
            if (operation.equals("record")) base += ",\"context_id\":\"" + contextId
                    + "\",\"generation\":" + generation + ",\"expires_at_ms\":" + expiresAt;
            return (base + "}").getBytes(StandardCharsets.US_ASCII);
        }
    }
    record Release(Gesture original, long releasedAt, long releaseBefore) {
        byte[] bytes() {
            String base = new String(original.bytes(), StandardCharsets.US_ASCII);
            return (base.substring(0, base.length() - 1) + ",\"released_at_ms\":" + releasedAt
                    + ",\"release_before_ms\":" + releaseBefore + "}").getBytes(StandardCharsets.US_ASCII);
        }
    }
    static Release release(Gesture original, long now) {
        if (!original.operation().equals("record") || now < original.createdAt() || now >= original.expiresAt())
            throw Json.invalid();
        return new Release(original, now, Math.min(Math.addExact(now, 3000), original.expiresAt()));
    }
    static Gesture gesture(String operation, State state, long now, long epoch, String id) {
        return new Gesture(operation, id, state.sessionId, state.contextId, state.generation,
                now, Math.addExact(now, 3000), Math.addExact(now, state.instructionTimeout), epoch);
    }
    static State state(byte[] body) {
        Map<String, Object> data = Json.object(body, 8192);
        keys(data, "protocol", "session_id", "context_id", "generation", "session_expires_at_ms",
                "instruction_timeout_ms", "can_record", "stopping", "audio_blocked", "voice", "last_record", "last_stop");
        integer(data, "protocol", 1, 1);
        String voiceId = null, phase = null;
        if (data.get("voice") != null) {
            Map<String, Object> voice = map(data.get("voice")); keys(voice, "request_id", "phase");
            voiceId = uuid(voice, "request_id");
            phase = choice(voice, "phase", false, "waiting_audio", "recording_pending", "recording", "finishing", "reading_audio", "transcribing");
        }
        return new State(uuid(data, "session_id"), hex(data, "context_id"), integer(data, "generation", 0, Integer.MAX_VALUE),
                integer(data, "session_expires_at_ms", 1, Long.MAX_VALUE), integer(data, "instruction_timeout_ms", 1000, 60000),
                bool(data, "can_record"), bool(data, "stopping"), bool(data, "audio_blocked"), voiceId, phase,
                nullableOperation(data.get("last_record")), nullableOperation(data.get("last_stop")));
    }
    static Operation operation(byte[] body) { return operation(map(Json.object(body, 8192))); }
    private static Operation nullableOperation(Object value) { return value == null ? null : operation(map(value)); }
    private static Operation operation(Map<String, Object> data) {
        keys(data, "request_id", "operation", "status", "phase", "game_kind", "feedback", "native_evidence_status",
                "reply_status", "playback", "reply_evidence_status", "reply_failure", "server_stop_id");
        String language = null, feedback = null;
        if (data.get("feedback") != null) {
            Map<String, Object> item = map(data.get("feedback")); keys(item, "language", "text");
            language = choice(item, "language", false, "sk", "cs", "en"); feedback = string(item, "text");
            if (feedback.length() > 400 || feedback.codePoints().anyMatch(ch -> Character.isISOControl(ch)
                    || Character.getType(ch) == Character.FORMAT || ch == 0xA7)) throw Json.invalid();
        }
        String stopId = data.get("server_stop_id") == null ? null : uuid(data, "server_stop_id");
        return new Operation(uuid(data, "request_id"), choice(data, "operation", false, "record", "stop"),
                choice(data, "status", false, "pending", "known", "refused", "unknown"),
                choice(data, "phase", true, "waiting_audio", "recording_pending", "recording", "finishing", "reading_audio", "transcribing", "queued"),
                choice(data, "game_kind", true, "applied", "refused", "cancelled", "expired", "unknown", "no_action", "clarification"),
                language, feedback, choice(data, "native_evidence_status", true, "pending", "recorded", "failed", "not_requested"),
                choice(data, "reply_status", true, "not_attempted", "generated", "failed", "cancelled_server_work_unknown"),
                choice(data, "playback", true, "not_attempted", "player_exited", "interrupted", "failed", "settlement_unknown"),
                choice(data, "reply_evidence_status", true, "recorded", "failed"),
                choice(data, "reply_failure", true, "synthesis_failed", "artifact_write_failed", "playback_failed", "playback_unsettled"), stopId);
    }
    static boolean fixedStatus(byte[] body, String status) {
        Map<String, Object> data = Json.object(body, 8192); keys(data, "protocol", "status");
        return integer(data, "protocol", 1, 1) == 1 && string(data, "status").equals(status);
    }
    static void keys(Map<String, Object> data, String... names) {
        if (!data.keySet().equals(Set.of(names))) throw Json.invalid();
    }
    @SuppressWarnings("unchecked")
    static Map<String, Object> map(Object value) {
        if (!(value instanceof Map<?, ?>)) throw Json.invalid();
        return (Map<String, Object>) value;
    }
    static long integer(Map<String, Object> data, String key, long min, long max) {
        if (!(data.get(key) instanceof Long number) || number < min || number > max) throw Json.invalid();
        return number;
    }
    static String string(Map<String, Object> data, String key) {
        if (!(data.get(key) instanceof String value)) throw Json.invalid(); return value;
    }
    static String hex(Map<String, Object> data, String key) {
        String value = string(data, key); if (!value.matches("[0-9a-f]{64}")) throw Json.invalid(); return value;
    }
    static String uuid(Map<String, Object> data, String key) {
        String value = string(data, key);
        try { if (!UUID.fromString(value).toString().equals(value)) throw Json.invalid(); }
        catch (IllegalArgumentException exception) { throw Json.invalid(); }
        return value;
    }
    private static boolean bool(Map<String, Object> data, String key) {
        if (!(data.get(key) instanceof Boolean value)) throw Json.invalid(); return value;
    }
    private static String choice(Map<String, Object> data, String key, boolean nullable, String... options) {
        if (nullable && data.get(key) == null) return null;
        String value = string(data, key); if (!Set.of(options).contains(value)) throw Json.invalid(); return value;
    }
}
