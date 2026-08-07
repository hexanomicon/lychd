---
title: Training Run
icon: material/progress-wrench
---

# :material-progress-wrench: The Training Run

> _A forge without a receipt has made only smoke._

This passage owns execution custody: a Training Intent, immutable Dataset Manifest, and exact
base-model digest, objective, and Recipe enter an admitted Training Run; a frozen Candidate Bundle
and receipt leave. The whole passage is **Designed**; no Training Run path runs. [State of
Work](../../../state-of-the-work.md#soulforge-training) owns delivery, and
[ADR 33](../../../adr/33-training.md#training-execution) owns execution law.

## Admit the strike

Entry requires the immutable Dataset Manifest produced by
[Corpus Admission and Compilation](./corpus.md), base-model and tokenizer/config digests, the
objective, Recipe, and Training Intent with resource envelope. The trainer receives these exact
inputs. It cannot expand the corpus, pull ambient traces, or alter them after admission.

The resource request names exact accelerators, memory, storage, network policy, duration, and
conflicting Covens. Training receives no universal priority. When a physical transition is
required, only affected leases drain; unused devices stay undisturbed. The operator may postpone
or refuse the request.

[Orchestrator](../../../adr/23-orchestrator.md) owns hardware readiness, admission closure,
affected-lease drain, conflict resolution, convergence, and restoration. Corpus meaning and
trainer success remain outside that authority.

The trainer receives only admitted secrets and network access, and writes to fresh Run-owned
locations. A container or Coven label cannot prove isolation: filesystem, credential, network,
process, and resource controls must enforce it and leave evidence. Local and remote execution
share the same custody bar. Local work has no privacy exemption; remote work records egress,
provider custody and retention, network and secret handling, returned artifacts, and receipts.

## Pin the evidence

A Training Run pins input digests, trainer and dependency revisions, environment, randomness,
Recipe-defined precision, budgets and stop conditions, resource observations, logs, checkpoints,
terminal status, and artifact digests. A friendly name never replaces a digest.

The trainer emits candidate bytes with its receipt. The frozen Candidate Bundle binds the base
digest, model or adapter bytes, tokenizer/config changes, Dataset Manifest and Recipe lineage,
trainer receipt, and compatibility claims. Any adapter remains pinned to its exact base and
compatible runtime.

Trainer loss, telemetry, development improvement, and trainer-authored samples remain diagnostics.
The job cannot replace a serving revision, enlarge its resource envelope, or promote its output;
independent evaluation begins only after custody freezes.

## Settle failure

Cancellation or failure preserves terminal truth, logs, completed checkpoints, and quarantined
partials for diagnosis. A partial never becomes a Candidate Bundle. Retry receives a new Training
Run identity and receipt rather than appending to or overwriting history.

If a resource transition fails, Orchestrator restores the exact prior world before admission
reopens; otherwise uncertainty stays visible and contained. Process exit alone is not clean
recovery.

The passage ends with either a frozen Candidate Bundle and receipt ready for independent handoff,
or exact failure or cancellation truth with every partial quarantined.
