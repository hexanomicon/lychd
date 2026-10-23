package org.lychd.companion;

import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.gamerules.GameRules;
import static org.lychd.companion.protocol.Protocol.*;

/** Minecraft thread only. Explicit global weather capability; no NPC controller ownership. */
public final class WorldWeatherController {
    private final MinecraftServer server;
    private final BridgeConfig config;
    private final UUID bootId;

    public WorldWeatherController(MinecraftServer server, BridgeConfig config, UUID bootId) {
        this.server = server; this.config = config; this.bootId = bootId;
    }

    public Outcome apply(Action request, long nowMs) {
        WeatherArgs args = request.weather();
        if (!"weather".equals(request.kind()) || args == null || !args.valid()
                || request.point() != null || request.targetId() != null || request.text() != null || request.time() != null)
            return Outcome.refused("invalid weather request");
        if (!bootId.equals(request.bootId()) || !config.actorId().equals(request.actorId())
                || request.generation() < 0 || nowMs < 0 || request.expiresAtMs() <= nowMs)
            return Outcome.refused("invalid weather envelope");
        if (!config.allowWeather()) return Outcome.refused("server weather capability disabled");
        var world = server.overworld();
        if (!world.canHaveWeather()) return Outcome.refused("overworld weather unavailable");
        if (!world.getGameRules().get(GameRules.ADVANCE_WEATHER))
            return Outcome.refused("weather advancement disabled");
        boolean rain = args.mode().equals("rain");
        server.setWeatherParameters(rain ? 0 : 600, rain ? 600 : 0, rain, false);
        var data = server.getWeatherData();
        return Outcome.weatherApplied(new WeatherObservation("blockworld.weather@1", bootId,
                request.generation(), config.actorId(), "server_weather", "minecraft:overworld", args.mode(), 600,
                data.getClearWeatherTime(), data.getRainTime(), data.getThunderTime(), data.isRaining(),
                data.isThundering(), world.getGameRules().get(GameRules.ADVANCE_WEATHER), world.getGameTime(), nowMs));
    }
}
