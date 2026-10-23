package org.lychd.companion;

import java.io.IOException;
import java.util.List;
import java.util.UUID;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.loader.api.FabricLoader;
import org.lychd.companion.protocol.ActionInbox;
import org.lychd.companion.protocol.BridgeHttpServer;
import org.lychd.companion.protocol.Protocol.State;

/** Opt-in dedicated-server delivery client. Missing private config has no listener/actor effects. */
public final class LychdBridge implements ModInitializer {
    private static final UUID BOOT_ID = UUID.randomUUID();
    private WolfController controller;
    private CompanionActuator actuator;
    private ActionInbox inbox;
    private BridgeHttpServer http;

    @Override public void onInitialize() {
        final BridgeConfig config;
        try { config = BridgeConfig.read(FabricLoader.getInstance().getConfigDir().resolve("lychd-bridge.json")); }
        catch (IOException e) { throw new IllegalStateException("Unable to load private companion configuration"); }
        if (config == null) return;
        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            try {
                controller = new WolfController(server, config, BOOT_ID);
                actuator = new CompanionActuator(controller, new WorldWeatherController(server, config, BOOT_ID),
                        new WorldClockController(server, config, BOOT_ID));
                State initial = new State(1, BOOT_ID, 0, config.actorId(), "unavailable", null, null, null,
                        0, null, List.of(), System.currentTimeMillis());
                inbox = new ActionInbox(BOOT_ID, config.actorId(), config.maxActions(), initial, config::contains);
                inbox.tick(System.currentTimeMillis(), actuator);
                http = new BridgeHttpServer(config.port(), config.token(), inbox);
                http.start();
            } catch (IOException | RuntimeException | Error e) {
                closeBridge();
                throw new IllegalStateException("Unable to initialize companion bridge", e);
            }
        });
        ServerTickEvents.START_SERVER_TICK.register(server -> {
            if (inbox != null && actuator != null) inbox.tick(System.currentTimeMillis(), actuator);
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> closeBridge());
    }
    private void closeBridge() {
        try { if (http != null) http.close(); }
        finally {
            http = null;
            try { if (controller != null) controller.close(); }
            finally { controller = null; actuator = null; inbox = null; }
        }
    }
}
