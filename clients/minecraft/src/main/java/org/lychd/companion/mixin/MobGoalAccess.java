package org.lychd.companion.mixin;

import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Mob exposes getGoalSelector(), but 26.3 has no public targetSelector accessor. */
@Mixin(Mob.class)
public interface MobGoalAccess {
    @Accessor("targetSelector") GoalSelector lychdTargetSelector();
}
