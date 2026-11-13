import { z } from "zod";
import type { OrbEventEnvelope, OrbRunSnapshot, OrbRunPage } from "$lib/api/models";

const sequence = z.number().int().min(-1);
const evidenceSchema = z.object({
  event_id: z.string(), seq: z.number().int().nonnegative(), kind: z.string(), occurred_at: z.string(),
  summary: z.string(), capture: z.enum(["process_local", "durable_best_effort"]),
  subject_key: z.string().nullish(), phase: z.string().nullish(), occurrence_id: z.string().nullish(),
  transition_request_id: z.string().nullish(), nexus_path: z.string().nullish(),
  animator_name: z.string().nullish(), capability_family: z.string().nullish(),
  model_id: z.string().nullish(), grant_id: z.string().nullish(),
  consent_id: z.string().max(128).regex(/^[A-Za-z0-9][A-Za-z0-9._~-]*$/).refine((id) => id.trim() === id).nullish()
});
const gapSchema = z.object({
  start_seq: z.number().int().nonnegative(), end_seq: z.number().int().nonnegative(),
  classification: z.literal("unknown_or_omitted")
}).refine((gap) => gap.start_seq <= gap.end_seq);


const workflowSchema = z.object({
  schema_version: z.number().int(), pattern_id: z.string(), revision: z.string(), digest: z.string(), title: z.string(), description: z.string(),
  entry_node: z.string(), checkpoint_schema: z.string(), implementation_revision: z.string(), mermaid_source: z.string(), trigger_hint: z.string(), publication: z.literal("published"),
  nodes: z.array(z.object({ key: z.string(), label: z.string(), kind: z.string() })),
  edges: z.array(z.object({ key: z.string(), source: z.string(), target: z.string(), relation: z.string() }))
});
const creationSummarySchema = z.object({
  case_id: z.uuid(), admission_id: z.uuid(), run_id: z.string(), admission_current: z.boolean(),
  native_status: z.enum(["reserved", "candidate", "accepted", "rejected", "partial", "incomplete", "unknown", "cancelled"]),
  reason_code: z.string().max(64).nullable(), deadline: z.iso.datetime({ offset: true }),
  deadline_elapsed: z.boolean(), slot_encumbered: z.boolean(),
  constructor_present: z.boolean(), constructor_adopted: z.boolean(),
  verifier_present: z.boolean(), verifier_adopted: z.boolean(), candidate_present: z.boolean(), verdict_present: z.boolean(),
  native_disposition: z.enum(["accepted", "rejected", "partial", "incomplete"]).nullable(),
  external_disposition: z.enum(["accepted", "rejected", "partial", "incomplete", "not_assessed"]).nullable(),
  feedback_status: z.enum(["unassessed", "review_required", "hold", "rejected"]),
  current_assessment_id: z.uuid().nullable(), current_decision_id: z.uuid().nullable()
});
const runSummarySchema = z.object({ run_id: z.string(), session_id: z.string(), workflow_name: z.string(), status: z.string(), created_at: z.string(), started_at: z.string().nullable(), finished_at: z.string().nullable(), error_present: z.boolean(), bridge_path: z.string().nullable(), application_path: z.string().nullable().optional() });
const bridgePreferenceSchema = z.object({
  policy_schema_version: z.literal(1), policy_digest: z.string().regex(/^[0-9a-f]{64}$/),
  batch_started_at: z.iso.datetime({ offset: true }), batch_finished_at: z.iso.datetime({ offset: true }),
  selected_capability_key: z.string().min(1).max(512),
  routes: z.array(z.object({
    capability_key: z.string().min(1).max(512), weight: z.number().int().min(0).max(1_000_000),
    phase: z.enum(["cold", "activatable", "warming", "warm", "error", "unknown"]).nullable(),
    observed_at: z.iso.datetime({ offset: true }).nullable(), admission_open: z.boolean(),
    exclusion_code: z.enum(["disabled", "not_warm", "admission_closed", "readiness_changed"]).nullable()
  })).length(2)
}).refine((summary) => new Set(summary.routes.map((route) => route.capability_key)).size === 2);

export const orbSnapshotSchema: z.ZodType<OrbRunSnapshot> = z.object({
  schema_version: z.literal(1), snapshot_at: z.string(), capture: z.enum(["process_local", "durable_best_effort"]),
  ledger_head_seq: sequence, page_end_seq: sequence.nullable(), has_more: z.boolean(),
  live_tail: z.literal("ledger_poll"), next_after_seq: sequence.nullable(), known_omissions: z.array(z.string()),
  evidence: z.array(evidenceSchema).max(100), gaps: z.array(gapSchema).max(101),
  workflow: workflowSchema.nullable(),
  creation: creationSummarySchema.nullish(),
  bridge_preference: bridgePreferenceSchema.nullish(),
  pattern: z.object({ pattern_id: z.string(), revision: z.string(), digest: z.string().nullable(), exact: z.boolean(), loom_path: z.string().nullable() }),
  run: runSummarySchema,
  delegated_jobs: z.array(z.object({
    job_id: z.string(), request_id: z.string(), step_id: z.string(), runtime: z.string(), profile: z.string(), status: z.string(),
    output_present: z.boolean(), error_present: z.boolean(), artifact_count: z.number().int().nonnegative(), events_truncated: z.boolean(),
    events: z.array(z.object({ event_id: z.string(), seq: z.number().int().nonnegative(), kind: z.string(), status: z.string(), occurred_at: z.string() })).max(64)
  })).max(32)
});
const envelopeSchema: z.ZodType<OrbEventEnvelope> = z.object({
  schema_version: z.literal(1), run_id: z.string(), kind: z.enum(["evidence", "reset", "settled"]),
  after_seq: sequence, cursor: sequence, snapshot: orbSnapshotSchema
});

