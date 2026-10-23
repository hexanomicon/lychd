package org.lychd.voice;

import java.util.Map;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/** Local closed labels; host feedback remains literal text and never becomes a translation key. */
final class HudText {
    private static final Map<String, String[]> WORDS = Map.ofEntries(
            word("record", "Hlas", "Hlas", "Voice"), word("stop", "Stop", "Stop", "Stop"),
            word("hold_requested", "držanie vyžiadané; uvoľni na spracovanie", "držení vyžádáno; uvolni pro zpracování", "hold requested; release to process"),
            word("release_requested", "ukončenie záznamu vyžiadané", "ukončení záznamu vyžádáno", "capture finish requested"),
            word("recording", "prijímanie audia", "přijímání audia", "receiving audio"),
            word("finishing", "ukončovanie záznamu", "ukončování záznamu", "finishing capture"),
            word("requested", "vyžiadané", "vyžádáno", "requested"),
            word("not_sent", "neodoslané", "neodesláno", "not sent"),
            word("pending", "čaká na výsledok", "čeká na výsledek", "result pending"),
            word("known", "výsledok známy", "výsledek známý", "result known"),
            word("refused", "odmietnuté", "odmítnuto", "refused"),
            word("unknown", "výsledok neznámy", "výsledek neznámý", "result unknown"),
            word("unreported", "nehlásené", "nehlášeno", "not reported"),
            word("display_space", "Málo miesta na celý výsledok. Zväčši okno alebo zníž mierku GUI; podrobnosti sú v konzole LychD.",
                    "Málo místa na celý výsledek. Zvětši okno nebo sniž měřítko GUI; podrobnosti jsou v konzoli LychD.",
                    "The full result needs more space. Enlarge the window or lower GUI scale; details are in the LychD console."),
            word("waiting_audio", "čaká na audio", "čeká na audio", "waiting for audio"),
            word("recording_pending", "záznam vyžiadaný", "záznam vyžádán", "capture requested"),
            word("reading_audio", "čítanie audia", "čtení audia", "reading audio"),
            word("transcribing", "prepisovanie", "přepisování", "transcribing"),
            word("queued", "vo fronte", "ve frontě", "queued"),
            word("game", "hra", "hra", "game"), word("reply", "odpoveď", "odpověď", "reply"),
            word("playback", "prehratie", "přehrání", "playback"),
            word("native_evidence", "doklad hry", "doklad hry", "game evidence"),
            word("reply_evidence", "doklad odpovede", "doklad odpovědi", "reply evidence"),
            word("applied", "vykonané", "provedeno", "applied"),
            word("cancelled", "zrušené", "zrušeno", "cancelled"),
            word("expired", "vypršané", "vypršelo", "expired"),
            word("no_action", "bez akcie", "bez akce", "no action"),
            word("clarification", "potrebné spresnenie", "nutné upřesnění", "clarification needed"),
            word("recorded", "uložené", "uloženo", "recorded"),
            word("failed", "zlyhalo", "selhalo", "failed"),
            word("not_requested", "nevyžiadané", "nevyžádáno", "not requested"),
            word("not_attempted", "neskúšané", "nezkoušeno", "not attempted"),
            word("generated", "vygenerované", "vygenerováno", "generated"),
            word("cancelled_server_work_unknown", "zrušené; stav servera neznámy", "zrušeno; stav serveru neznámý", "cancelled; server work unknown"),
            word("player_exited", "prehrávač skončil; počutie nepotvrdené", "přehrávač skončil; slyšení nepotvrzeno", "player exited; hearing unconfirmed"),
            word("interrupted", "prerušené", "přerušeno", "interrupted"),
            word("settlement_unknown", "ukončenie neznáme", "ukončení neznámé", "settlement unknown"),
            word("synthesis_failed", "syntéza zlyhala", "syntéza selhala", "synthesis failed"),
            word("artifact_write_failed", "zápis zlyhal", "zápis selhal", "artifact write failed"),
            word("playback_failed", "prehratie zlyhalo", "přehrání selhalo", "playback failed"),
            word("playback_unsettled", "prehratie neukončené", "přehrání neukončené", "playback unsettled")
    );
    private static Map.Entry<String, String[]> word(String key, String sk, String cs, String en) {
        return Map.entry(key, new String[] {sk, cs, en});
    }
    static String render(VoiceController.Hud hud, String language) {
        return String.join(" · ", paragraphs(hud, language));
    }
    static List<String> paragraphs(VoiceController.Hud hud, String language) {
        int locale = locale(language);
        List<String> text = new ArrayList<>();
        text.add(header(hud, locale));
        text.add(label(hud.localStage(), locale) + (hud.phase() == null ? "" : " · " + label(hud.phase(), locale)));
        Protocol.Operation result = hud.result();
        if (result != null) {
            field(text, "game", result.gameKind(), locale);
            field(text, "reply", result.replyStatus(), locale);
            field(text, "playback", result.playback(), locale);
            field(text, "native_evidence", result.nativeEvidence(), locale);
            field(text, "reply_evidence", result.replyEvidence(), locale);
            if (result.replyFailure() != null) text.add(label(result.replyFailure(), locale));
            if (result.feedback() != null && !result.feedback().isEmpty()) text.add(result.feedback());
        }
        return List.copyOf(text);
    }
    /** Wrap complete semantic rows. Never show a success-only subset when the full result cannot fit. */
    static List<String> panel(VoiceController.Hud hud, String language,
                              Function<String, List<String>> wrap, int maximumLines) {
        List<String> lines = new ArrayList<>();
        for (String paragraph : paragraphs(hud, language)) lines.addAll(wrap.apply(paragraph));
        if (lines.size() <= maximumLines) return List.copyOf(lines);
        lines.clear();
        lines.addAll(wrap.apply(header(hud, locale(language))));
        lines.addAll(wrap.apply(label("display_space", locale(language))));
        return lines.size() <= maximumLines ? List.copyOf(lines) : List.of();
    }
    private static int locale(String language) {
        return language != null && language.startsWith("sk") ? 0 : language != null && language.startsWith("cs") ? 1 : 2;
    }
    private static String header(VoiceController.Hud hud, int locale) {
        return "LychD " + label(hud.operation(), locale) + " [" + hud.requestId().substring(0, 8) + "]";
    }
    private static void field(List<String> out, String name, String value, int language) {
        out.add(label(name, language) + ": " + label(value == null ? "unreported" : value, language));
    }
    private static String label(String key, int locale) {
        String[] words = WORDS.get(key);
        return words == null ? WORDS.get("unknown")[locale] : words[locale];
    }
}
