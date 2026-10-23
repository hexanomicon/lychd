package org.lychd.companion;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ClockPlacementTest {
    @Test void exactMarkersAndBoundaryPlacementAreForwardOnly() {
        long[][] cases = {{0,1000,13000},{999,1000,13000},{1000,1000,13000},
                {1001,25000,13000},{11999,25000,13000},{12000,25000,13000},
                {12999,25000,13000},{13000,25000,13000},{13001,25000,37000},
                {23999,25000,37000},{24000,25000,37000}};
        for (long[] c : cases) {
            assertEquals(c[1], ClockPlacement.compute(c[0], "day").after());
            assertEquals(c[2], ClockPlacement.compute(c[0], "night").after());
        }
        assertEquals("night", ClockPlacement.compute(11999, "toggle").mode());
        assertEquals("day", ClockPlacement.compute(12000, "toggle").mode());
        assertEquals("night", ClockPlacement.compute(24000, "toggle").mode());
        assertEquals(23999, ClockPlacement.compute(1001, "day").delta());
        assertEquals(0, ClockPlacement.compute(25000, "day").delta());
    }
    @Test void wholeCyclePropertiesHoldForEveryPhaseAndLargeCalendar() {
        for (long base : new long[]{0, 24000, 8_000_000_000_000_000_000L / 24000 * 24000})
            for (int phase = 0; phase < 24000; phase++)
                for (String mode : new String[]{"day", "night", "toggle"}) {
                    var p = ClockPlacement.compute(base + phase, mode);
                    assertTrue(p.after() >= p.before()); assertTrue(p.delta() >= 0 && p.delta() < 24000);
                    assertEquals(p.after() - p.before(), p.delta());
                    assertEquals(p.after() % 24000, p.afterPhase());
                    assertEquals(p.after() / 24000 - p.before() / 24000, p.cycleIncrement());
                    assertTrue(p.cycleIncrement() == 0 || p.cycleIncrement() == 1);
                }
    }
    @Test void negativeInputAndOverflowRefuseWhileLastRepresentableMarkersWork() {
        assertThrows(IllegalArgumentException.class, () -> ClockPlacement.compute(-1, "day"));
        assertThrows(IllegalArgumentException.class, () -> ClockPlacement.compute(0, "noon"));
        for (String mode : new String[]{"day", "night", "toggle"})
            assertThrows(IllegalArgumentException.class, () -> ClockPlacement.compute(Long.MAX_VALUE, mode));
        for (int marker : new int[]{1000, 13000}) {
            long last = Long.MAX_VALUE - Math.floorMod(Long.MAX_VALUE - marker, 24000);
            String mode = marker == 1000 ? "day" : "night";
            assertEquals(last, ClockPlacement.compute(last, mode).after());
            assertEquals(last, ClockPlacement.compute(last - 1, mode).after());
            assertThrows(IllegalArgumentException.class, () -> ClockPlacement.compute(last + 1, mode));
        }
    }
}
