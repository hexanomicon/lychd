import createClient from "openapi-fetch";

import type { paths } from "./openapi";
import type {
  AltarStatus,
  AtlasCatalogue,
  AtlasCreate,
  AtlasMutation,
  AtlasProject,
  AtlasSummary,
  BridgeSnapshot,
  LoomSummary,
  LoomView,
  NexusSnapshot,
  RunProjectionSnapshot,
  OrbRunSnapshot,
  SessionCreated,
  SessionPage,
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
    readonly status?: number,
    readonly code?: string
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
    const extra = typeof result.error === "object" && result.error !== null && "extra" in result.error
      ? result.error.extra : undefined;
    const code = typeof extra === "object" && extra !== null && "code" in extra && typeof extra.code === "string"
      ? extra.code : undefined;
    throw new ApiError(detail, result.response.status, code);
  }
  return result.data;
}

export async function getAltarStatus(): Promise<AltarStatus> {
  const status = unwrap(await client.GET("/api/v1/altar/status")) as AltarStatus;
  csrfContract = status.csrf;
  return status;
}

export async function getAtlasProjects(
  options: { limit?: number; offset?: number; signal?: AbortSignal } = {}
): Promise<AtlasCatalogue> {
  return unwrap(await client.GET("/api/v1/atlas/projects", {
    signal: options.signal,
    params: { query: { limit: options.limit, offset: options.offset } }
  }));
}

export async function getAtlasProject(id: string, signal?: AbortSignal): Promise<AtlasProject> {
  return unwrap(await client.GET("/api/v1/atlas/projects/{project_id}", {
    signal,
    params: { path: { project_id: id } }
  }));
}

export async function createAtlasProject(data: AtlasCreate): Promise<AtlasProject> {
  return unwrap(await client.POST("/api/v1/atlas/projects", {
    body: data,
    headers: await csrfHeaders()
  }));
}

export async function changeAtlasProject(id: string, data: AtlasMutation): Promise<AtlasProject> {
  return unwrap(await client.POST("/api/v1/atlas/projects/{project_id}/changes", {
    params: { path: { project_id: id } },
    body: data,
    headers: await csrfHeaders()
  }));
}

export async function getAtlasReferences(
  kind: "session" | "run", targetId: string, signal?: AbortSignal
): Promise<AtlasSummary[]> {
  return unwrap(await client.GET("/api/v1/atlas/references", {
    signal,
    params: { query: { kind, target_id: targetId } }
  }));
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

export async function getBridgeSessions(cursor: string, signal?: AbortSignal): Promise<SessionPage> {
  return unwrap(await client.GET("/api/v1/bridge/sessions", {
    signal,
    params: { query: { cursor } }
  }));
}

export async function getRunSnapshot(runId: string): Promise<RunProjectionSnapshot> {
  return unwrap(
    await client.GET("/api/v1/bridge/runs/{run_id}", {
      params: { path: { run_id: runId } }
    })
  ) as RunProjectionSnapshot;
}

export async function cancelBridgeRun(runId: string): Promise<RunProjectionSnapshot> {
  return unwrap(
    await client.POST("/api/v1/bridge/runs/{run_id}/cancel", {
      params: { path: { run_id: runId } },
      headers: await csrfHeaders()
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

export async function sendBridgeMessage(sessionId: string, prompt: string, requestId: string) {
  return unwrap(
    await client.POST("/api/v1/bridge/sessions/{session_id}/messages", {
      params: { path: { session_id: sessionId } },
      body: { prompt, request_id: requestId },
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

export async function getNexusSwap(ticketId: string): Promise<SwapAccepted> {
  return unwrap(
    await client.GET("/api/v1/nexus/swaps/{ticket_id}", {
      params: { path: { ticket_id: ticketId } }
    })
  ) as SwapAccepted;
}

export async function createNexusSwap(target: string, requestId: string): Promise<SwapAccepted> {
  return unwrap(
    await client.POST("/api/v1/nexus/swaps", {
      body: { request_id: requestId, target },
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
  options: { afterSeq?: number; limit?: number; signal?: AbortSignal } = {}
): Promise<OrbRunSnapshot> {
  return unwrap(
    await client.GET("/api/v1/orb/runs/{run_id}", {
      signal: options.signal,
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
  onHardClose?: (message: string) => void;
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
      options.onHardClose?.(message);
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
      if (event.run_id !== runId) {
        fault("The Vessel emitted a run event for another Run.");
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
    if (stopped) return;
    // Non-200 responses (including capacity refusals) stop native EventSource retries.
    // Let the owning view apply its bounded snapshot recovery instead of staying live.
    if (source.readyState === EventSource.CLOSED) {
      fault("The run stream closed; its projection may be stale.");
    } else if (!refetching) onFault("The run stream went quiet; reconnecting.");
  };
  return () => {
    stopped = true;
    source.close();
  };
}

export type TransitionStreamOptions = {
  onHardClose?: (message: string) => void;
};

export function listenToSwap(
  ticketId: string,
  onEvent: (event: ReturnType<typeof transitionEventSchema.parse>) => void,
  onFault: (message: string) => void,
  options: TransitionStreamOptions = {}
): () => void {
  const source = new EventSource(`/api/v1/nexus/swaps/${encodeURIComponent(ticketId)}/events`);
  let stopped = false;

  function fault(message: string) {
    if (stopped) return;
    stopped = true;
    source.close();
    try {
      options.onHardClose?.(message);
    } finally {
      onFault(message);
    }
  }

  source.addEventListener("transition", (raw) => {
    if (stopped) return;
    try {
      const event = transitionEventSchema.parse(JSON.parse((raw as MessageEvent<string>).data));
      if (event.ticket.id !== ticketId) {
        fault("The Vessel emitted a transition event for another ticket.");
        return;
      }
      onEvent(event);
      if (event.ticket.state !== "warming") {
        stopped = true;
        source.close();
      }
    } catch {
      fault("The Vessel emitted an invalid transition event.");
    }
  });
  source.onerror = () => {
    if (!stopped) onFault("The transition stream went quiet.");
  };
  return () => {
    stopped = true;
    source.close();
  };
}
