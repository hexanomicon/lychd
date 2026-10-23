package org.lychd.voice;

import java.lang.reflect.Field;

/** Exact source-bound read-only witness. Callers hold the original controller monitor. */
public final class VoiceControllerAccess {
    private static final Field STATE = field("state");
    private static final Field STATE_AT = field("stateAt");
    private static final Field CLOSED = field("closed");
    private final VoiceController controller;
    VoiceControllerAccess(VoiceController controller) { this.controller = controller; }
    Protocol.State lychdFixtureState() { return (Protocol.State) read(STATE); }
    long lychdFixtureStateAt() { return (Long) read(STATE_AT); }
    boolean lychdFixtureClosed() { return (Boolean) read(CLOSED); }
    private static Field field(String name) {
        try {
            Field field = VoiceController.class.getDeclaredField(name);
            FixtureObservation.check(field.trySetAccessible(), "read-only controller witness access");
            return field;
        } catch (ReflectiveOperationException exception) {
            throw new IllegalStateException("Client control fixture controller witness unavailable");
        }
    }
    private Object read(Field field) {
        FixtureObservation.check(Thread.holdsLock(controller), "controller witness monitor");
        try { return field.get(controller); }
        catch (IllegalAccessException exception) {
            throw new IllegalStateException("Client control fixture controller witness unavailable");
        }
    }
}
