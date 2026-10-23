package org.lychd.voice;

import com.mojang.blaze3d.platform.InputConstants;
import java.io.IOException;
import java.util.Properties;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.TestInput;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestDedicatedServerConnection;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.UUIDUtil;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.FormattedText;

/** Sequential actual-client qualification; Fabric input/focus is synthetic, not physical SDL evidence. */
public final class ClientControlGameTest implements FabricClientGameTest {
    private static final int RECORD = InputConstants.KEY_F8;
    private static final int TALK = InputConstants.KEY_NUMPADENTER;
    private static final int STOP = InputConstants.KEY_F9;
    private static final UUID EXPECTED_PLAYER = UUID.fromString("23b3ecc2-026f-3a15-a197-ac0e44cdc79f");
    private ProtocolFixture fixture;
    private ClientGameTestContext context;
    private TestInput input;

    private static final class FixtureMenu extends Screen {
        FixtureMenu() { super(Component.literal("Synthetic client control fixture")); }
    }

    @Override public void runTest(ClientGameTestContext context) {
        this.context = context;
        input = context.getInput();
        VoiceClientAccess production = context.computeOnClient(ignored -> FixtureObservation.client());
        Profile profile = production.lychdFixtureProfile();
        FixtureObservation.check(UUIDUtil.createOfflinePlayerUUID("LychdProbe").equals(EXPECTED_PLAYER)
                && profile.playerId.equals(EXPECTED_PLAYER.toString()), "exact offline synthetic identity");
        context.runOnClient(ignored -> {
            KeyMapping record = KeyMapping.get("key.lychd_voice.record");
            KeyMapping talk = KeyMapping.get("key.lychd_voice.talk");
            KeyMapping stop = KeyMapping.get("key.lychd_voice.stop");
            FixtureObservation.check(record != null && stop != null && record.isUnbound() && stop.isUnbound(),
                    "actual production mappings start unbound");
            FixtureObservation.check(talk != null && talk.isUnbound(), "actual third mapping starts unbound");
            talk.setKey(InputConstants.Type.KEYBOARD.getOrCreate(TALK));
            record.setKey(InputConstants.Type.KEYBOARD.getOrCreate(RECORD));
            stop.setKey(InputConstants.Type.KEYBOARD.getOrCreate(STOP));
            KeyMapping.resetMapping();
        });
        try { fixture = new ProtocolFixture(profile); }
        catch (IOException exception) { throw new IllegalStateException("Client control fixture could not bind local endpoint"); }
        FixtureObservation.fixture = fixture;
        Properties properties = new Properties();
        properties.setProperty("server-ip", "127.0.0.1");
        properties.setProperty("server-port", "25573");
        properties.setProperty("online-mode", "false");
        properties.setProperty("level-type", "minecraft:flat");
        properties.setProperty("view-distance", "2");
        properties.setProperty("simulation-distance", "2");
        try (var server = context.worldBuilder().createServer(properties)) {
            TestDedicatedServerConnection connection = server.connect();
            boolean disconnected = false;
            try {
                context.waitFor(minecraft -> minecraft.level != null && minecraft.player != null
                        && minecraft.getCurrentServer() != null && minecraft.isWindowActive()
                        && minecraft.gui.screen() == null && minecraft.gui.overlay() == null, 400);
                context.runOnClient(minecraft -> FixtureObservation.check(
                        minecraft.player.getUUID().equals(EXPECTED_PLAYER)
                        && minecraft.getCurrentServer().ip.equals("localhost:25573"), "actual matched world and player"));
                released();
                // Let vanilla's initial join/tutorial toasts retire before judging settled HUD readability.
                holdFor(10000);
                eligible();

                input.holdKey(RECORD);
                await(() -> fixture.records() == 1, 4000, "first actual record ingress");
                settledRecord(1);
                for (String language : List.of("en_us", "sk_sk", "cs_cz")) {
                    context.runOnClient(minecraft -> minecraft.options.languageCode = language);
                    ownHud(1);
                    context.takeScreenshot("lychd-readable-" + language);
                }
                context.runOnClient(minecraft -> minecraft.options.languageCode = "en_us");
                ownHud(1, false);
                input.pressKey(InputConstants.KEY_F1);
                context.waitTicks(3);
                int hiddenAt = FixtureObservation.renderedPanels();
                int hiddenExtractions = FixtureObservation.extractions();
                holdFor(350);
                FixtureObservation.check(FixtureObservation.renderedPanels() == hiddenAt
                        && FixtureObservation.extractions() > hiddenExtractions, "vanilla hide-HUD hides own panel during GUI extraction");
                FixtureObservation.hiddenHudChecked = true;
                input.pressKey(InputConstants.KEY_F1);
                ownHud(1, false);
                heldAcrossPolls(1);

                // Both menu boundaries are actual Screen transitions while the record key stays down.
                context.setScreen(FixtureMenu::new);
                context.waitTicks(3);
                int menuAt = FixtureObservation.renderedPanels();
                int menuExtractions = FixtureObservation.extractions();
                holdFor(350);
                FixtureObservation.check(FixtureObservation.renderedPanels() == menuAt
                        && FixtureObservation.extractions() > menuExtractions, "menu hides own panel during GUI extraction");
                FixtureObservation.menuHudChecked = true;
                counts(1, 0);
                context.setScreen(() -> null);
                context.waitTicks(3);
                heldAcrossPolls(1);
                released();
                eligible();
                input.holdKey(RECORD);
                await(() -> fixture.records() == 2, 4000, "fresh record after menu release");
                settledRecord(2);
                ownHud(2);
                context.takeScreenshot("lychd-unknown-playback");

                fixture.changeContext();
                await(() -> {
                    Protocol.State state = FixtureObservation.state();
                    return state != null && state.generation() == 2 && state.contextId().equals(ProtocolFixture.CONTEXT_TWO);
                }, 4000, "actual production observation of new host context");
                context.waitTicks(3);
                heldAcrossPolls(2);
                released();
                eligible();
                input.holdKey(RECORD);
                await(() -> fixture.records() == 3, 4000, "fresh record in new generation");
                settledRecord(3);
                ownHud(3);
                context.takeScreenshot("lychd-hearing-unconfirmed");
                released();

                context.runOnClient(ignored -> {
                    KeyMapping.get("key.lychd_voice.stop").setKey(InputConstants.Type.KEYBOARD.getOrCreate(RECORD));
                    KeyMapping.resetMapping();
                });
                context.waitTicks(2);
                input.holdKey(RECORD);
                await(() -> fixture.stops() == 1, 4000, "same binding selects stop");
                holdFor(300);
                counts(3, 1);
                released();
                stopAcknowledged(1);
                context.runOnClient(ignored -> {
                    KeyMapping.get("key.lychd_voice.stop").setKey(InputConstants.Type.KEYBOARD.getOrCreate(STOP));
                    KeyMapping.resetMapping();
                });

                context.setScreen(FixtureMenu::new);
                released();
                input.holdKey(STOP);
                await(() -> fixture.stops() == 2, 4000, "safe nontext stop in actual menu");
                holdFor(300);
                counts(3, 2);
                released();
                stopAcknowledged(2);
                context.setScreen(() -> null);
                released();
                eligible();

                // Block one real ordinary HTTP exchange, then exercise the reserved production stop lane.
                fixture.blockNextRecord();
                input.holdKey(RECORD);
                await(() -> fixture.gate() != null, 4000, "ordinary HTTP entered fixture gate");
                ProtocolFixture.Gate gate = fixture.gate();
                try {
                    input.holdKey(STOP);
                    await(() -> fixture.stops() == 3, 1200, "reserved stop ingress before ordinary response");
                    FixtureObservation.check(gate.stopBeforeRelease && gate.releasedAt == 0,
                            "reserved stop reached while ordinary exchange remained held");
                } finally { gate.release(); }
                released();
                stopAcknowledged(3);
                settledRecord(4);
                counts(4, 3);
                eligible();

                // A real disconnect retires an outstanding own record through the untouched tick path.
                fixture.pendingNextRecord();
                input.holdKey(RECORD);
                await(() -> fixture.records() == 5, 4000, "outstanding record before disconnect");
                context.waitTicks(2);
                input.releaseKey(RECORD);
                connection.close();
                disconnected = true;
                await(() -> fixture.stops() == 4, 4000, "best effort stop after actual world disconnect");
                holdFor(700);
                counts(5, 4);
                context.runOnClient(minecraft -> FixtureObservation.check(minecraft.level == null && minecraft.player == null,
                        "actual world retired"));
                FixtureObservation.check(fixture.healthy(), "closed local protocol validation");
                FixtureObservation.fixedScenariosPassed = true;
                // Preserve the complete original five-record/four-stop chain before exercising held input.
                TestDedicatedServerConnection heldConnection = server.connect();
                try {
                    context.waitFor(minecraft -> minecraft.level != null && minecraft.player != null
                            && minecraft.getCurrentServer() != null && minecraft.isWindowActive()
                            && minecraft.gui.screen() == null && minecraft.gui.overlay() == null, 400);
                    heldScenarios();
                } finally {
                    input.releaseKey(TALK); heldConnection.close();
                }
                FixtureObservation.scenariosPassed = true;
            } finally {
                ProtocolFixture.Gate gate = fixture.gate();
                if (gate != null) gate.release();
                input.releaseKey(RECORD);
                input.releaseKey(STOP);
                input.releaseKey(TALK);
                if (!disconnected) connection.close();
            }
        }
        // Framework completion is separate from the later actual CLIENT_STOPPING receipt.
    }

