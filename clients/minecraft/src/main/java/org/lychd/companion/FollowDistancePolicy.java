package org.lychd.companion;

/** Pure follow hysteresis; distances do not grant navigation or extend a controller lease. */
public record FollowDistancePolicy(double stopDistance, double resumeDistance) {
    public static final FollowDistancePolicy DEFAULT = new FollowDistancePolicy(2, 3);
    public enum Decision { WAIT, STOP, NAVIGATE, CONTINUE }

    public FollowDistancePolicy {
        if (!Double.isFinite(stopDistance) || !Double.isFinite(resumeDistance)
                || stopDistance < 0.5 || stopDistance >= resumeDistance || resumeDistance > 8)
            throw new IllegalArgumentException("Invalid follow distance band");
    }

    public Decision decide(boolean pursuing, double distanceSquared, boolean refreshPath) {
        if (!Double.isFinite(distanceSquared) || distanceSquared < 0)
            throw new IllegalArgumentException("Invalid follow separation");
        if (!pursuing)
            return distanceSquared > resumeDistance * resumeDistance ? Decision.NAVIGATE : Decision.WAIT;
        if (distanceSquared <= stopDistance * stopDistance) return Decision.STOP;
        return refreshPath ? Decision.NAVIGATE : Decision.CONTINUE;
    }
}
