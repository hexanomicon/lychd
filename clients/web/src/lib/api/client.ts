import createClient from "openapi-fetch";
import type { InspectionSelection } from "./inspection";

import type { components, paths } from "./openapi";
import type {
  AltarStatus,
  ArchiveRunRecall,
  AtlasCatalogue,
  AtlasCreate,
  AtlasMutation,
  AtlasProject,
  AtlasSummary,
  CanvasProjectCreate,
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

export async function getDictationDiscovery(signal?: AbortSignal): Promise<components["schemas"]["DictationDiscovery"]> {
  return unwrap(await client.GET("/api/v1/bridge/dictation", { signal }));
}

export async function transcribeDictation(
  body: components["schemas"]["DictationRequest"], signal?: AbortSignal
): Promise<components["schemas"]["DictationResult"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/transcribe", {
    body, signal, headers: await csrfHeaders()
  }));
}

export async function getDictationAttempt(attemptId: string, signal?: AbortSignal): Promise<components["schemas"]["DictationResult"]> {
  return unwrap(await client.GET("/api/v1/bridge/dictation/attempts/{attempt_id}", {
    signal, params: { path: { attempt_id: attemptId } }
  }));
}

export async function listDictationAttempts(signal?: AbortSignal): Promise<components["schemas"]["DictationAttemptSummary"][]> {
  return unwrap(await client.GET("/api/v1/bridge/dictation/attempts", { signal }));
}

export async function recordDictationCorrection(
  body: components["schemas"]["DictationCorrectionRequest"]
): Promise<components["schemas"]["DictationCorrection"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/corrections", {
    body, headers: await csrfHeaders()
  }));
}

export async function listDictationCorrections(signal?: AbortSignal): Promise<components["schemas"]["DictationCorrection"][]> {
  return unwrap(await client.GET("/api/v1/bridge/dictation/corrections", { signal }));
}

export async function deleteDictationAttempt(attemptId: string): Promise<components["schemas"]["DictationDeleted"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/attempts/{attempt_id}/delete", {
    params: { path: { attempt_id: attemptId } }, headers: await csrfHeaders()
  }));
}

export async function listDictationLexicon(signal?: AbortSignal): Promise<components["schemas"]["DictationLexiconRule"][]> {
  return unwrap(await client.GET("/api/v1/bridge/dictation/lexicon", { signal }));
}

export async function approveDictationLexicon(
  body: components["schemas"]["DictationLexiconRuleRequest"]
): Promise<components["schemas"]["DictationLexiconRule"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/lexicon", {
    body, headers: await csrfHeaders()
  }));
}

export async function deleteDictationLexicon(ruleId: string): Promise<components["schemas"]["DictationLexiconDeleted"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/lexicon/{rule_id}/delete", {
    params: { path: { rule_id: ruleId } }, headers: await csrfHeaders()
  }));
}

export async function getDictationSuggestions(
  body: components["schemas"]["DictationSuggestionRequest"], signal?: AbortSignal
): Promise<components["schemas"]["DictationSuggestion"]> {
  return unwrap(await client.POST("/api/v1/bridge/dictation/suggestions", {
    body, signal, headers: await csrfHeaders()
  }));
}

export async function submitCreationInvestigation(
  request: components["schemas"]["InvestigationRequest"]
): Promise<components["schemas"]["CaseView"]> {
  return unwrap(await client.POST("/api/v1/creation/investigations", {
    body: request,
    headers: await csrfHeaders()
  }));
}

export async function readCreationInvestigation(
  caseId: string, signal?: AbortSignal
): Promise<components["schemas"]["CaseView"]> {
  return unwrap(await client.GET("/api/v1/creation/investigations/{case_id}", {
    signal,
    params: { path: { case_id: caseId } }
  }));
}

export async function readCreationFeedback(
  caseId: string, signal?: AbortSignal
): Promise<components["schemas"]["FeedbackView"]> {
  return unwrap(await client.GET("/api/v1/creation/investigations/{case_id}/feedback", {
    signal,
    params: { path: { case_id: caseId } }
  }));
}

export async function getScavengerState(signal?: AbortSignal): Promise<components["schemas"]["ScavengerState"]> {
  return unwrap(await client.GET("/api/v1/scavenger", { signal }));
}

export async function submitMarketObservation(body: components["schemas"]["ObserveMarketRequest"]): Promise<components["schemas"]["ObservationAdmission"]> {
  return unwrap(await client.POST("/api/v1/scavenger/observations", { body, headers: await csrfHeaders() }));
}

export async function readMarketObservation(admissionId: string, signal?: AbortSignal): Promise<components["schemas"]["ObservationDocument"]> {
  return unwrap(await client.GET("/api/v1/scavenger/observations/{admission_id}", {
    signal, params: { path: { admission_id: admissionId } }
  }));
}

