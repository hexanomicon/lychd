---
title: Vessel
icon: material/skull-scan
---

# :material-skull-scan: Vessel

> _Through a mortal body, the daemon takes breath._

The **Vessel** is the application process through which LychD receives work and serves the
[Altar](../../divination/altar/index.md). Its composition root assembles domain services, admits
supported Invocations, and gives queued execution to [Ghouls](ghouls.md). The
[Lich](../lich/index.md) is the recurrent whole that may answer through this process and return
after it dies.

## One process takes breath

A request enters through Granian's production ASGI service. Litestar supplies routing, injection,
lifecycle, and API authority, while Pydantic validates configuration and typed boundaries.
Pydantic AI provides Agent and Graph mechanics over [Animator](../animator/index.md) capabilities.
Litestar also serves the compiled static SvelteKit client, so the browser remains a projection
without a separate server authority.

Exactly one ASGI process is required. Two SAQ workers, live Run events, cancellation, and the
service graph share its event loop. A second process or reload supervisor would create another
private runtime world. A blocking Ghoul can therefore delay HTTP as well as other work.

## Before the Altar opens

Startup first connects the queues, constructs services, warms the registry, and synchronizes
standing policy. Before workers can claim jobs or HTTP can expose those services, the PostgreSQL
profile must reconcile what the previous process left behind: canonical Runs, their exact
deliveries, checkpoints, Consent, and delegated-wait owners. These records determine whether
work may resume, must remain parked, or needs containment and settlement.

Required reconciliation must finish cleanly before admission opens; startup aborts on failure
or degradation. The memory profile has no cross-process truth and retains
best-effort recovery. After admission opens, lifespan-owned delivery, consent, and delegated-wait
relays continue repairing their respective publication and return obligations.

The owned launcher enters the application lifespan explicitly, then runs one embedded ASGI
worker with no lifespan of its own. Retirement first refuses new application callbacks and waits
for existing callbacks, including background work continuing after a response was delivered.
Only then does it close application services. A required startup or shutdown failure produces a
failed process exit. Signals request this retirement; the user manager's outer timeout decides
whether a stuck process must ultimately be forced.

The managed Vessel image uses the fixed internal `0.0.0.0:8000` listener behind generated
loopback-only host publication. Host-native Vessel deployment and hidden `lychd serve` are
retired. Images must be rebuilt to acquire launcher changes; unsupported server tuning refuses.

Current active installation lifecycle completion is unavailable until authenticated container
admission and exact settlement are implemented and qualified. The old signed native stops and
trusted installed-hybrid receipt remain frozen historical observations of their removed profile.
They do not qualify a rebuilt Vessel or authorize fallback control. Follow the current
[CLI boundary](../../state-of-the-work.md#core-cli-rites) before an installation operation.

Shutdown stops workers before their collaborators and queues. Process death loses active tasks,
subscribers, leases, and other volatile state. Only records committed through the
[Phylactery](../phylactery/index.md) can enter a supported return path.

Follow [Ghouls](ghouls.md) from admission to settlement, or
[Reanimation](../phylactery/reanimation.md) across process death.
[Backend](../../adr/11-backend.md) owns the architecture;
[State of Work](../../state-of-the-work.md#topology-a-local-runs) records the available local
execution and its evidence limits.
