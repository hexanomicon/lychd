---
title: Runtime transitions
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Runtime transitions

A local capability may be declared yet unable to answer until its service starts or another model
releases the required iron. This guide follows the operator's request through inspection,
Orchestrator admission, readiness, and recovery. [Coven](coven.md) names compatible service groups;
the transition acts on exact capabilities and their compiled conflict neighborhood.

Use the [Nexus](../../divination/altar/nexus.md) for the Altar projection or the bounded HTTP
operations below. The source and receipt limits remain in
[State of Work](../../state-of-the-work.md#safe-runtime-transitions).

## What the Nexus Shows

The [Nexus](../../divination/altar/nexus.md) presents capability readiness to the operator.
[Capabilities](capabilities.md#readiness-is-not-compatibility) defines the six underlying phases;
a displayed label is an observation, not a lease or permission to perform a transition.

## The Transition Contract

The [Orchestrator](../../adr/23-orchestrator.md) owns every application-requested transition:

1. refresh the target and compute its exact affected conflict neighborhood;
2. close lease admission and the Run claim gate;
3. drain affected leases;
4. revalidate configuration and the loaded Scribe-owned unit graph;
5. request one physical transaction or supported runtime-native activation;
6. require honest `WARM`, then reopen only under the restoration law.

A parked requester holds no lease. Refusal before effect or an exact restoration reopens
admission. An uncertain mutation remains contained for operator recovery.

## Inspect and Request

```bash
curl -s http://localhost:7134/orchestrator/queues | jq
curl -s http://localhost:7134/orchestrator/status | jq '.mutation_containment'
```

The queues response exposes `depth`, `active`, `paused`, and each lease's `capability_key`,
`holder`, and `priority`. `mutation_containment` is normally `null`; a reason means later
transitions remain fenced.

List the exact registered keys before requesting a transition:

```bash
curl -fsS http://localhost:7134/orchestrator/status \
  | jq -r '.all_capabilities[].capability_key'
```

Copy an eligible local key from that observation. The example below uses Summoning's
`atelier:chat:first-model`; replace it if your declaration differs. Read-only endpoints require
`altar:read`; activation requires `orchestrator:transition`. The current same-host middleware
supplies the fixed `magus:*` scope floor, not credential-backed remote authentication.

Production POSTs also require a matching CSRF cookie and header. Obtain their exact names from the
Altar status response, retain the cookie from that same GET, then submit:

```bash
LYCHD_URL=http://localhost:7134
LYCHD_CAPABILITY=atelier:chat:first-model
LYCHD_COOKIE_JAR=$(mktemp)
LYCHD_STATUS=$(curl -fsS -c "$LYCHD_COOKIE_JAR" "$LYCHD_URL/api/v1/altar/status")
LYCHD_COOKIE_NAME=$(printf '%s' "$LYCHD_STATUS" | jq -r '.csrf.cookie_name')
LYCHD_HEADER_NAME=$(printf '%s' "$LYCHD_STATUS" | jq -r '.csrf.header_name')
LYCHD_CSRF=$(awk -v name="$LYCHD_COOKIE_NAME" '$6 == name {print $7}' "$LYCHD_COOKIE_JAR")

test -n "$LYCHD_CSRF" && curl -sS -i -X POST -G \
  -b "$LYCHD_COOKIE_JAR" -H "$LYCHD_HEADER_NAME: $LYCHD_CSRF" \
  --data-urlencode "target=$LYCHD_CAPABILITY" --data-urlencode "priority=70" \
  "$LYCHD_URL/orchestrator/activate"
rm -f -- "$LYCHD_COOKIE_JAR"
unset LYCHD_STATUS LYCHD_CSRF
```

Keep this operation on the same-host boundary. A failed scope or CSRF check is a refusal, not a
reason to disable the guard or expose the endpoint remotely.

- **202**: the completed transition plan, after target readiness convergence or a confirmed warm,
  open no-op. This endpoint waits for the transition before returning.
- **409**: a hard swap was declined because priority was below
  `min_priority_for_hard_swap`; the response carries the plan and threshold.

After **202**, inspect the selected capability in Nexus or `/orchestrator/status` again, including
`mutation_containment`, before making a later decision. Readiness can change after the response;
any subsequent containment reason keeps later transitions fenced.

Priority is **higher = hotter**. This endpoint is an explicit operational surface, not a side door
for an Agent or extension to bypass ordinary dispatch.

## Switching Settings

Set these fields beneath `[orchestration.switching]` in the Codex.

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `actuator` | `"host-reactor"` | Caged mediated actuation; `"systemd"` selects explicit uncaged mode. |
| `host_reactor_dir` | XDG trigger inbox | Absolute writable intent inbox; sibling journal is derived read-only. |
| `policy` | `"declared-conflicts"` | Select exact active conflict neighbors; `"evict-idle"` is a compatibility alias. |
| `min_priority_for_hard_swap` | `40` | Decline colder hard swaps. |
| `planning_timeout_s` | `30.0` | Bound all managed-runtime observations together for each preflight or replan. |
| `drain_timeout_s` | `120.0` | Bound lease drain. |
| `warmup_timeout_s` | `180.0` | One absolute readiness-convergence budget. |
| `reactor_ack_timeout_s` | `120.0` | Bound only the unclaimed Reactor phase. |

Unknown policy values fail at startup. Coven and alliance labels never alter the compiled conflict
graph.

The Host Reactor records exact outcomes: `.declined.json` proves no effect,
`.restored.json` proves the prior world, `.contained.json` fences an uncertain physical outcome,
`.processing.json` is claimed and nonterminal, and `.rejected.json` is invalid delivery. A
systemd unit may remain active while the probe sees it absent; reconcile that mismatch before
retrying.

## Tune With Intent

- Raise `min_priority_for_hard_swap` to resist disruptive swaps.
- Change planning, drain, and warm-up deadlines to match measured local observation and convergence.
- Mark support services `persistent_resident = true` to keep them outside conflicts and eviction.
- Give incompatible managed Soulstones a shared conflict-domain label; use explicit `[]` only
  after measuring safe coexistence.

`[orchestration.whim]`, `idle_evict_after_s`, and `preload` are not current settings; unknown
configuration is rejected. Resource-aware preloading and eviction remain designed. The current
graph is not a VRAM capacity solver.

[State of Work](../../state-of-the-work.md#declared-conflict-topology) records the available
conflict contract; [safe runtime transitions](../../state-of-the-work.md#safe-runtime-transitions)
remain partial, including soft-load recovery and real-host proof.

## Queue and Routing Context

`[server.jobs]` fixes two in-process queues: `runs` uses `interactive_concurrency = 2`; `rites`
uses `background_concurrency = 4`. These settings bound tasks, not CPU, memory, admission, or
preemption. The optional SAQ diagnostic UI is disabled by default; enabling it starts no second
server. `admin_ui_path` defaults to `/saq`; exposing it requires an explicit access policy.

`[orchestration.routing]` maps Intent source to queue and doctrine priority:

| Source | Queue | Default priority |
| :--- | :--- | :--- |
| `default` | `runs` | `50` |
| `cli` | `runs` | `50` |
| `bridge` | `runs` | `70` |
| `rite` | `rites` | `20` |

Each rule accepts priority 0–100. Queue execution belongs to
[Workers (14)](../../adr/14-workers.md); these values matter here only because transition policy
receives the Run's doctrine priority.
