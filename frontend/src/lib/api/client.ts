import createClient from "openapi-fetch";

import type { paths } from "./openapi";
import type {
  AltarStatus,
  BridgeSnapshot,
  LoomSummary,
  LoomView,
  NexusSnapshot,
  RunProjectionSnapshot,
  OrbRunSnapshot,
  SessionCreated,
  SwapAccepted,
  TransitionPlan,
  TransitionRecordView
} from "./models";
import { csrfHeadersFromCookie, type CsrfContract } from "./csrf";
import { runEventEnvelopeSchema, transitionEventSchema } from "./runtime";
import { initialRunEventCursor, reduceRunEventCursor } from "./run-stream";

const client = createClient<paths>();
let csrfContract: CsrfContract | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
  }
}

async function csrfHeaders(): Promise<Record<string, string>> {
  const contract = csrfContract ?? (await getAltarStatus()).csrf;
  return csrfHeadersFromCookie(contract, document.cookie);
}

function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    const detail =
      typeof result.error === "object" && result.error !== null && "detail" in result.error
        ? String(result.error.detail)
        : `The Vessel refused the request (${result.response.status}).`;
    throw new ApiError(detail, result.response.status);
  }
  return result.data;
}

export async function getAltarStatus(): Promise<AltarStatus> {
  const status = unwrap(await client.GET("/api/v1/altar/status")) as AltarStatus;
  csrfContract = status.csrf;
  return status;
}

export async function getBridgeSnapshot(sessionId?: string): Promise<BridgeSnapshot> {
  if (sessionId) {
    return unwrap(
      await client.GET("/api/v1/bridge/sessions/{session_id}", {
        params: { path: { session_id: sessionId } }
      })
    ) as BridgeSnapshot;
  }
  return unwrap(await client.GET("/api/v1/bridge")) as BridgeSnapshot;
}

export async function getRunSnapshot(runId: string): Promise<RunProjectionSnapshot> {
  return unwrap(
    await client.GET("/api/v1/bridge/runs/{run_id}", {
      params: { path: { run_id: runId } }
    })
  ) as RunProjectionSnapshot;
}

export async function createBridgeSession(): Promise<SessionCreated> {
  return unwrap(
    await client.POST("/api/v1/bridge/sessions", {
      headers: await csrfHeaders()
    })
  );
}

export async function sendBridgeMessage(sessionId: string, prompt: string) {
  return unwrap(
    await client.POST("/api/v1/bridge/sessions/{session_id}/messages", {
      params: { path: { session_id: sessionId } },
      body: { prompt },
      headers: await csrfHeaders()
    })
  );
}

export async function decideConsent(consentId: string, verdict: "approve" | "deny") {
  return unwrap(
    await client.POST("/api/v1/bridge/consents/{consent_id}/decision", {
      params: { path: { consent_id: consentId } },
      body: { verdict },
      headers: await csrfHeaders()
    })
  );
}

export async function getNexusSnapshot(): Promise<NexusSnapshot> {
  return unwrap(await client.GET("/api/v1/nexus")) as NexusSnapshot;
}

export async function getNexusPlan(target: string): Promise<TransitionPlan> {
  return unwrap(
    await client.GET("/api/v1/nexus/plan", {
      params: { query: { target } }
    })
  ) as TransitionPlan;
}

export async function getNexusTransition(requestId: string): Promise<TransitionRecordView> {
  return unwrap(
    await client.GET("/api/v1/nexus/transitions/{request_id}", {
      params: { path: { request_id: requestId } }
    })
  ) as TransitionRecordView;
}

export async function createNexusSwap(target: string): Promise<SwapAccepted> {
  return unwrap(
    await client.POST("/api/v1/nexus/swaps", {
      body: { target },
      headers: await csrfHeaders()
    })
  ) as SwapAccepted;
}

export async function getLoomCatalogue(): Promise<LoomSummary[]> {
  return unwrap(await client.GET("/api/v1/loom")) as LoomSummary[];
}

export async function getLoomPatternRevision(
  patternId: string,
  revision: string
): Promise<LoomView> {
  return unwrap(
    await client.GET("/api/v1/loom/{pattern_id}/{revision}", {
      params: { path: { pattern_id: patternId, revision } }
    })
  ) as LoomView;
}

export async function getOrbRun(
  runId: string,
  options: { afterSeq?: number; limit?: number } = {}
): Promise<OrbRunSnapshot> {
  return unwrap(
    await client.GET("/api/v1/orb/runs/{run_id}", {
      params: {
        path: { run_id: runId },
        query: {
          after_seq: options.afterSeq,
          limit: options.limit
        }
      }
    })
  ) as OrbRunSnapshot;
}

export type RunStreamOptions = {
  initialCursor?: number;
  onHardClose?: () => void;
};

export function listenToRun(
  runId: string,
  onEvent: (event: ReturnType<typeof runEventEnvelopeSchema.parse>) => void,
  onFault: (message: string) => void,
  onRefetch: () => Promise<{ cursor: number; terminal: boolean }>,
  options: RunStreamOptions = {}
): () => void {
  const source = new EventSource(`/api/v1/bridge/runs/${encodeURIComponent(runId)}/events`);
  const kinds = [
    "token",
    "status",
    "node",
    "dispatch",
    "transition",
    "fragment",
    "consent",
    "log",
    "done",
    "resync"
  ] as const;
  let cursor = initialRunEventCursor(options.initialCursor);
  let serial = Promise.resolve();
  let refetching = false;
  let stopped = false;

  function fault(message: string) {
    if (stopped) return;
    stopped = true;
    source.close();
    try {
      options.onHardClose?.();
    } finally {
      onFault(message);
    }
  }

  for (const kind of kinds) {
    source.addEventListener(kind, (raw) => {
      let event: ReturnType<typeof runEventEnvelopeSchema.parse>;
      try {
        event = runEventEnvelopeSchema.parse(JSON.parse((raw as MessageEvent<string>).data));
      } catch {
        fault("The Vessel emitted an invalid run event.");
        return;
      }

      serial = serial
        .then(async () => {
          if (stopped) return;
          const disposition = reduceRunEventCursor(cursor, event);
          cursor = disposition.cursor;
          if (disposition.refetch) {
            refetching = true;
            const snapshot = await onRefetch();
            cursor = initialRunEventCursor(snapshot.cursor);
            refetching = false;
            if (snapshot.terminal) {
              stopped = true;
              source.close();
            }
          } else if (disposition.deliver) {
            onEvent(event);
          }
          if (event.kind === "done") {
            stopped = true;
            source.close();
          }
        })
        .catch(() => fault("The authoritative run snapshot could not be refreshed."));
    });
  }
  source.onerror = () => {
    if (!refetching && !stopped) onFault("The run stream went quiet; reconnecting.");
  };
  return () => {
    stopped = true;
    source.close();
  };
}

export function listenToSwap(
  ticketId: string,
  onEvent: (event: ReturnType<typeof transitionEventSchema.parse>) => void,
  onFault: (message: string) => void
): () => void {
  const source = new EventSource(`/api/v1/nexus/swaps/${encodeURIComponent(ticketId)}/events`);
  source.addEventListener("transition", (raw) => {
    try {
      const event = transitionEventSchema.parse(JSON.parse((raw as MessageEvent<string>).data));
      onEvent(event);
      if (event.ticket.state !== "warming") source.close();
    } catch {
      source.close();
      onFault("The Vessel emitted an invalid transition event.");
    }
  });
  source.onerror = () => onFault("The transition stream went quiet.");
  return () => source.close();
}
