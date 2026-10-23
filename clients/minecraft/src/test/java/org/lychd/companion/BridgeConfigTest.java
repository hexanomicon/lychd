package org.lychd.companion;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class BridgeConfigTest {
    @TempDir Path temporary;
    private static String configuration(String optional) {
        return "{\"protocol\":1,\"token\":\"" + "a".repeat(64) + "\",\"port\":18184,"
                + "\"actor_id\":\"00000000-0000-4000-8000-000000000002\",\"spawn_actor\":true,"
                + "\"spawn_x\":0,\"spawn_z\":0,\"radius\":24,\"max_actions\":256" + optional + "}";
    }
    private BridgeConfig read(String document) throws Exception {
        Path file = temporary.resolve("lychd-bridge.json");
        Files.writeString(file, document);
        return BridgeConfig.read(file);
    }
    @Test void absentConfigurationIsInertAndInvalidTokenNeverAppearsInException() throws Exception {
        Path file = temporary.resolve("lychd-bridge.json");
        assertNull(BridgeConfig.read(file));
        assertFalse(Files.exists(file));
        String secret = "private-secret-must-not-appear";
        Files.writeString(file, "{\"token\":\"" + secret + "\"}");
        var error = assertThrows(java.io.IOException.class, () -> BridgeConfig.read(file));
        assertFalse(error.toString().contains(secret));
        assertNull(error.getCause());
    }
    @Test void existingExactConfigurationKeepsItsFieldsAndGetsDefaultFollowDistances() throws Exception {
        var config = read(configuration(""));
        assertEquals(FollowDistancePolicy.DEFAULT, config.followDistance());
        assertEquals(18184, config.port());
        assertEquals(24, config.radius());
        assertEquals(256, config.maxActions());
        assertTrue(config.spawnActor());
        assertEquals("BridgeConfig[private]", config.toString());
    }
    @Test void optionalDistancesCanBeCustomizedTogetherOrIndependently() throws Exception {
        assertEquals(new FollowDistancePolicy(1.5, 4), read(configuration(
                ",\"follow_stop_distance\":1.5,\"follow_resume_distance\":4")).followDistance());
        assertEquals(new FollowDistancePolicy(0.5, 3), read(configuration(
                ",\"follow_stop_distance\":0.5")).followDistance());
        assertEquals(new FollowDistancePolicy(2, 8), read(configuration(
                ",\"follow_resume_distance\":8")).followDistance());
    }
    @Test void invalidOptionalTypesNumbersBandsAndUnknownFieldsStayValueFree() {
        String[] invalid = {",\"follow_stop_distance\":true", ",\"follow_resume_distance\":false",
                ",\"follow_stop_distance\":\"2\"", ",\"follow_resume_distance\":null",
                ",\"follow_stop_distance\":NaN", ",\"follow_resume_distance\":1e999",
                ",\"follow_stop_distance\":0.49", ",\"follow_stop_distance\":3",
                ",\"follow_resume_distance\":2", ",\"follow_resume_distance\":8.01",
                ",\"follow_stop_distance\":4,\"follow_resume_distance\":3",
                ",\"follow_stop_distance\":1,\"follow_stop_distance\":2",
                ",\"follow_resume_distances\":4", ",\"unknown\":1"};
        for (String optional : invalid) {
            var error = assertThrows(java.io.IOException.class, () -> read(configuration(optional)));
            assertEquals("Invalid lychd-bridge.json configuration", error.getMessage());
            assertFalse(error.toString().contains("a".repeat(64)));
            assertNull(error.getCause());
        }
    }
    @Test void optionalFieldsDoNotMakeAnOldRequiredFieldOptional() {
        String document = configuration(",\"follow_stop_distance\":1").replace(",\"max_actions\":256", "");
        assertThrows(java.io.IOException.class, () -> read(document));
    }
}
