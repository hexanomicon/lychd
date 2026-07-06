---
title: The First Breath
icon: material/weather-windy
---

# :material-weather-windy: Stage 5 — The First Breath

Everything is in place: the grounds are clear, the tool is installed, the Codex is
inscribed, and a Soulstone is bound. This stage wakes the daemon and exchanges the first
message.

## Start the daemon

Summon the Vessel through the user's systemd session:

```bash
systemctl --user start lychd
```

The Sepulcher starts the required services in order — the Phylactery (Postgres) first, then
the Vessel (the web application). Watch the daemon's internal monologue while it comes up:

```bash
journalctl --user -fu lychd
```

!!! tip "Foreground alternative for development"
    From a source checkout you can run the Vessel in the foreground instead:

    ```bash
    uv run lychd run
    ```

    This is convenient while developing; the summoned systemd service is the real daemon.

## Open the Altar

The [Altar](../divination/altar/index.md) is the web surface for communing with the Lich.
Open it in a browser:

```
http://localhost:7134
```

## Watch the Nexus warm

Open the [Nexus](../divination/altar/nexus.md) — the capability board. When you first
arrive, your model's `chat` capability will show as **awaited** (a `DYNAMIC` model that is
reachable but not yet loaded) or **cold**. This is honest: nothing is loaded until
something asks for it.

## Exchange the first message

Open the [Bridge](../divination/altar/index.md) — the chat instrument — and send a message.

Behind the scenes: your Intent resolves to the `chat` capability; the Dispatcher sees the
model is not yet warm and drives its activation; the Nexus moves the capability
**awaited → warming → active**; and the first tokens stream back to you on the Bridge.

!!! success "The summoning is complete"
    A local model just answered you from your own iron. The daemon is alive.

## Where to go next

The [Praxis](../praxis/index.md) is the manual for daily use:

- [Open a Portal](../praxis/rites/open-a-portal.md) to add a remote provider alongside your
  local models.
- [Manage covens](../praxis/rites/manage-covens.md) to understand and drive model swaps.
- [Exorcism](../praxis/exorcism.md) when something misbehaves.
