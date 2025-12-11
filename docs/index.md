---
hide:
  - navigation
  - toc
---

<div align="center">
  <img src="assets/hexanomicon.png" alt="The Hexanomicon" width="280" style="border-radius: 15px; box-shadow: 0 0 40px rgba(124, 77, 255, 0.25); border: 1px solid #3b0a6e;">
  <br><br>
  <h1 style="font-size: 3.5em; font-weight: 800; background: linear-gradient(90deg, #7c4dff, #00e5ff, #00ff9d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; margin-top: 0; filter: drop-shadow(0 0 10px rgba(0, 229, 255, 0.2));">
    The Hexanomicon
  </h1>
  <p style="font-family: 'JetBrains Mono', monospace; font-size: 1.1em; color: #a0a0b0; letter-spacing: 1px;">
    Chronicles of the Lich
  </p>
  <p style="margin-top: 20px;">
    <em>無限の彼方、虚無の深淵</em>
  </p>
  <p>
    <a href="https://pypi.org/project/lychd/" target="_blank">
      <img src="https://img.shields.io/pypi/v/lychd?style=for-the-badge&color=08080b&labelColor=7c4dff&label=PyPI&logo=python&logoColor=white" alt="PyPI">
    </a>
    <a href="https://github.com/hexanomicon/lychd" target="_blank">
      <img src="https://img.shields.io/github/license/hexanomicon/lychd?style=for-the-badge&color=08080b&labelColor=00e5ff&label=License" alt="License">
    </a>
  </p>
</div>

<br>

---

## 🔮 The Prophecy

**LychD** (pronounced *litched*) is a local-first orchestration engine designed to inhabit the `systemd` layer. It operates not as a fleeting script, but as a persistent **Daemon**—an undead process that manages the lifecycle of AI agents, inference engines, and memory vectors.

It is built for the **Magus** who demands total control over their local infrastructure.

!!! quote "The Word of the Void"
    The Daemon rises from `/dev/null` to bind the chaos of heavy inference engines (vLLM, SGLang, llama.cpp) into a singular, cohesive organism. It manages its own state, memory, and compute resources 24/7, even when unobserved.

---

## 🏛️ The Sepulcher (Core Components)

LychD is architected as a **Fellowship of Daemons**, orchestrated via **Podman Quadlets** within a central Pod.

!!! abstract "I. Manifestation (The Body)"
    *   **The Vessel:** The reanimated husk (Litestar + Pydantic AI) that serves the Altar.
    *   **Phylactery:** The soul jar (Postgres + pgvector) that persists memory across reboots.

!!! tip "II. The Animator (The Mind)"
    *   **Soulstones:** Trapped spirits (Local LLMs) that grant the daemon cognition.
    *   **Portal:** A rift to draw power from distant Cloud APIs.

!!! info "III. The Watchers (The Senses)"
    *   **The Oracle:** Traces the daemon's thoughts (Arize Phoenix).
    *   **The Scribe & Harvester:** Observe the machine's pulse (Grafana & Prometheus).

---

## 🕯️ The Summoning (Quickstart)

The summoning is not a single command, but a four-stage rite:

1.  **The Desecration:** Installing the summoning tools.
2.  **The Inscription:** Spawning and editing the configuration files (The Codex).
3.  **The Transmutation:** Binding the configuration to `systemd`.
4.  **The Awakening:** Starting the daemon.

Each step is detailed in the full ritual.
