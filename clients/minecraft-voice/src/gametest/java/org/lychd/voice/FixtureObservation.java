package org.lychd.voice;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.Minecraft;

/** Bounded, body-free observations; credential/header/body values never enter a receipt or failure. */
public final class FixtureObservation {
    private static VoiceClient client;
    private static int initializations;
    private static final ArrayDeque<String> hud = new ArrayDeque<>();
    private static final List<String> panel = new ArrayList<>();
    private static int extractions, renderedPanels, maximumTextWidth, maximumBottom, guiWidth, guiHeight;
    private static boolean geometryHealthy = true;
    static volatile int readableCases;
    static volatile boolean hiddenHudChecked, menuHudChecked;
    static volatile ProtocolFixture fixture;
    static volatile boolean scenariosPassed, fixedScenariosPassed, heldScenariosPassed;

    private FixtureObservation() { }
    public static synchronized void initialized(VoiceClient instance) {
        client = instance;
        initializations++;
        FixtureLifecycle.observeProductionStopping();
    }
    static synchronized VoiceClientAccess client() {
        check(initializations == 1 && client != null, "production initialization count");
        VoiceClientAccess view = new VoiceClientAccess(client);
        check(view.lychdFixtureController() != null && view.lychdFixtureProfile() != null,
                "production controls were inert");
        return view;
    }
    static Protocol.State state() {
        VoiceController controller = client().lychdFixtureController();
        synchronized (controller) { return new VoiceControllerAccess(controller).lychdFixtureState(); }
    }
    static long stateAt() {
        VoiceController controller = client().lychdFixtureController();
        synchronized (controller) { return new VoiceControllerAccess(controller).lychdFixtureStateAt(); }
    }
    public static synchronized void drawn(String text, int x, int y, int width, int lineHeight, int screenWidth, int screenHeight) {
        ProtocolFixture current = fixture;
        if (current == null || text.length() > 1024 || x != 8) return;
        boolean header = y == 8 && text.startsWith("LychD ") && current.ownsHud(text);
        if (header) {
            panel.clear(); renderedPanels++;
            if (hud.size() == 64) hud.removeFirst();
            hud.addLast(text);
        }
        if ((!header && panel.isEmpty()) || panel.size() >= 64 || y != 8 + panel.size() * lineHeight) return;
        panel.add(text);
        geometryHealthy &= width <= screenWidth - 16 && y + lineHeight <= screenHeight - 4;
        maximumTextWidth = Math.max(maximumTextWidth, width);
        maximumBottom = Math.max(maximumBottom, y + lineHeight);
        guiWidth = screenWidth; guiHeight = screenHeight;
    }
    static synchronized boolean sawPanel(List<String> text) { return panel.equals(text); }
    public static synchronized void guiExtraction() { extractions++; }
    static synchronized int extractions() { return extractions; }
    static synchronized int renderedPanels() { return renderedPanels; }
    static synchronized boolean geometryHealthy() { return geometryHealthy; }
    static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError("Client control fixture: " + label);
    }
    static void stopping(Minecraft minecraft) {
        boolean productionClosed = false;
        VoiceClient captured;
        int initCount;
        int hudCount;
        synchronized (FixtureObservation.class) {
            captured = client; initCount = initializations; hudCount = hud.size();
        }
        if (captured != null) {
            VoiceController controller = new VoiceClientAccess(captured).lychdFixtureController();
            if (controller != null) synchronized (controller) {
                productionClosed = new VoiceControllerAccess(controller).lychdFixtureClosed();
            }
        }
        boolean productionWorkersDead = Thread.getAllStackTraces().keySet().stream()
                .noneMatch(thread -> thread.isAlive() && thread.getName().startsWith("lychd-voice-"));
        ProtocolFixture current = fixture;
        boolean fixtureClosed = current != null && current.closeAndAudit();
        int records = current == null ? 0 : current.records();
        int stops = current == null ? 0 : current.stops();
        int holds = current == null ? 0 : current.holds();
        int releases = current == null ? 0 : current.releases();
        int heldStops = current == null ? 0 : current.heldStops();
        boolean protocolHealthy = current != null && current.healthy();
        String receipt = "{\"protocol\":1,\"actual_client_stopping\":true,\"production_initializations\":"
                + initCount + ",\"scenarios_passed\":" + scenariosPassed
                + ",\"production_closed\":" + productionClosed
                + ",\"production_workers_dead\":" + productionWorkersDead
                + ",\"fixture_closed_and_workers_dead\":" + fixtureClosed
                + ",\"protocol_healthy\":" + protocolHealthy
                + ",\"record_ingress\":" + records + ",\"stop_ingress\":" + stops
                + ",\"hold_ingress\":" + holds + ",\"release_ingress\":" + releases
                + ",\"held_stop_ingress\":" + heldStops
                + ",\"fixed_scenarios_passed\":" + fixedScenariosPassed
                + ",\"held_scenarios_passed\":" + heldScenariosPassed
                + ",\"own_hud_observations\":" + hudCount
                + ",\"readable_cases\":" + readableCases + ",\"hidden_hud_checked\":" + hiddenHudChecked
                + ",\"menu_hud_checked\":" + menuHudChecked + ",\"geometry_healthy\":" + geometryHealthy
                + ",\"gui_width\":" + guiWidth + ",\"gui_height\":" + guiHeight
                + ",\"maximum_text_width\":" + maximumTextWidth + ",\"maximum_bottom\":" + maximumBottom + "}\n";
        try {
            Files.writeString(minecraft.gameDirectory.toPath().resolve("lychd-client-control-audit.json"),
                    receipt, StandardCharsets.US_ASCII, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        } catch (IOException exception) {
            throw new IllegalStateException("Client control fixture audit write failed");
        }
        check(initCount == 1 && scenariosPassed && productionClosed && productionWorkersDead
                && fixtureClosed && protocolHealthy && records == 5 && stops == 5 && heldStops == 1
                && holds == 2 && releases == 1 && fixedScenariosPassed && heldScenariosPassed && hudCount > 0
                && readableCases == 5 && hiddenHudChecked && menuHudChecked && geometryHealthy,
                "actual lifecycle audit failed");
    }
}
