package org.lychd.companion;

/** Pure forward-only cumulative clock arithmetic. No engine objects or numeric tick authority. */
public final class ClockPlacement {
    private ClockPlacement() {}
    public record Placement(String mode, long before, long after, int delta, int beforePhase,
                            int afterPhase, long beforeCycle, long afterCycle, int cycleIncrement) {}
    public static Placement compute(long before, String requested) {
        if (before < 0) throw new IllegalArgumentException("negative cumulative clock");
        int phase = (int) (before % 24000);
        String mode = switch (requested) {
            case "day", "night" -> requested;
            case "toggle" -> phase < 12000 ? "night" : "day";
            default -> throw new IllegalArgumentException("unsupported clock mode");
        };
        int target = mode.equals("day") ? 1000 : 13000;
        int delta = Math.floorMod(target - phase, 24000);
        if (before > Long.MAX_VALUE - delta) throw new IllegalArgumentException("cumulative clock overflow");
        long after = before + delta;
        return new Placement(mode, before, after, delta, phase, target, before / 24000,
                after / 24000, (int) (after / 24000 - before / 24000));
    }
}