    private void heldScenarios() {
        released(); eligible();
        input.holdKey(TALK);
        await(() -> fixture.holds() == 1, 4000, "Num Enter held start through third production mapping");
        ownHeldHud(1, "hold_requested", "recording");
        int stateReads = fixture.stateReads();
        holdFor(1150);
        await(() -> fixture.stateReads() > stateReads, 2000, "held Num Enter across state polling");
        FixtureObservation.check(fixture.holds() == 1 && fixture.releases() == 0,
                "holding Num Enter neither replays nor submits");
        counts(5, 4);
        input.releaseKey(TALK);
        await(() -> fixture.releases() == 1, 4000, "physical Num Enter release finishes original hold");
        await(() -> fixture.holdResult(1).settled() && FixtureObservation.state().lastRecord() != null
                && FixtureObservation.state().lastRecord().requestId().equals(fixture.holdId(1))
                && FixtureObservation.state().lastRecord().settled(), 4000, "released own hold settled through state");
        ownHeldHud(1, "known", null);
        context.takeScreenshot("lychd-held-num-enter");
        released(); eligible();
        input.holdKey(TALK);
        await(() -> fixture.holds() == 2, 4000, "fresh second Num Enter hold");
        context.setScreen(FixtureMenu::new);
        await(() -> fixture.stops() == 5 && fixture.heldStops() == 1, 4000, "menu boundary independently cancels held capture");
        FixtureObservation.check(fixture.releases() == 1, "menu entry did not submit a release");
        context.setScreen(() -> null);
        holdFor(700);
        FixtureObservation.check(fixture.holds() == 2 && fixture.releases() == 1,
                "held Num Enter after menu return does not replay or submit");
        released(); stopAcknowledged(5);
        FixtureObservation.check(fixture.records() == 5 && fixture.stops() == 5 && fixture.holds() == 2
                && fixture.releases() == 1 && fixture.heldStops() == 1, "held scenarios retain original fixed counts");
        FixtureObservation.heldScenariosPassed = true;
    }
    private void ownHeldHud(int index, String stage, String phase) {
        int after = FixtureObservation.renderedPanels();
        List<String> expected = context.computeOnClient(minecraft -> {
            var hud = new VoiceController.Hud(fixture.holdId(index), "record", stage, phase, fixture.holdResult(index));
            int width = Math.min(480, minecraft.getWindow().getGuiScaledWidth() - 16);
            return HudText.paragraphs(hud, minecraft.options.languageCode).stream()
                    .flatMap(text -> minecraft.font.splitIgnoringLanguage(Component.literal(text), width).stream())
                    .map(FormattedText::getString).toList();
        });
        await(() -> FixtureObservation.renderedPanels() > after && FixtureObservation.sawPanel(expected), 4000,
                "fresh passive correlated held status panel");
        FixtureObservation.check(FixtureObservation.geometryHealthy(), "held status rows fit actual geometry");
    }
    private void released() {
        input.releaseKey(RECORD);
        input.releaseKey(STOP);
        input.releaseKey(TALK);
        context.waitTicks(3);
    }
    private void eligible() {
        await(() -> {
            Protocol.State state = FixtureObservation.state();
            long now = System.currentTimeMillis();
            return state != null && state.canRecord() && !state.stopping() && !state.audioBlocked()
                    && FixtureObservation.stateAt() >= 0 && now - FixtureObservation.stateAt() <= 1500;
        }, 4000, "fresh eligible real production state");
        context.waitTicks(2);
    }
    private void settledRecord(int index) {
        await(() -> {
            Protocol.State state = FixtureObservation.state();
            return state != null && state.lastRecord() != null && state.lastRecord().settled()
                    && state.lastRecord().requestId().equals(fixture.recordId(index));
        }, 4000, "own settled record observed through production state polling");
    }
    private void stopAcknowledged(int index) {
        await(() -> {
            Protocol.State state = FixtureObservation.state();
            return state != null && state.lastStop() != null && state.lastStop().status().equals("known")
                    && state.lastStop().requestId().equals(fixture.stopId(index));
        }, 4000, "own stop observed through production state polling");
        context.waitTicks(2);
    }
    private void ownHud(int index) {
        ownHud(index, true);
    }
    private void ownHud(int index, boolean count) {
        int after = FixtureObservation.renderedPanels();
        List<String> expected = context.computeOnClient(minecraft -> {
            var hud = new VoiceController.Hud(fixture.recordId(index), "record", "known", null, fixture.recordResult(index));
            int width = Math.min(480, minecraft.getWindow().getGuiScaledWidth() - 16);
            var lines = HudText.paragraphs(hud, minecraft.options.languageCode).stream()
                    .flatMap(text -> minecraft.font.splitIgnoringLanguage(Component.literal(text), width).stream())
                    .map(FormattedText::getString).toList();
            FixtureObservation.check(lines.size() * (minecraft.font.lineHeight + 1)
                    <= minecraft.getWindow().getGuiScaledHeight() - 16, "complete semantic content fits actual scaled height");
            FixtureObservation.check(minecraft.font.width(HudText.render(hud, minecraft.options.languageCode)) > width,
                    "unwrapped actionbar counterfactual exceeds actual font width");
            return lines;
        });
        await(() -> FixtureObservation.renderedPanels() > after && FixtureObservation.sawPanel(expected), 4000,
                "fresh passive actual complete own correlated panel");
        FixtureObservation.check(FixtureObservation.geometryHealthy(), "all submitted HUD rows fit actual geometry");
        if (count) FixtureObservation.readableCases++;
    }
    private void heldAcrossPolls(int expectedRecords) {
        int before = fixture.stateReads();
        holdFor(1150);
        await(() -> fixture.stateReads() > before, 2000, "held key across real state polling");
        eligible();
        FixtureObservation.check(fixture.records() == expectedRecords, "held record did not replay while host remained eligible");
    }
    private void counts(int records, int stops) {
        FixtureObservation.check(fixture.records() == records && fixture.stops() == stops, "finite expected ingress counts");
    }
    private void holdFor(long milliseconds) {
        long until = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(milliseconds);
        for (int ticks = 0; System.nanoTime() < until; ticks++) {
            FixtureObservation.check(ticks < 2000, "bounded held observation ticks");
            context.waitTick();
            healthy();
        }
    }
    private void await(BooleanSupplier condition, long milliseconds, String label) {
        long until = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(milliseconds);
        for (int ticks = 0; ticks < 2000; ticks++) {
            healthy();
            if (context.computeOnClient(ignored -> condition.getAsBoolean())) return;
            FixtureObservation.check(System.nanoTime() < until, label);
            context.waitTick();
        }
        throw new AssertionError("Client control fixture: bounded predicate ticks");
    }
    private void healthy() { FixtureObservation.check(fixture.healthy(), "local protocol fixture health"); }
}
