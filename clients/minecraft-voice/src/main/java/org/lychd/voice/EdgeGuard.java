package org.lychd.voice;

/** Pure physical edge state. Every boundary requires all three controls released before another action. */
final class EdgeGuard {
    enum Action { NONE, RECORD, HOLD, RELEASE, STOP }
    record Input(Object world, boolean matched, boolean focused, boolean menuFree, boolean paused,
                 boolean recordDown, boolean holdDown, boolean stopDown, boolean menuStopSafe, boolean recordStopSame, boolean holdStopSame) { }
    private Object world;
    private boolean matched, focused, menuFree, paused, initialized, armed, recordDown, holdDown, stopDown;
    private long contextVersion = -1;
    private long epoch;

    record Decision(Action action, boolean lostWorldOrFocus, boolean boundary, long epoch) { }
    Decision update(Input input, long context) {
        boolean boundary = !initialized || world != input.world || matched != input.matched || focused != input.focused
                || menuFree != input.menuFree || paused != input.paused || contextVersion != context;
        boolean lost = initialized && matched && focused && (!input.matched || !input.focused || world != input.world);
        if (boundary) { epoch++; armed = false; }
        Action action = Action.NONE;
        boolean stopEdge = input.stopDown && !stopDown;
        boolean recordEdge = input.recordDown && !recordDown;
        boolean holdEdge = input.holdDown && !holdDown;
        if (armed && !boundary && input.matched && input.focused) {
            if ((stopEdge || input.recordStopSame && recordEdge || input.holdStopSame && holdEdge)
                    && (input.menuFree || input.menuStopSafe)) action = Action.STOP;
            else if (!input.stopDown && input.menuFree && !input.paused) {
                if (holdDown && !input.holdDown) action = Action.RELEASE;
                else if (!(input.recordDown && input.holdDown)) {
                    if (holdEdge) action = Action.HOLD;
                    else if (recordEdge) action = Action.RECORD;
                }
            }
        }
        if (!input.recordDown && !input.holdDown && !input.stopDown) armed = true;
        world = input.world; matched = input.matched; focused = input.focused; menuFree = input.menuFree;
        paused = input.paused; recordDown = input.recordDown; holdDown = input.holdDown; stopDown = input.stopDown;
        contextVersion = context; initialized = true;
        return new Decision(action, lost, boundary, epoch);
    }
    long epoch() { return epoch; }
}