export type OrbConnection = "connecting" | "connected" | "reconnecting" | "closed" | "settled";
export interface OrbLiveCallbacks {
  onFrame: (frame: OrbEventEnvelope) => void;
  onConnection: (state: OrbConnection) => void;
  onReset: () => void;
  onFault: (message: string) => void;
}

/** A selected Run's retained-ledger feed; transport state never establishes Run status. */
export function listenToOrb(runId: string, afterSeq: number, callbacks: OrbLiveCallbacks): () => void {
  const source = new EventSource(`/api/v1/orb/runs/${encodeURIComponent(runId)}/events?after_seq=${afterSeq}`);
  let cursor = afterSeq;
  let stopped = false;
  callbacks.onConnection("connecting");
  const close = () => { stopped = true; source.close(); };
  const fault = (message: string) => {
    if (stopped) return;
    close();
    callbacks.onConnection("closed");
    callbacks.onFault(message);
  };
  source.onopen = () => { if (!stopped) callbacks.onConnection("connected"); };
  for (const kind of ["evidence", "reset", "settled"] as const) {
    source.addEventListener(kind, (raw) => {
      if (stopped) return;
      const message = raw as MessageEvent<string>;
      let frame: OrbEventEnvelope;
      try { frame = envelopeSchema.parse(JSON.parse(message.data)); }
      catch { fault("The Orb feed supplied an invalid evidence envelope. Refresh the retained account."); return; }
      if (frame.kind !== kind || frame.run_id !== runId || frame.snapshot.run.run_id !== runId ||
          (frame.snapshot.creation != null && frame.snapshot.creation.run_id !== runId) ||
          (message.lastEventId && message.lastEventId !== String(frame.cursor))) {
        fault("The Orb feed identity does not match this Run or cursor. Refresh the retained account."); return;
      }
      if (kind === "reset") {
        close();
        callbacks.onConnection("closed");
        callbacks.onReset();
        return;
      }
      const records = frame.snapshot.evidence;
      const ordered = records.every((row, index) => row.seq > frame.after_seq && row.seq <= frame.cursor &&
        (index === 0 || row.seq > records[index - 1]!.seq));
      if (!ordered || frame.cursor < frame.after_seq || frame.cursor > frame.snapshot.ledger_head_seq ||
          (records.length ? records.at(-1)!.seq !== frame.cursor : frame.cursor !== frame.after_seq)) {
        fault("The Orb feed supplied an inconsistent evidence range. Refresh the retained account."); return;
      }
      // Native EventSource replay can repeat an already delivered page.
      if (frame.cursor < cursor || (frame.cursor === cursor && frame.after_seq < cursor)) return;
      if (frame.after_seq !== cursor) {
        fault("The Orb feed cursor skipped its loaded boundary. Refresh the retained account."); return;
      }
      cursor = frame.cursor;
      callbacks.onFrame(frame);
      if (kind === "settled") {
        close();
        callbacks.onConnection("settled");
      }
    });
  }
  source.onerror = () => {
    if (stopped) return;
    if (source.readyState === EventSource.CLOSED) fault("The Orb feed closed. Retained evidence remains readable; refresh to reconnect.");
    else callbacks.onConnection("reconnecting");
  };
  return close;
}

const pageSchema: z.ZodType<OrbRunPage> = z.object({
  schema_version: z.literal(1), snapshot_at: z.string(), runs: z.array(runSummarySchema).max(50),
  next_cursor: z.string().nullable(), capture: z.enum(["process_local", "durable_best_effort"])
});

export class OrbCatalogueError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

export async function getOrbCatalogue(cursor?: string, signal?: AbortSignal): Promise<OrbRunPage> {
  const query = new URLSearchParams({ limit: "20" });
  if (cursor) query.set("cursor", cursor);
  const response = await fetch(`/api/v1/orb/runs?${query}`, { signal });
  if (!response.ok) throw new OrbCatalogueError(response.status === 403 || response.status === 401 ? "This authority cannot read the Run catalogue." : `The Run catalogue could not be read (${response.status}).`, response.status);
  return pageSchema.parse(await response.json());
}
