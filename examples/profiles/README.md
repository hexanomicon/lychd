# Operator Profiles

The directories describe hardware capacity classes:

- [NVIDIA 24 GB](nvidia-24gb/README.md): one 24 GB card, such as an RTX 3090, RTX 4090, or A5000.
- [NVIDIA 2×24 GB](nvidia-2x24gb/README.md): two 24 GB cards, commonly a dual-RTX-3090 workstation.

Use these profiles to compare runtime shapes, then adapt their older fragments through the
[current Rune contract](../../docs/sepulcher/animator/soulstone/rune.md). Declare the exact model
shelf, mounts, devices, image, ports, and launch arguments for your machine. Model size, context,
and concurrency must fit the memory left after the driver, desktop, and runtime overhead; a
folder name cannot establish that fit.

[Summoning](../../docs/summoning.md) owns the bind/start sequence and observations needed for one
local host receipt.