export async function getMarketObservationConsent(admissionId: string, signal?: AbortSignal): Promise<components["schemas"]["ConsentCard"] | null> {
  return unwrap(await client.GET("/api/v1/scavenger/observations/{admission_id}/consent", {
    signal, params: { path: { admission_id: admissionId } }
  }));
}

export async function filterMarketObservation(admissionId: string, body: components["schemas"]["LiteralFilter"], signal?: AbortSignal): Promise<components["schemas"]["ObservationView"]> {
  return unwrap(await client.POST("/api/v1/scavenger/observations/{admission_id}/view", {
    signal, params: { path: { admission_id: admissionId } }, body, headers: await csrfHeaders()
  }));
}

export async function deleteMarketObservation(admissionId: string, body: components["schemas"]["DeleteObservationRequest"]): Promise<components["schemas"]["ObservationDeleted"]> {
  return unwrap(await client.POST("/api/v1/scavenger/observations/{admission_id}/delete", {
    params: { path: { admission_id: admissionId } }, body, headers: await csrfHeaders()
  }));
}

export async function getArchiveProfile(signal?: AbortSignal): Promise<components["schemas"]["ArchiveProfile"]> {
  return unwrap(await client.GET("/api/v1/archive/profile", { signal }));
}
export async function discoverArchiveGeneration(signal?: AbortSignal): Promise<components["schemas"]["GenerationRef"]> {
  return unwrap(await client.GET("/api/v1/archive/derivations/generations/configured", { signal }));
}
export async function registerArchiveGeneration(body: components["schemas"]["GenerationRef"]): Promise<components["schemas"]["GenerationStatus"]> {
  return unwrap(await client.POST("/api/v1/archive/derivations/generations/register", { body, headers: await csrfHeaders() }));
}
export async function deriveArchiveNote(body: components["schemas"]["DerivationRequest"]): Promise<components["schemas"]["DerivationStatus"]> {
  return unwrap(await client.POST("/api/v1/archive/derivations/derive", { body, headers: await csrfHeaders() }));
}
export async function inspectArchiveDerivation(body: components["schemas"]["DerivationRequest"], signal?: AbortSignal): Promise<components["schemas"]["DerivationStatus"]> {
  return unwrap(await client.POST("/api/v1/archive/derivations/status", { body, signal, headers: await csrfHeaders() }));
}
export async function recallArchiveSemanticNotes(body: components["schemas"]["SemanticRecallRequest"]): Promise<components["schemas"]["SemanticRecallResult"]> {
  return unwrap(await client.POST("/api/v1/archive/semantic/recalls", { body, headers: await csrfHeaders() }));
}
export async function inspectArchiveSemanticRecall(body: components["schemas"]["SemanticRecallRequest"], signal?: AbortSignal): Promise<components["schemas"]["SemanticRecallReceipt"] | null> {
  return unwrap(await client.POST("/api/v1/archive/semantic/recalls/inspect", { body, signal, headers: await csrfHeaders() }));
}
export async function resolveArchiveSemanticRecall(receiptId: string, body: components["schemas"]["ArchiveResolveIntent"], signal?: AbortSignal): Promise<components["schemas"]["SemanticRecallProjection"]> {
  return unwrap(await client.POST("/api/v1/archive/semantic/recalls/{receipt_id}/resolve", {
    params: { path: { receipt_id: receiptId } }, body, signal, headers: await csrfHeaders()
  }));
}
export async function getArchiveBridgeDefault(signal?: AbortSignal): Promise<components["schemas"]["ArchiveBridgeDefault"]> {
  return unwrap(await client.GET("/api/v1/archive/bridge-default", { signal }));
}
export async function listArchiveNotes(options: { sourceKey?: string; cursor?: string; signal?: AbortSignal } = {}): Promise<components["schemas"]["NoteListPage"]> {
  return unwrap(await client.GET("/api/v1/archive/notes", {
    signal: options.signal, params: { query: { limit: 50, source_key: options.sourceKey, cursor: options.cursor } }
  }));
}
export async function getArchiveRunRecall(runId: string, signal?: AbortSignal): Promise<ArchiveRunRecall> {
  return unwrap(await client.GET("/api/v1/archive/runs/{run_id}/recall", {
    signal, params: { path: { run_id: runId } }
  }));
}

