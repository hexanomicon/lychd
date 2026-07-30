# Operator Profiles

Profiles are copyable Codex fragments for common hardware shapes—not exact
product requirements or a host receipt.

The folder names describe capacity classes, not exact product requirements:

- `nvidia-24gb/`: one 24 GB NVIDIA card, such as RTX 3090, RTX 4090, A5000.
- `nvidia-2x24gb/`: two 24 GB NVIDIA cards, commonly dual RTX 3090.

Keep model paths, ports, and mounts local to the machine. Each profile gives a
runtime pattern and the fields to edit; bind/start still require the normal
LychD flow.
