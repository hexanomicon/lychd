---
title: Voxel and block export
icon: material/cube-outline
---

# :material-cube-outline: Voxel and block export

A spatial asset can become a bounded grid, a game-qualified block palette, and a portable
schematic. This Form workflow owns that conversion and its read-back evidence. Its return is an
artifact that [Foundry](../../../compositions/foundry/assets.md) or
[Blockworld](../../../compositions/blockworld/mission.md) may separately admit.

The passage is Designed. It shares [Form's](form.md) source custody, typed facets, exact execution
attempt, and technical settlement, and the [Vision Covenant](../../../adr/36-vision.md) owns its
law. Selecting an exporter grants no authority to place blocks in a live world.

## Voxels and the 32-cubed proving fixture

Form distinguishes three voxel routes rather than calling each a Minecraft generator:

1. **Deterministic conversion:** normalize an admitted mesh or volume, choose `solid`, `shell`, or
   `surface` occupancy, sample exactly 32 by 32 by 32 cells, apply an optional palette and interior
   rule, validate, and export.
2. **Block-native generation:** an eligible future model produces or inpaints a bounded semantic
   block region. The result maps through the same canonical palette and validation; it does not
   masquerade as a voxelized mesh.
3. **Procedural composition:** a Mind may propose an inert `ProceduralFormRecipe@1` using admitted
   shapes, transforms, repetition, booleans, symmetry, palette entries, and bounds. A separate
   contained interpreter effect validates and renders it. Arbitrary Python, shell, Blender scripts,
   or Minecraft commands are not this contract.

`VoxelGrid@1` pins dimensions, axes, origin, cell scale, occupancy or density channels, optional
colors, source axis-aligned bounding-box (AABB) fit and padding, cell-center or cell-volume sampling, boundary and tie rules,
axis-to-index mapping, and source transform. The canonical `BlockGrid@1` pins dimensions, origin,
axes, units, exact game registry edition and version plus registry digest, palette revision and
ordering, exact block identifiers and state properties, air and unknown policy, source relation,
and digest. It remains independent of one game-file encoding.

The derived Minecraft projection pins Java edition and version, `DataVersion`, palette mapping,
offset, unsupported-block policy, block-entity and entity policy, metadata and timestamp policy,
and encoder revision. Its first profile permits full cubes only; stairs, slabs, fences, fluids,
redstone, and stateful blocks require later explicit topology and behavior profiles. Unknown or
unsupported states fail closed unless the profile names and records an exact substitution.

The export candidate is
[Sponge Schematic v3](https://github.com/SpongePowered/Schematic-Specification/blob/master/versions/schematic-3.md):
GZip-compressed NBT with an outer `Schematic` compound, `Version = 3`, required `DataVersion`,
unsigned-short interpretation of `Width`, `Height`, and `Length`, `Blocks.Palette`, and varint
`Blocks.Data` indexed as `x + z*Width + y*Width*Length`. Read-back normalization proves dimensions,
palette, offsets, states, block data, and metadata against the canonical grid.

The package contains the source grid, canonical block grid, `.schem`, preview GLB and PNG, block
counts, palette statistics, clipping and unsupported-material findings, plus an export-and-read-back
receipt. Thirty-two cubed is only 32,768 cells, so this first golden fixture favors simple,
inspectable data structures over a large-volume framework. It is one proving profile, never a
universal product limit.

A `.schem` admitted to [Foundry](../../../compositions/foundry/assets.md) is a project asset. The
same exact blueprint admitted to a [Blockworld mission](../../../compositions/blockworld/mission.md)
still grants no live placement authority: Sentinel must validate every bounded world effect
against world epoch, plot lease, inventory, and mission policy.