export async function getArchiveNote(recordId: string, signal?: AbortSignal): Promise<components["schemas"]["NoteRecord"]> {
  return unwrap(await client.GET("/api/v1/archive/notes/{record_id}", { signal, params: { path: { record_id: recordId } } }));
}
export async function admitArchiveNote(body: components["schemas"]["NoteProposal"]): Promise<components["schemas"]["NoteRecord"]> {
  return unwrap(await client.POST("/api/v1/archive/notes", { body, headers: await csrfHeaders() }));
}
export async function promoteArchiveNote(recordId: string, body: components["schemas"]["ArchiveLifecycleIntent"]): Promise<components["schemas"]["NoteRecord"]> {
  return unwrap(await client.POST("/api/v1/archive/notes/{record_id}/promote", {
    params: { path: { record_id: recordId } }, body, headers: await csrfHeaders()
  }));
}
export async function revokeArchiveNote(recordId: string, body: components["schemas"]["ArchiveLifecycleIntent"]): Promise<components["schemas"]["NoteRecord"]> {
  return unwrap(await client.POST("/api/v1/archive/notes/{record_id}/revoke", {
    params: { path: { record_id: recordId } }, body, headers: await csrfHeaders()
  }));
}

export async function getNaming(signal?: AbortSignal): Promise<components["schemas"]["NamingView"]> {
  return unwrap(await client.GET("/api/v1/altar/naming", { signal }));
}

export async function acceptNaming(
  body: components["schemas"]["NamingAcceptance"], signal?: AbortSignal
): Promise<components["schemas"]["NamingView"]> {
  return unwrap(await client.PUT("/api/v1/altar/naming", {
    body, signal, headers: await csrfHeaders()
  }));
}

export async function getNamingSuggestions(signal?: AbortSignal): Promise<components["schemas"]["NameSuggestions"]> {
  return unwrap(await client.GET("/api/v1/altar/naming/suggestions", { signal }));
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

export async function createCanvasProject(data: CanvasProjectCreate): Promise<AtlasProject> {
  return unwrap(await client.POST("/api/v1/canvas/projects", {
    body: data,
    headers: await csrfHeaders()
  }));
}

export async function bootstrapCanvasWorkspace(): Promise<AtlasProject> {
  return unwrap(await client.POST("/api/v1/canvas/workspace/bootstrap", {
    headers: await csrfHeaders()
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

export async function getBridgeSessions(cursor?: string, signal?: AbortSignal): Promise<SessionPage> {
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

export async function decideConsent(
  consentId: string,
  verdict: components["schemas"]["ConsentDecisionIntent"]["verdict"],
  reviewBindingDigest?: components["schemas"]["ConsentDecisionIntent"]["review_binding_digest"]
) {
  return unwrap(
    await client.POST("/api/v1/bridge/consents/{consent_id}/decision", {
      params: { path: { consent_id: consentId } },
      body: {
        verdict,
        ...(reviewBindingDigest === undefined ? {} : { review_binding_digest: reviewBindingDigest })
      },
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
  revision: string,
  binding?: InspectionSelection
): Promise<LoomView> {
  return unwrap(
    await client.GET("/api/v1/loom/{pattern_id}/{revision}", {
      params: { path: { pattern_id: patternId, revision }, query: binding ? { source_id: binding.source_id, generation: binding.source_generation, profile_id: binding.profile_id, profile_revision: binding.profile_revision } : undefined }
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

// Native EventSource keeps delivering while an authoritative snapshot is pending.
const MAX_PENDING_RUN_EVENTS = 256;

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
  const pending: ReturnType<typeof runEventEnvelopeSchema.parse>[] = [];
  let draining = false;
  let refetching = false;
  let stopped = false;

  function close() {
    if (stopped) return;
    stopped = true;
    pending.length = 0;
    source.close();
  }

  function fault(message: string) {
    if (stopped) return;
    close();
    try {
      options.onHardClose?.(message);
    } finally {
      onFault(message);
    }
  }

  async function drain() {
    if (draining || stopped) return;
    draining = true;
    try {
      while (!stopped && pending.length) {
        const event = pending.shift()!;
        const disposition = reduceRunEventCursor(cursor, event);
        cursor = disposition.cursor;
        if (disposition.refetch) {
          refetching = true;
          const snapshot = await onRefetch();
          if (stopped) return;
          cursor = initialRunEventCursor(snapshot.cursor);
          refetching = false;
          if (snapshot.terminal) close();
        } else if (disposition.deliver) {
          onEvent(event);
        }
        if (event.kind === "done") close();
      }
    } catch {
      fault("The authoritative run snapshot could not be refreshed.");
    } finally {
      draining = false;
      refetching = false;
    }
  }

  for (const kind of kinds) {
    source.addEventListener(kind, (raw) => {
      if (stopped) return;
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

      if (pending.length >= MAX_PENDING_RUN_EVENTS) {
        fault("The run stream exceeded its pending event limit; its projection may be stale.");
        return;
      }
      pending.push(event);
      void drain();
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
  return close;
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
    if (stopped) return;
    if (source.readyState === EventSource.CLOSED) {
      fault("The transition stream closed; its projection may be stale.");
    } else onFault("The transition stream went quiet.");
  };
  return () => {
    stopped = true;
    source.close();
  };
}
