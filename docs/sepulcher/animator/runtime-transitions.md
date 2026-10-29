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

Retrieve the dedicated local credential with `lychd access` as described in
[The Awakening](../../summoning.md#the-awakening). Each command below uses `--user magus` so curl
prompts for the password. Enter it at that prompt; keep it out of URLs and command arguments.

```bash
curl --user magus -fsS http://localhost:7134/orchestrator/queues | jq
curl --user magus -fsS http://localhost:7134/orchestrator/status | jq '.mutation_containment'
```

The queues response exposes `depth`, `active`, `paused`, and each lease's `capability_key`,
`holder`, and `priority`. `mutation_containment` is normally `null`; a reason means later
transitions remain fenced.

List the exact registered keys before requesting a transition:

```bash
curl --user magus -fsS http://localhost:7134/orchestrator/status \
  | jq -r '.all_capabilities[].capability_key'
```

Copy an eligible local key from that observation. The example below uses Summoning's
`atelier:chat:first-model`; replace it if your declaration differs. Read-only endpoints require
`altar:read`; activation requires `orchestrator:transition`. The current same-host middleware
assigns the fixed `magus:*` scope floor after verifying the local credential. This is not remote
authentication.

Production POSTs also require a matching CSRF cookie and header. Obtain their exact names from the
Altar status response, retain the cookie from that same GET, then submit:

```bash
LYCHD_URL=http://localhost:7134
LYCHD_CAPABILITY=atelier:chat:first-model
LYCHD_COOKIE_JAR=$(mktemp)
LYCHD_STATUS=$(curl --user magus -fsS -c "$LYCHD_COOKIE_JAR" "$LYCHD_URL/api/v1/altar/status")
LYCHD_COOKIE_NAME=$(printf '%s' "$LYCHD_STATUS" | jq -r '.csrf.cookie_name')
LYCHD_HEADER_NAME=$(printf '%s' "$LYCHD_STATUS" | jq -r '.csrf.header_name')
LYCHD_CSRF=$(awk -v name="$LYCHD_COOKIE_NAME" '$6 == name {print $7}' "$LYCHD_COOKIE_JAR")

test -n "$LYCHD_CSRF" && curl --user magus -sS -i -X POST -G \
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
- **400**: invalid `admission_timeout_s`.
- **409**: a hard swap was declined because priority was below
  `min_priority_for_hard_swap`, or an admission window expired. Priority refusal carries the
  plan and threshold; admission expiry carries `code` and readable `detail`, as described in
  [Limit admission time](#limit-admission-time).

After **202**, inspect the selected capability in Nexus or `/orchestrator/status` again, including
`mutation_containment`, before making a later decision. Readiness can change after the response;
any subsequent containment reason keeps later transitions fenced.

Priority is **higher = hotter**. This endpoint is an explicit operational surface, not a side door
for an Agent or extension to bypass ordinary dispatch.

## Limit admission time

When a transition would no longer be useful after a short wait, add
`--data-urlencode "admission_timeout_s=10"` to the activation command. This optional query value
counts seconds from entry to the activation handler. It must be finite and nonnegative; `0`
declines immediately. Omission adds no caller-owned admission cutoff.

Treat the cutoff as a limit on admitting the change. It covers queueing, planning, lease drain,
and observation before activation. It ends when Orchestrator invokes the actuator or adapter,
or confirms readiness on a path requiring no activation. If a capability is already warming,
it must become honestly ready within this window.

After admission, the request continues waiting for settlement, even beyond the cutoff. Planning,
drain, and convergence retain their separate safety budgets. A local safety deadline that expires
first keeps its existing failure classification.

Requests for the same capability and priority share one in-flight transition. The first request
owns its admission cutoff. A follower may limit how long it waits for admission, but cannot cancel
the owner's work. A nonexpired follower that joins already-admitted work waits for settlement.
Thus an untimed follower may inherit a timed owner's refusal, while a timed follower cannot shorten
an untimed owner's budget. Different priorities create separate requests.

Admission refusal returns **409** with readable `detail` and one of these codes:

| `code` | Meaning |
| --- | --- |
| `transition_admission_expired` | The request arrived expired, or the transition owner's admission window ended. |
| `transition_admission_wait_expired` | Only this follower's wait ended; the shared transition may continue. |

Invalid admission durations return **400**. A refused request cannot use its admission cutoff
to abandon required cleanup, and disconnecting does not prove that physical work stopped.
Inspect current status before retrying. This request option is separate from Codex switching
settings and does not set a deadline for the whole operation.

## Switching Settings

Set these fields beneath `[orchestration.switching]` in the Codex.

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `actuator` | `"host-reactor"` | Managed-container mediated actuation; `"systemd"` is a host-adapter test mechanism, not a host-native Core profile. |
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

## Recover an interrupted soft activation

Before activating a model through a runtime-native API, the Vessel writes
`runtime-guard/pending.json` in the Crypt. An unfinished record means the activation's physical
outcome still needs reconciliation. Both actuator profiles block startup before any Run queue
connects while that record remains. Restarting, changing configuration, or observing a warm model
cannot clear it.

The owner-only `0700` directory is provisioned by `lychd init` and mounted read-write by the
generated Vessel binding. Existing installations need updated initialization and binding before
using this path. Missing or unsafe storage makes startup refuse.

For recovery, establish and keep both the Vessel and the record's target Animator stopped under
a separately authorized [operator recovery plan](../../summoning.md#close-the-rite). The current
public stop command cannot establish that state for an active Vessel;
[State of Work](../../state-of-the-work.md#core-cli-rites) records the lifecycle limit. If the
stopped state cannot be established, keep the pending record and admission fenced. Once those
prerequisites hold, read the exact `activation_id` from that owner-only record, then invoke the
bounded host helper:

```bash
lychd reactor recover-soft ACTIVATION_ID
```

Supply the record's exact 32-character `ACTIVATION_ID`. The hidden helper performs no start or
stop itself. It validates the record against current declarations, attests the Scribe-owned
loaded topology, and verifies that both Vessel and affected runtime are stopped with no main or
control processes and no pending systemd work. Only then can it clear that exact record.

Changed configuration, corrupt records, unknown ownership, live or uncertain runtime state, and
persistence errors refuse release. Keep the record and reconcile the reported discrepancy;
manual deletion would remove the evidence without proving recovery. Host Reactor `.contained`
and `.processing` records retain a separate recovery boundary.

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
preemption. The raw SAQ administrative UI is disabled; setting `admin_ui_enabled = true` is
refused during startup. Inspect queues through the curated Altar projection and the authenticated
endpoints above.

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
