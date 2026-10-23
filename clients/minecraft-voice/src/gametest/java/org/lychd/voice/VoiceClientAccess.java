package org.lychd.voice;

import java.lang.reflect.Field;

/** Test witness only, not a delivery API. Exactly two reads; no setters or method invocation. */
public final class VoiceClientAccess {
    private static final Field CONTROLLER = field("controller");
    private static final Field PROFILE = field("profile");
    private final VoiceClient client;
    VoiceClientAccess(VoiceClient client) { this.client = client; }
    VoiceController lychdFixtureController() { return (VoiceController) read(CONTROLLER); }
    Profile lychdFixtureProfile() { return (Profile) read(PROFILE); }
    private static Field field(String name) {
        try {
            Field field = VoiceClient.class.getDeclaredField(name);
            FixtureObservation.check(field.trySetAccessible(), "read-only production witness access");
            return field;
        } catch (ReflectiveOperationException exception) {
            throw new IllegalStateException("Client control fixture production witness unavailable");
        }
    }
    private Object read(Field field) {
        try { return field.get(client); }
        catch (IllegalAccessException exception) {
            throw new IllegalStateException("Client control fixture production witness unavailable");
        }
    }
}
