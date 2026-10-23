package org.lychd.voice;

import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class HudTextTest {
    private static final String ID = "cb31ca92-4c94-47e3-bedd-c83a0e151600";
    private static VoiceController.Hud result(String stage, String game, String nativeEvidence, String reply,
                                             String playback, String replyEvidence, String failure, String feedback) {
        return new VoiceController.Hud(ID, "record", stage, null, new Protocol.Operation(ID, "record", "known", null,
                game, "en", feedback, nativeEvidence, reply, playback, replyEvidence, failure, null));
    }
    @Test void mixedFailureIsNeverCompressedIntoGameSuccess() {
        var hud = result("known", "applied", "failed", "failed", "not_attempted", "failed", "synthesis_failed", "literal.key");
        var lines = HudText.panel(hud, "en_us", List::of, 20);
        assertEquals(List.of("LychD Voice [cb31ca92]", "result known", "game: applied", "reply: failed",
                "playback: not attempted", "game evidence: failed", "reply evidence: failed", "synthesis failed", "literal.key"), lines);
        assertEquals(lines, HudText.panel(hud, "en_us", List::of, lines.size()));
        assertTrue(HudText.panel(hud, "en_us", List::of, lines.size() - 1).getLast().contains("full result needs more space"));
    }
    @Test void missingChannelsAreUnreportedAndDoNotEraseLocalUncertainty() {
        var lines = HudText.paragraphs(result("unknown", "applied", null, null, null, null, null, null), "en_us");
        assertTrue(lines.contains("result unknown"));
        assertTrue(lines.contains("game: applied"));
        for (String channel : List.of("reply", "playback", "game evidence", "reply evidence"))
            assertTrue(lines.contains(channel + ": not reported"));
    }
    @Test void cancellationAndPlayerExitKeepTheirQualificationsInEveryLocale() {
        var hud = result("known", "unknown", "pending", "cancelled_server_work_unknown", "player_exited", "failed", null, null);
        for (var expected : List.of(
                List.of("en_us", "reply: cancelled; server work unknown", "playback: player exited; hearing unconfirmed"),
                List.of("sk_sk", "odpoveď: zrušené; stav servera neznámy", "prehratie: prehrávač skončil; počutie nepotvrdené"),
                List.of("cs_cz", "odpověď: zrušeno; stav serveru neznámý", "přehrání: přehrávač skončil; slyšení nepotvrzeno"))) {
            var lines = HudText.paragraphs(hud, expected.getFirst());
            assertTrue(lines.contains(expected.get(1))); assertTrue(lines.contains(expected.get(2)));
        }
        assertEquals(HudText.paragraphs(hud, "en_us"), HudText.paragraphs(hud, "de_de"));
    }
    @Test void requestedCaptureAndPendingPhasesNeverClaimDeviceActivityOrApplication() {
        var hud = new VoiceController.Hud(ID, "record", "pending", "recording_pending", null);
        assertEquals(List.of("LychD Voice [cb31ca92]", "result pending · capture requested"), HudText.paragraphs(hud, "en_us"));
        assertFalse(HudText.render(hud, "en_us").contains("active"));
        assertFalse(HudText.render(hud, "en_us").contains("applied"));
    }
    @Test void verticalExhaustionNeverShowsOnlyTheSuccessfulSubset() {
        var hud = result("known", "applied", "failed", "generated", "settlement_unknown", "failed", "playback_unsettled", "long feedback");
        var notice = HudText.panel(hud, "en_us", List::of, 2);
        assertEquals("LychD Voice [cb31ca92]", notice.getFirst());
        assertTrue(notice.get(1).contains("full result needs more space"));
        assertTrue(notice.get(1).contains("LychD console"));
        assertFalse(String.join(" ", notice).contains("applied"));
        assertFalse(String.join(" ", notice).contains("result unknown"));
        assertTrue(HudText.panel(hud, "en_us", List::of, 1).isEmpty());
    }
    @Test void wrapperReceivesCompleteLiteralUnicodeAndItsRowsRemainIntact() {
        String literal = "translation.key Žluťoučký 🧱 " + "W".repeat(360);
        var hud = result("known", "clarification", "not_requested", "not_attempted", "not_attempted", null, null, literal);
        var lines = HudText.panel(hud, "sk_sk", text -> List.of(text + "!", "continued"), 30);
        assertTrue(lines.contains(literal + "!"));
        assertEquals(16, lines.size());
        assertEquals("LychD Hlas [cb31ca92]!", lines.getFirst());
        assertThrows(UnsupportedOperationException.class, () -> lines.add("mutable"));
    }
    @Test void terminalVoiceFailuresPreserveLiteralFeedbackWithoutInventingGameOutcome() {
        for (var expected : List.of(
                List.of("sk", "sk_sk", "odmietnuté", "výsledok neznámy", "hra: nehlásené",
                        "Prepis sa nepodaril. Skontroluj vybranú hlasovú službu alebo použi presný textový príkaz.",
                        "Prijatie pokynu nie je potvrdené. Neopakujem ho; over aktuálny stav príkazom stav."),
                List.of("cs", "cs_cz", "odmítnuto", "výsledek neznámý", "hra: nehlášeno",
                        "Přepis se nepodařil. Zkontroluj vybranou hlasovou službu nebo použij přesný textový příkaz.",
                        "Přijetí pokynu není potvrzeno. Neopakuji ho; ověř aktuální stav příkazem stav."),
                List.of("en", "en_us", "refused", "result unknown", "game: not reported",
                        "Transcription did not complete. Check the selected speech service or use an exact text command.",
                        "Instruction admission is unconfirmed. I will not repeat it; check current state with state."))) {
            for (String status : List.of("refused", "unknown")) {
                String feedback = expected.get(status.equals("refused") ? 5 : 6);
                String wire = voiceFailure(status, expected.getFirst(), feedback);
                var operation = Protocol.operation(wire.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                assertEquals(ID, operation.requestId());
                assertEquals("record", operation.operation());
                assertEquals(status, operation.status());
                assertTrue(operation.terminal());
                assertTrue(operation.settled());
                assertNull(operation.gameKind());
                assertEquals(expected.getFirst(), operation.feedbackLanguage());
                assertEquals(feedback, operation.feedback());
                var hud = new VoiceController.Hud(ID, "record", operation.status(), operation.phase(), operation);
                var lines = HudText.paragraphs(hud, expected.get(1));
                assertEquals(expected.get(status.equals("refused") ? 2 : 3), lines.get(1));
                assertEquals(expected.get(4), lines.get(2));
                assertEquals(feedback, lines.getLast());
                assertEquals(lines, HudText.panel(hud, expected.get(1), List::of, lines.size()));
                assertTrue(HudText.render(hud, expected.get(1)).endsWith(feedback));
            }
        }
    }
    @Test void terminalVoiceFailureFeedbackKeepsTheExistingLiteralLengthBound() {
        for (String status : List.of("refused", "unknown")) {
            String literal = "translation.key Žluťoučký 🧱 ";
            literal += "W".repeat(400 - literal.length());
            String wire = voiceFailure(status, "cs", literal);
            var operation = Protocol.operation(wire.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            assertEquals(literal, operation.feedback());
            var hud = new VoiceController.Hud(ID, "record", operation.status(), null, operation);
            assertEquals(literal, HudText.paragraphs(hud, "cs_cz").getLast());
            String oversized = voiceFailure(status, "cs", literal + "W");
            assertThrows(IllegalArgumentException.class,
                    () -> Protocol.operation(oversized.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        }
    }
    private static String voiceFailure(String status, String language, String feedback) {
        return "{\"request_id\":\"" + ID + "\",\"operation\":\"record\",\"status\":\"" + status
                + "\",\"phase\":null,\"game_kind\":null,\"feedback\":{\"language\":\"" + language
                + "\",\"text\":\"" + feedback + "\"},\"native_evidence_status\":null,"
                + "\"reply_status\":null,\"playback\":null,\"reply_evidence_status\":null,"
                + "\"reply_failure\":null,\"server_stop_id\":null}";
    }
}
