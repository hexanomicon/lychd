import { z } from "zod";

import type { RunEventEnvelope, TransitionEventEnvelope } from "./models";

export const runEventEnvelopeSchema: z.ZodType<RunEventEnvelope> = z.object({
  schema_version: z.literal(1),
  run_id: z.string(),
  seq: z.number().int().nonnegative(),
  kind: z.enum(["token", "status", "node", "fragment", "consent", "log", "done", "resync"]),
  occurred_at: z.string(),
  payload: z.record(z.string(), z.unknown())
});

export const transitionEventSchema: z.ZodType<TransitionEventEnvelope> = z.object({
  schema_version: z.literal(1),
  seq: z.number().int().nonnegative(),
  ticket: z.object({
    id: z.string(),
    target: z.string(),
    state: z.enum(["warming", "settled", "failed"]),
    action_type: z.string(),
    total_metabolic_cost: z.number()
  })
});
