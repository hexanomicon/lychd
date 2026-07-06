---
title: Exorcism
icon: material/ghost-off
---

# :material-ghost-off: Exorcism — troubleshooting

When the daemon misbehaves, work symptom → cause → cure. This guide is seeded with the
faults you can hit through the [Summoning](../summoning/index.md) and the Wave-3 rites; it
grows as the daemon does.

## Diagnostic incantations

Keep these at hand:

```bash
lychd animators                                  # declared animators + live capability phase
journalctl --user -fu lychd                       # the Vessel's log stream
systemctl --user status lychd-vessel.service      # a specific unit's state
curl -s http://localhost:7134/orchestrator/queues | jq   # queues + live leases
```

## The `lychd` command is not found

| | |
| :--- | :--- |
| **Symptom** | `lychd: command not found` after installing. |
| **Cause** | The tool's install directory is not on your `PATH`. |
| **Cure** | With `uv tool install`, ensure `~/.local/bin` is on `PATH` (`uv tool update-shell`). From a source checkout, run it as `uv run lychd`. |

## A unit won't start

| | |
| :--- | :--- |
| **Symptom** | `systemctl --user start lychd` fails, or a Soulstone service stays `failed`. |
| **Cause** | Bad image reference, a port collision, or a missing device/volume in the rune. |
| **Cure** | Read the unit's log: `journalctl --user -u <service> -e`. A port collision is caught at `lychd bind` with both claimants named — fix the conflicting `port` and re-bind. Confirm the image pulls: `podman pull <image>`. |

## A capability never warms

| | |
| :--- | :--- |
| **Symptom** | The [Nexus](../divination/altar/nexus.md) shows a capability stuck at **cold** or **awaited**; runs park and never resume. |
| **Cause** | The model server is not actually up, the model path is wrong, or a hard swap was declined for low priority. |
| **Cure** | Run `lychd animators` — an empty **Warm** column means the endpoint is not serving yet; check the unit is running and the `port`/`base_url` is correct. If a swap was **declined** (a 409 from `/orchestrator/activate`), raise the request priority or lower `min_priority_for_hard_swap` (see the [Orchestration reference](runes/orchestration.md)). |

## A swap times out

| | |
| :--- | :--- |
| **Symptom** | A transition fails with "Lease drain timed out". |
| **Cause** | A run held a lease on the animator being evicted longer than `drain_timeout_s`. |
| **Cure** | Inspect live leases: `curl .../orchestrator/queues \| jq '.leases'`. Let the holding run finish, or raise `drain_timeout_s` in `[orchestration.switching]`. Leased animators are protected by design — the swap waits rather than lobotomizing live work. |

## A Portal never appears

| | |
| :--- | :--- |
| **Symptom** | After binding a [Portal](rites/open-a-portal.md), its capability is absent from `lychd animators`. |
| **Cause** | The Portal declares zero `[[models]]` (a Portal with no models yields no capabilities), or the rune failed to load. |
| **Cure** | Add at least one `[[models]]` block (see the [Portal reference](runes/portals.md)). Confirm the rune parsed — `lychd bind` reports a named error on an invalid rune, so a rune that fails validation is never registered. |

## Postgres is unreachable

| | |
| :--- | :--- |
| **Symptom** | The Vessel fails to start with a database connection error. |
| **Cause** | The [Phylactery](../sepulcher/phylactery/index.md) (Postgres) is down, unreachable, or missing `pgvector`. |
| **Cure** | Confirm the server: `psql "$DATABASE_URL" -c '\dx'` and that `vector` is listed. Enable it with `CREATE EXTENSION IF NOT EXISTS vector;`. Re-check the grounds ([Stage 1](../summoning/grounds.md)). |

## VRAM contention

| | |
| :--- | :--- |
| **Symptom** | Model loads fail with out-of-memory, or the system thrashes between covens. |
| **Cause** | Two covens are trying to occupy the same hardware, or a model is too large for the GPU. |
| **Cure** | Check `nvidia-smi` / `rocm-smi` for what is resident. Use `[concurrency]` in your Soulstone Runes to declare which runtimes are `dedicated` (swappable) and raise `min_priority_for_hard_swap` to reduce thrashing. See [Manage Covens](rites/manage-covens.md). |
