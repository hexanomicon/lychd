package org.lychd.companion;

import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.lychd.companion.protocol.StrictJson;
import static org.lychd.companion.protocol.Protocol.*;

/** Private opt-in configuration. Errors intentionally exclude values and parser input. */
public record BridgeConfig(String token, int port, UUID actorId, boolean spawnActor,
                           int spawnX, int spawnZ, int radius, int maxActions,
                           FollowDistancePolicy followDistance, boolean allowWeather, boolean allowTime) {
    public BridgeConfig(String token, int port, UUID actorId, boolean spawnActor,
                        int spawnX, int spawnZ, int radius, int maxActions, FollowDistancePolicy followDistance, boolean allowWeather) {
        this(token, port, actorId, spawnActor, spawnX, spawnZ, radius, maxActions, followDistance, allowWeather, false);
    }
    public BridgeConfig(String token, int port, UUID actorId, boolean spawnActor,
                        int spawnX, int spawnZ, int radius, int maxActions, FollowDistancePolicy followDistance) {
        this(token, port, actorId, spawnActor, spawnX, spawnZ, radius, maxActions, followDistance, false);
    }
    public static BridgeConfig read(Path path) throws IOException {
        if (!Files.exists(path)) return null;
        try {
            if (Files.size(path) > MAX_REQUEST_BYTES) throw new IllegalArgumentException();
            JsonObject o = StrictJson.object(StrictJson.utf8(Files.readAllBytes(path)));
            JsonObject required = o.deepCopy();
            required.remove("follow_stop_distance");
            required.remove("follow_resume_distance");
            required.remove("allow_weather");
            required.remove("allow_time");
            StrictJson.keys(required, "protocol", "token", "port", "actor_id", "spawn_actor", "spawn_x", "spawn_z", "radius", "max_actions");
            String token = StrictJson.string(o, "token");
            long port = StrictJson.integer(o, "port"), x = StrictJson.integer(o, "spawn_x"), z = StrictJson.integer(o, "spawn_z");
            long radius = StrictJson.integer(o, "radius"), max = StrictJson.integer(o, "max_actions");
            if (StrictJson.integer(o, "protocol") != VERSION || !token.matches("[0-9a-f]{64}")
                    || port < 1024 || port > 65535 || x < -29_000_000 || x > 29_000_000
                    || z < -29_000_000 || z > 29_000_000 || radius < 1 || radius > 24 || max < 1 || max > 256)
                throw new IllegalArgumentException();
            var followDistance = new FollowDistancePolicy(
                    o.has("follow_stop_distance") ? StrictJson.number(o, "follow_stop_distance")
                            : FollowDistancePolicy.DEFAULT.stopDistance(),
                    o.has("follow_resume_distance") ? StrictJson.number(o, "follow_resume_distance")
                            : FollowDistancePolicy.DEFAULT.resumeDistance());
            return new BridgeConfig(token, (int) port, StrictJson.uuid(o, "actor_id"), StrictJson.bool(o, "spawn_actor"),
                    (int) x, (int) z, (int) radius, (int) max, followDistance,
                    o.has("allow_weather") && StrictJson.bool(o, "allow_weather"),
                    o.has("allow_time") && StrictJson.bool(o, "allow_time"));
        } catch (RuntimeException e) { throw new IOException("Invalid lychd-bridge.json configuration"); }
    }
    public boolean contains(Point point) {
        return Double.isFinite(point.x()) && Double.isFinite(point.y()) && Double.isFinite(point.z())
                && Math.abs(point.x() - spawnX) <= radius && Math.abs(point.z() - spawnZ) <= radius
                && point.y() >= -64 && point.y() <= 320;
    }
    @Override public String toString() { return "BridgeConfig[private]"; }
}
