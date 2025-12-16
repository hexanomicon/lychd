# 📐 Blueprint: The Runes (Quadlet Specs)

> _"Many spirits may inhabit the Crypt, but only one may animate the Body at a time."_

This document defines the **Jinja2** templating strategy. It uses a **Cartridge Architecture** for the Soulstones, allowing multiple inference engines to be defined (`~/.config/containers/systemd/`) but enforcing mutual exclusivity at runtime.

## ⚗️ The Transmutation (Mapping)

| Template Source | Rune Type       | Runtime Output                 | Logic                                    |
| :-------------- | :-------------- | :----------------------------- | :--------------------------------------- |
| `soulstone.j2`  | **[Container]** | `soulstone-{engine}.container` | Generated **N** times (once per config). |
| `harvester.j2`  | **[Container]** | `harvester.container`          | Prometheus (Static Scrape Config).       |
| `scribe.j2`     | **[Container]** | `scribe.container`             | Grafana (Multi-Dashboard Provisioning).  |

## 🧬 The Soulstone Cartridges

The `soulstone.j2` template is reused to generate multiple unit files (e.g., `soulstone-vllm.container`, `soulstone-llama.container`).

### 1. Mutual Exclusion (`Conflicts`)

Every Soulstone unit must declare war on its siblings to prevent resource collision (GPU lock).

```ini
[Unit]
Description=LychD Animator: {{ engine_name|upper }}
# "If I live, all other soulstones must die."
Conflicts=soulstone-*.service
```

### 2. The Standard Interface (Ports)

To ensure the **Vessel** and **The Watchers** function without reconfiguration, all Soulstones must align to the **Sepulcher Standard**.

- **Internal API Port:** `8081` (The Vessel sends completion requests here).
- **Metrics Port:** `8081` (Prometheus scrapes here).
  - _Note:_ Most engines allow serving metrics on the same port as the API. If an engine requires a separate port, we must map it to a standard internal port (e.g., `9090`) using `podman run -p`.

## 🏗️ The Watchers (Robust Observability)

### The Harvester (Prometheus)

Because of the Standard Interface, Prometheus is dumb and happy. It does not need complex service discovery.

- **Config (`prometheus.yml`):**
  ```yaml
  scrape_configs:
    - job_name: "soulstone"
      static_configs:
        - targets: ["localhost:8081"] # Scrapes whoever is currently holding the port
  ```

### The Scribe (Grafana)

Grafana cannot easily morph its UI. Instead, we provision **all** possibilities.

- **Provisioning Logic:**
  The `lychd init` command copies a folder of JSON dashboards into the volume:
  - `dashboards/soulstone-vllm.json`
  - `dashboards/soulstone-sglang.json`
  - `dashboards/lychd-vessel.json`
- **User Experience:** The user logs into Grafana. If they launched `soulstone-vllm`, they open the vLLM dashboard. The SGLang dashboard will simply show "No Data".

## 🛠️ The Compilation Logic (`cli.py`)

The `init` command iterates through the user's desired configurations.

```python
# Pseudo-code for the "Compiler"
engines = ["vllm", "sglang"]

for engine in engines:
    # 1. Define the conflicts list (everyone but me)
    conflicts = [f"soulstone-{e}.service" for e in engines if e != engine]

    # 2. Render the Rune
    render_template(
        "soulstone.j2",
        output=f"soulstone-{engine}.container",
        context={
            "engine_name": engine,
            "port": 8081,
            "conflicts": " ".join(conflicts)
        }
    )
```
