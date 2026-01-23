This is a critical correction. We are stripping away the "nested TOML" trick in favor of **Explicit Grouping**.

A **Soulstone** is now purely a high-level declaration of intent that maps directly to the **[ContainerRune](../../adr/08-containers.md)** schema. The exclusivity logic is governed by the `groups` field, which defines which **Covens** the Rune inhabits.

Here is the remastered **Soulstone** documentation, technically aligned with the Rune substrate.

---

### File 2: `animator/soulstone.md`

```markdown
---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Rune

> _"A Portal is a whisper from the void, but a Soulstone is a god trapped in a bottle. It lives on your iron. It burns your electricity. It obeys only you."_

A **Soulstone** is the configuration for a local, containerized inference engine. It is the architectural source for a **[Container Rune](../../adr/08-containers.md)**. When inscribed in the Codex, the system's "Hand" transmutes this TOML into a physical Podman Quadlet (Systemd Service).

## 💎 The Infrastructure Mapping

Every Soulstone in the Codex is a manifestation of the `ContainerRune` schema. The fields you define in the scroll dictate the physical form of the container:

| TOML Field | Rune Property | Purpose |
| :--- | :--- | :--- |
| `image` | `image` | The OCI image (e.g., vLLM, SGLang). |
| `groups` | `covens` | The mutually inclusive states this Rune belongs to. |
| `capabilities` | `capabilities` | The abstract functional tags (e.g., `ocr`, `vision`). |
| `exec` | `exec` | The joined shell command for the container entrypoint. |
| `port_expose` | `ExposePort` | Signals the Pod to publish the port to the host. |

## 🤝 Coven Management (The Group Rule)

To manage finite VRAM, Soulstones declare their membership in **Covens** using the `groups` field.

- **Inclusive Coexistence:** If two Soulstones share at least one common group (e.g., `groups = ["vision-state"]`), they belong to the same Coven. Systemd allows them to run simultaneously.
- **Exclusive Banishment:** If two Soulstones share **no** common groups, they are mutually exclusive. The system generates a `Conflicts=` directive between them.

### Example: A Vision Coven

```toml
# ~/.config/lychd/soulstones/vision_eye.toml
[eye]
description = "Reasoning and Vision engine."
image = "vllm/vllm-openai:latest"
groups = ["vision-ritual"] # Membership in the Vision Coven
capabilities = ["text-generation", "vision-analysis"]
port = 8780

# ~/.config/lychd/soulstones/vision_scribe.toml
[scribe]
description = "Specialized OCR tool."
image = "my-ocr-service:latest"
groups = ["vision-ritual"] # Shares the group; will NOT be killed by 'eye'
capabilities = ["ocr"]
port = 8781
```

## ⚔️ The Law of Exclusivity

The **[Orchestrator](../../adr/21-orchestrator.md)** uses these group definitions to manifest the machine's state.

1. **The Intent:** An Agent needs `vision`. The Orchestrator identifies the `vision-ritual` coven.
2. **The Cleansing:** Systemd automatically stops any active Runes that do not belong to `vision-ritual` (e.g., your heavy `deep-think` coven).
3. **The Manifestation:** All Runes tagged with `vision-ritual` are started in concert.

## 📜 Inscribing the Body

Soulstones favor engines that support the OpenAI API standard, allowing for seamless integration with the **[Dispatcher](../../adr/20-dispatcher.md)**.

### Supported Engines

- **vLLM / SGLang:** For high-throughput, continuous batching.
- **Llama.cpp:** For hybrid CPU/GPU offloading.
- **ExLlamaV2:** For maximum tokens-per-second on consumer silicon.

!!! warning "The Port Singularity"
    **Every Soulstone must listen on a unique host port.**
    Even if they are in different Covens and never run together, the host OS requires a "cool down" period for the TCP socket. Reusing a port across different Soulstones will cause state transitions to fail with `Address already in use`.

!!! tip "Self-Aware Connectivity"
    The system automatically calculates the `uri` for every Soulstone as `http://localhost:{port}/v1`. The Lich handles the internal networking within the Pod; you only define the capabilities and the groups.

```
