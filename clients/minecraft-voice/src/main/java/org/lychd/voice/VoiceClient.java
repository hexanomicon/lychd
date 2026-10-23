package org.lychd.voice;

import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.hud.VanillaHudElements;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.FormattedText;
import net.minecraft.resources.Identifier;

/** Client-only entrypoint. There is no game-server transport, audio device or model in this artifact. */
public final class VoiceClient implements ClientModInitializer {
    private VoiceController controller;
    private VoiceWorkers workers;
    private Profile profile;
    private KeyMapping record, talk, stop;

    @Override public void onInitializeClient() {
        Minecraft client = Minecraft.getInstance();
        try { profile = Profile.read(client.gameDirectory.toPath().resolve("config").resolve("lychd-voice.json")); }
        catch (java.io.IOException | RuntimeException exception) {
            // Values, file paths, bearer credentials and foreign diagnostics never enter a log or chat.
            throw new IllegalStateException("Invalid private LychD voice configuration");
        }
        if (profile == null) return;
        KeyMapping.Category category = KeyMapping.Category.register(Identifier.fromNamespaceAndPath("lychd_voice", "controls"));
        record = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.lychd_voice.record", InputConstants.UNKNOWN.getValue(), category));
        talk = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.lychd_voice.talk", InputConstants.UNKNOWN.getValue(), category));
        stop = KeyMappingHelper.registerKeyMapping(new KeyMapping("key.lychd_voice.stop", InputConstants.UNKNOWN.getValue(), category));
        LoopbackTransport transport = new LoopbackTransport(profile);
        workers = new VoiceWorkers(transport);
        controller = new VoiceController(transport, workers.ordinary(), workers.finish(), workers.stop());
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
        HudElementRegistry.attachElementAfter(VanillaHudElements.OVERLAY_MESSAGE,
                Identifier.fromNamespaceAndPath("lychd_voice", "status"), this::renderHud);
        ClientLifecycleEvents.CLIENT_STOPPING.register(ignored -> {
            controller.beginClose(); workers.close();
        });
    }

    private void tick(Minecraft client) {
        boolean matched = client.level != null && client.player != null && client.getCurrentServer() != null
                && profile.playerId.equals(client.player.getUUID().toString())
                && profile.serverAddress.equals(client.getCurrentServer().ip);
        boolean menuFree = client.gui.screen() == null && client.gui.overlay() == null;
        InputConstants.Key recordKey = KeyMappingHelper.getBoundKeyOf(record);
        InputConstants.Key talkKey = KeyMappingHelper.getBoundKeyOf(talk);
        InputConstants.Key stopKey = KeyMappingHelper.getBoundKeyOf(stop);
        boolean recordDown = physicalDown(record, recordKey, menuFree);
        boolean holdDown = physicalDown(talk, talkKey, menuFree);
        boolean stopDown = physicalDown(stop, stopKey, menuFree);
        boolean menuStopSafe = stopKey.getType() == InputConstants.Type.KEYBOARD && nonTextKey(stopKey.getValue());
        controller.tick(new EdgeGuard.Input(client.level, matched, client.isWindowActive(), menuFree,
                client.isPaused(), recordDown, holdDown, stopDown, menuStopSafe,
                !stop.isUnbound() && record.same(stop), !stop.isUnbound() && talk.same(stop)));
    }

    private void renderHud(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker) {
        Minecraft client = Minecraft.getInstance();
        if (client.level == null || client.player == null || client.getCurrentServer() == null
                || !profile.playerId.equals(client.player.getUUID().toString())
                || !profile.serverAddress.equals(client.getCurrentServer().ip) || !client.isWindowActive()
                || client.gui.screen() != null || client.gui.overlay() != null) return;
        VoiceController.Hud hud = controller.hud();
        if (hud == null) return;
        int width = Math.min(480, graphics.guiWidth() - 16);
        int lineHeight = client.font.lineHeight + 1;
        int maximumLines = (graphics.guiHeight() - 16) / lineHeight;
        if (width <= 0 || maximumLines <= 0) return;
        var lines = HudText.panel(hud, client.options.languageCode,
                paragraph -> client.font.splitIgnoringLanguage(Component.literal(paragraph), width).stream()
                        .map(FormattedText::getString).toList(), maximumLines);
        if (lines.isEmpty()) return;
        int drawnWidth = lines.stream().mapToInt(client.font::width).max().orElse(0);
        graphics.fill(4, 4, drawnWidth + 12, lines.size() * lineHeight + 12, 0xC0000000);
        for (int index = 0; index < lines.size(); index++) {
            graphics.text(client.font, lines.get(index), 8, 8 + index * lineHeight, 0xFFFFFFFF, true);
        }
    }

    private static boolean physicalDown(KeyMapping mapping, InputConstants.Key key, boolean menuFree) {
        if (mapping.isUnbound()) return false;
        if (key.getType() == InputConstants.Type.KEYBOARD) return InputConstants.isKeyDown(key.getValue());
        return menuFree && mapping.isDown();
    }
    private static boolean nonTextKey(int key) {
        return key >= InputConstants.KEY_F1 && key <= InputConstants.KEY_F24
                || key == InputConstants.KEY_PAUSE || key == InputConstants.KEY_PRINTSCREEN
                || key == InputConstants.KEY_SCROLLLOCK;
    }
}
