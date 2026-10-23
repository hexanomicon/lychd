package org.lychd.companion.gametest.mixin;

import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestInfo;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Per-test terminal callbacks; runBeforeTestEnd is only a scheduled tick. */
@Mixin(GameTestHelper.class)
public interface GameTestInfoAccess {
    @Accessor("testInfo") GameTestInfo lychdTestInfo();
}
