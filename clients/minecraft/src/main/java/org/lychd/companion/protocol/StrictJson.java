package org.lychd.companion.protocol;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import com.google.gson.Strictness;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.io.IOException;
import java.io.StringReader;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.UUID;
import static org.lychd.companion.protocol.Protocol.*;

/** Strict bounded JSON and exact request schemas. Gson's object adapter alone accepts duplicates. */
public final class StrictJson {
    public static final Gson GSON = new GsonBuilder().serializeNulls().disableHtmlEscaping().create();
    private StrictJson() {}

    public static String utf8(byte[] bytes) {
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        } catch (CharacterCodingException e) { throw bad("invalid UTF-8"); }
    }
    public static JsonObject object(String body) {
        try (JsonReader reader = new JsonReader(new StringReader(body))) {
            reader.setStrictness(Strictness.STRICT);
            JsonElement value = read(reader, 0);
            if (reader.peek() != JsonToken.END_DOCUMENT || !value.isJsonObject()) throw bad("expected one object");
            return value.getAsJsonObject();
        } catch (IOException | IllegalStateException | NumberFormatException e) { throw bad("invalid JSON"); }
    }
    private static JsonElement read(JsonReader reader, int depth) throws IOException {
        if (depth > 8) throw bad("JSON nesting limit");
        return switch (reader.peek()) {
            case BEGIN_OBJECT -> {
                reader.beginObject();
                JsonObject object = new JsonObject();
                while (reader.hasNext()) {
                    String name = reader.nextName();
                    if (object.has(name)) throw bad("duplicate key");
                    object.add(name, read(reader, depth + 1));
                }
                reader.endObject();
                yield object;
            }
            case BEGIN_ARRAY -> {
                reader.beginArray();
                JsonArray array = new JsonArray();
                while (reader.hasNext()) array.add(read(reader, depth + 1));
                reader.endArray();
                yield array;
            }
            case STRING -> new JsonPrimitive(reader.nextString());
            case NUMBER -> {
                String literal = reader.nextString();
                double number = Double.parseDouble(literal);
                if (!Double.isFinite(number)) throw bad("nonfinite number");
                // Preserve integer precision for generation and millisecond deadlines.
                yield new JsonPrimitive(new ExactNumber(literal));
            }
            case BOOLEAN -> new JsonPrimitive(reader.nextBoolean());
            case NULL -> { reader.nextNull(); yield JsonNull.INSTANCE; }
            default -> throw bad("invalid JSON value");
        };
    }
    /** BigDecimal normalizes 0e0 to 0, which would defeat original-integer validation. */
    private static final class ExactNumber extends Number {
        private final String literal;
        private final java.math.BigDecimal value;
        ExactNumber(String literal) { this.literal = literal; this.value = new java.math.BigDecimal(literal); }
        @Override public int intValue() { return value.intValue(); }
        @Override public long longValue() { return value.longValue(); }
        @Override public float floatValue() { return value.floatValue(); }
        @Override public double doubleValue() { return value.doubleValue(); }
        @Override public String toString() { return literal; }
    }
    public static void keys(JsonObject o, String... required) {
        if (!o.keySet().equals(Set.of(required))) throw bad("missing or unknown field");
    }
    public static String string(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isString()) throw bad("expected string");
        String s = e.getAsString();
        // Unpaired surrogate escapes are not valid Unicode scalar values.
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (++i >= s.length() || !Character.isLowSurrogate(s.charAt(i))) throw bad("invalid Unicode");
            } else if (Character.isLowSurrogate(c)) throw bad("invalid Unicode");
        }
        return s;
    }
    public static long integer(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isNumber()) throw bad("expected integer");
        if (!e.getAsString().matches("-?(0|[1-9][0-9]*)")) throw bad("expected integer literal");
        try { return e.getAsBigDecimal().longValueExact(); }
        catch (ArithmeticException | NumberFormatException ex) { throw bad("expected bounded integer"); }
    }
    public static double number(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isNumber()) throw bad("expected number");
        double n = e.getAsDouble();
        if (!Double.isFinite(n)) throw bad("nonfinite number");
        return n;
    }
    public static boolean bool(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isBoolean()) throw bad("expected boolean");
        return e.getAsBoolean();
    }
    public static UUID uuid(String s) {
        try {
            UUID id = UUID.fromString(s);
            if (!id.toString().equals(s)) throw bad("expected canonical UUID");
            return id;
        } catch (IllegalArgumentException e) { throw bad("expected canonical UUID"); }
    }
    public static UUID uuid(JsonObject o, String key) { return uuid(string(o, key)); }
    private static void version(JsonObject o) {
        if (integer(o, "protocol") != VERSION) throw bad("unsupported protocol");
    }
    public static Action action(String body) {
        JsonObject o = object(body);
        keys(o, "protocol", "boot_id", "generation", "actor_id", "run_id", "action_id", "expires_at_ms", "kind", "args");
        version(o);
        long generation = integer(o, "generation");
        if (generation < 0) throw bad("negative generation");
        String kind = string(o, "kind");
        if (!o.get("args").isJsonObject()) throw bad("expected args object");
        JsonObject args = o.getAsJsonObject("args");
        Point point = null;
        UUID target = null;
        String text = null;
        WeatherArgs weather = null;
        TimeArgs time = null;
        switch (kind) {
            case "state", "idle" -> keys(args);
            case "look", "goto" -> {
                keys(args, "x", "y", "z");
                point = new Point(number(args, "x"), number(args, "y"), number(args, "z"));
            }
            case "inspect" -> {
                keys(args, "revision", "x", "y", "z");
                if (integer(args, "revision") != 1) throw bad("unsupported inspection revision");
                long x = integer(args, "x"), y = integer(args, "y"), z = integer(args, "z");
                if (x < -30_000_000 || x > 30_000_000 || y < -30_000_000 || y > 30_000_000
                        || z < -30_000_000 || z > 30_000_000) throw bad("cell outside coordinate bounds");
                point = new Point(x, y, z);
            }
            case "follow" -> { keys(args, "target_id"); target = uuid(args, "target_id"); }
            case "time" -> {
                keys(args, "revision", "scope", "mode");
                if (integer(args, "revision") != 1) throw bad("unsupported time revision");
                time = new TimeArgs(1, string(args, "scope"), string(args, "mode"));
                if (!time.valid()) throw bad("unsupported time scope or mode");
            }
            case "weather" -> {
                keys(args, "revision", "scope", "mode", "duration_ticks");
                if (integer(args, "revision") != 1 || integer(args, "duration_ticks") != 600)
                    throw bad("unsupported weather revision or duration");
                weather = new WeatherArgs(1, string(args, "scope"), string(args, "mode"), 600);
                if (!weather.valid()) throw bad("unsupported weather scope or mode");
            }
            case "say" -> {
                keys(args, "text");
                text = string(args, "text");
                if (text.isBlank() || text.codePointCount(0, text.length()) > 200 || text.stripLeading().startsWith("/")
                        || text.codePoints().anyMatch(c -> Character.isISOControl(c) || Character.getType(c) == Character.FORMAT))
                    throw bad("invalid ordinary chat text");
            }
            default -> throw bad("unsupported action kind");
        }
        return new Action(uuid(o, "boot_id"), generation, uuid(o, "actor_id"), uuid(o, "run_id"),
                uuid(o, "action_id"), integer(o, "expires_at_ms"), kind, point, target, text, weather, time);
    }
    public static Stop stop(String body) {
        JsonObject o = object(body);
        keys(o, "protocol", "boot_id", "actor_id", "run_id", "action_id");
        version(o);
        return new Stop(uuid(o, "boot_id"), uuid(o, "actor_id"), uuid(o, "run_id"), uuid(o, "action_id"));
    }
    private static Rejection bad(String detail) { return new Rejection(400, detail); }
}
