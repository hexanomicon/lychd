package org.lychd.voice.gametest.mixin;

import org.lychd.voice.FixtureObservation;
import org.lychd.voice.VoiceClient;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = VoiceClient.class, remap = false)
public abstract class VoiceClientInitObserver {
    @Inject(method = "onInitializeClient", at = @At("TAIL"))
    private void lychdFixtureObservedInit(CallbackInfo callback) {
        FixtureObservation.initialized((VoiceClient) (Object) this);
    }
}
