package org.lychd.voice;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;

/** Called only by the passive production-init TAIL observer, after its stop hook was registered. */
final class FixtureLifecycle {
    private FixtureLifecycle() { }
    static void observeProductionStopping() {
        ClientLifecycleEvents.CLIENT_STOPPING.register(FixtureObservation::stopping);
    }
}
