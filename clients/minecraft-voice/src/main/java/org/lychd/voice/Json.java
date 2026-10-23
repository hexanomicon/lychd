package org.lychd.voice;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/** Closed, bounded JSON subset used by this protocol: no arrays, floating point or duplicates. */
final class Json {
    private final String text;
    private int at;
    private Json(String text) { this.text = text; }

    static Map<String, Object> object(byte[] bytes, int limit) {
        if (bytes.length > limit) throw invalid();
        try {
            String text = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
            Json parser = new Json(text);
            Map<String, Object> result = parser.map(0);
            parser.space();
            if (parser.at != text.length()) throw invalid();
            return result;
        } catch (CharacterCodingException exception) { throw invalid(); }
    }

    private Map<String, Object> map(int depth) {
        if (depth > 4) throw invalid();
        space(); take('{'); space();
        Map<String, Object> result = new LinkedHashMap<>();
        if (peek('}')) { at++; return result; }
        do {
            space(); String key = string(); space(); take(':'); space();
            if (key.length() > 64 || result.containsKey(key) || result.size() >= 32) throw invalid();
            result.put(key, value(depth + 1)); space();
            if (peek('}')) { at++; return result; }
            take(',');
        } while (true);
    }

    private Object value(int depth) {
        if (peek('{')) return map(depth);
        if (peek('"')) return string();
        for (String keyword : new String[] {"true", "false", "null"}) {
            if (text.startsWith(keyword, at)) {
                at += keyword.length();
                return keyword.equals("null") ? null : Boolean.valueOf(keyword);
            }
        }
        int start = at;
        if (peek('-')) at++;
        if (peek('0')) at++;
        else {
            if (at >= text.length() || text.charAt(at) < '1' || text.charAt(at) > '9') throw invalid();
            while (at < text.length() && text.charAt(at) >= '0' && text.charAt(at) <= '9') at++;
        }
        try { return Long.valueOf(text.substring(start, at)); }
        catch (NumberFormatException exception) { throw invalid(); }
    }

    private String string() {
        take('"'); StringBuilder out = new StringBuilder();
        while (at < text.length()) {
            char ch = text.charAt(at++);
            if (ch == '"') {
                String value = out.toString();
                for (int i = 0; i < value.length(); i++) {
                    char c = value.charAt(i);
                    if (Character.isHighSurrogate(c)) {
                        if (++i >= value.length() || !Character.isLowSurrogate(value.charAt(i))) throw invalid();
                    } else if (Character.isLowSurrogate(c)) throw invalid();
                }
                return value;
            }
            if (ch < 32) throw invalid();
            if (ch == '\\') {
                if (at >= text.length()) throw invalid();
                char escape = text.charAt(at++);
                ch = switch (escape) {
                    case '"', '\\', '/' -> escape;
                    case 'b' -> '\b'; case 'f' -> '\f'; case 'n' -> '\n';
                    case 'r' -> '\r'; case 't' -> '\t';
                    case 'u' -> {
                        if (at + 4 > text.length()) throw invalid();
                        int code = 0;
                        for (int i = 0; i < 4; i++) {
                            int digit = Character.digit(text.charAt(at++), 16);
                            if (digit < 0) throw invalid();
                            code = code * 16 + digit;
                        }
                        yield (char) code;
                    }
                    default -> throw invalid();
                };
            }
            out.append(ch);
            if (out.length() > 4096) throw invalid();
        }
        throw invalid();
    }

    private void space() {
        while (at < text.length() && " \n\r\t".indexOf(text.charAt(at)) >= 0) at++;
    }
    private boolean peek(char ch) { return at < text.length() && text.charAt(at) == ch; }
    private void take(char ch) { if (!peek(ch)) throw invalid(); at++; }
    static IllegalArgumentException invalid() { return new IllegalArgumentException("Invalid voice control data"); }
}
