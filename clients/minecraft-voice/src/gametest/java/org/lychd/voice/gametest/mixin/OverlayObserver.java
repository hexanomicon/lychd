package org.lychd.voice.gametest.mixin;

import org.lychd.voice.FixtureObservation;

import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Passive observation of submitted text and its actual scaled-font bounds, never a renderer substitute. */
@Mixin(GuiGraphicsExtractor.class)
public abstract class OverlayObserver {
    @Inject(method = "<init>", at = @At("TAIL"))
    private void lychdFixtureObservedExtraction(CallbackInfo callback) {
        FixtureObservation.guiExtraction();
    }
    @Inject(method = "text(Lnet/minecraft/client/gui/Font;Ljava/lang/String;IIIZ)V", at = @At("TAIL"))
    private void lychdFixtureObservedText(Font font, String text, int x, int y, int color, boolean shadow, CallbackInfo callback) {
        GuiGraphicsExtractor graphics = (GuiGraphicsExtractor) (Object) this;
        FixtureObservation.drawn(text, x, y, font.width(text), font.lineHeight + 1,
                graphics.guiWidth(), graphics.guiHeight());
    }
}
