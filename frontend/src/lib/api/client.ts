import createClient from "openapi-fetch";

import type { paths } from "./openapi";
import type {
  AltarStatus,
  BridgeSnapshot,
  LoomSummary,
  LoomView,
  NexusSnapshot,
  SessionCreated,
  SwapAccepted,
  TransitionPlan
} from "./models";
import { runEventEnvelopeSchema, transitionEventSchema } from "./runtime";

const client = createClient<paths>();

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
  }
}

function csrfHeaders(): Record<string, string> {
  const token = document.cookie
    .split("; ")
    .find((part) => part.startsWith("csrftoken="))
    ?.split("=")
    .slice(1)
    .join("=");
  return token ? { "x-csrftoken": decodeURIComponent(token) } : {};
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
  return unwrap(await client.GET("/api/v1/altar/status")) as AltarStatus;
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

export async function createBridgeSession(): Promise<SessionCreated> {
  return unwrap(
    await client.POST("/api/v1/bridge/sessions", {
      headers: csrfHeaders()
    })
  );
}

export async function sendBridgeMessage(sessionId: string, prompt: string) {
  return unwrap(
    await client.POST("/api/v1/bridge/sessions/{session_id}/messages", {
      params: { path: { session_id: sessionId } },
      body: { prompt },
      headers: csrfHeaders()
    })
  );
}

export async function decideConsent(consentId: string, verdict: "approve" | "deny") {
  return unwrap(
    await client.POST("/api/v1/bridge/consents/{consent_id}/decision", {
      params: { path: { consent_id: consentId } },
      body: { verdict },
      headers: csrfHeaders()
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

export async function createNexusSwap(target: string): Promise<SwapAccepted> {
  return unwrap(
    await client.POST("/api/v1/nexus/swaps", {
      body: { target },
      headers: csrfHeaders()
    })
  ) as SwapAccepted;
}

export async function getLoomCatalogue(): Promise<LoomSummary[]> {
  return unwrap(await client.GET("/api/v1/loom")) as LoomSummary[];
}

export async function getLoomWorkflow(workflow: string): Promise<LoomView> {
  return unwrap(
    await client.GET("/api/v1/loom/{workflow}", {
      params: { path: { workflow } }
    })
  ) as LoomView;
}

export function listenToRun(
  runId: string,
  onEvent: (event: ReturnType<typeof runEventEnvelopeSchema.parse>) => void,
  onFault: (message: string) => void
): () => void {
  const source = new EventSource(`/api/v1/bridge/runs/${encodeURIComponent(runId)}/events`);
  const kinds = ["token", "status", "node", "fragment", "consent", "log", "done", "resync"] as const;
  for (const kind of kinds) {
    source.addEventListener(kind, (raw) => {
      try {
        const event = runEventEnvelopeSchema.parse(JSON.parse((raw as MessageEvent<string>).data));
        onEvent(event);
        if (event.kind === "done") source.close();
      } catch {
        source.close();
        onFault("The Vessel emitted an invalid run event.");
      }
    });
  }
  source.onerror = () => onFault("The run stream went quiet; reconnecting.");
  return () => source.close();
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
