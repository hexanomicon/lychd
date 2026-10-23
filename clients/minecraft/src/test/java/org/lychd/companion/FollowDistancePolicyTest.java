package org.lychd.companion;

import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.lychd.companion.FollowDistancePolicy.Decision.*;

class FollowDistancePolicyTest {
    @Test void nearbyAdmissionWaitsWithoutAskingForNavigationAndResumeRequiresCrossingOuterBoundary() {
        var policy = FollowDistancePolicy.DEFAULT;
        for (double distance : new double[] {0, 1, 2, 2.5, 3}) {
            assertEquals(WAIT, policy.decide(false, distance * distance, false));
            assertEquals(WAIT, policy.decide(false, distance * distance, true));
        }
        double beyond = Math.nextUp(3.0);
        assertEquals(NAVIGATE, policy.decide(false, beyond * beyond, false));
    }
    @Test void pursuingStopsAtInnerBoundaryAndRetainsItsStateInsideTheBand() {
        var policy = FollowDistancePolicy.DEFAULT;
        assertEquals(STOP, policy.decide(true, 2 * 2, false));
        assertEquals(STOP, policy.decide(true, 2 * 2, true));
        assertEquals(STOP, policy.decide(true, 0, true));
        double aboveStop = Math.nextUp(2.0);
        for (double distance : new double[] {aboveStop, 2.5, 3, 4}) {
            assertEquals(CONTINUE, policy.decide(true, distance * distance, false));
            assertEquals(NAVIGATE, policy.decide(true, distance * distance, true));
        }
    }
    @Test void oscillatingNearEitherBoundaryDoesNotRepeatedlyStartAndStopNavigation() {
        var policy = FollowDistancePolicy.DEFAULT;
        boolean pursuing = false;
        var expected = List.of(WAIT, WAIT, NAVIGATE, CONTINUE, CONTINUE, STOP, WAIT, WAIT, NAVIGATE);
        double[] distances = {2, 3, 3.1, 2.9, 2.01, 2, 2.1, 3, 3.1};
        for (int i = 0; i < distances.length; i++) {
            var decision = policy.decide(pursuing, distances[i] * distances[i], false);
            assertEquals(expected.get(i), decision, "step " + i);
            pursuing = switch (decision) {
                case NAVIGATE -> true;
                case STOP, WAIT -> false;
                case CONTINUE -> pursuing;
            };
        }
    }
    @Test void customBandAcceptsTheAllowedEndpointsAndUsesTheirExactThresholds() {
        var policy = new FollowDistancePolicy(0.5, 8);
        assertEquals(STOP, policy.decide(true, 0.5 * 0.5, true));
        assertEquals(CONTINUE, policy.decide(true, 1, false));
        assertEquals(WAIT, policy.decide(false, 8 * 8, true));
        double beyond = Math.nextUp(8.0);
        assertEquals(NAVIGATE, policy.decide(false, beyond * beyond, false));
    }
    @Test void invalidBandsAndUnusableSeparationsRefuseWithoutValuesInErrors() {
        double[][] invalid = {{0.49, 3}, {2, 2}, {3, 2}, {2, 8.01},
                {Double.NaN, 3}, {2, Double.NaN}, {Double.NEGATIVE_INFINITY, 3},
                {2, Double.POSITIVE_INFINITY}};
        for (double[] band : invalid) {
            var error = assertThrows(IllegalArgumentException.class,
                    () -> new FollowDistancePolicy(band[0], band[1]));
            assertEquals("Invalid follow distance band", error.getMessage());
        }
        for (double distanceSquared : new double[] {-1, Double.NaN, Double.POSITIVE_INFINITY})
            assertThrows(IllegalArgumentException.class,
                    () -> FollowDistancePolicy.DEFAULT.decide(false, distanceSquared, false));
    }
}
