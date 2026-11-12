import type { ObservationDocument, ObservationRequest } from "./observation";

export const admissionId = "00000000-0000-4000-8000-000000000001";
export const otherId = "00000000-0000-4000-8000-000000000002";
export const runId = "00000000-0000-4000-8000-000000000003";
export function request(): ObservationRequest {
  return { request_id: admissionId, initial_filter: { revision: "literal-casefold@1", query: "é" },
    seed: { schema_version: "CampaignSeed@1", subject_profile: "Technology@1", need: "Private need é",
      inventory: [], hard_criteria: [], preferences: [], budget_minor: null, currency: "EUR",
      deadline: "2099-01-01T00:00:00Z", region: null, evidence_standard: "Public title/link only",
      travel_delivery: "Not assessed", source_policy: "admitted-public-feed-only@1", disclosure_policy: "none",
      learning_mode: "none", operating_mode: "Watch" } };
}
export function field(): ObservationDocument {
  return { admission_id: admissionId, request_digest: "a".repeat(64), status: "observed", run_id: runId,
    run_status: "done", acquisition_status: "succeeded", terminal_disposition: "terminal", seed: request().seed,
    seed_document: JSON.stringify(request().seed),
    initial_filter: request().initial_filter, observation_digest: "b".repeat(64),
    observation: { schema_version: "MarketObservation@1", observation_id: admissionId, admission_id: admissionId,
      run_id: runId, seed_digest: "c".repeat(64), pattern_digest: "d".repeat(64), acquisition_binding_digest: "e".repeat(64),
      profile: "bazos-pc-title-link@1", acquisition_profile: "rss-public-feed@1", extractor: "scout-rss-extract@1",
      requested_url: "https://www.bazos.sk/rss.php?rub=pc", contacted_url: "https://www.bazos.sk/rss.php?rub=pc",
      acquired_at: "2026-10-18T00:00:00Z", scout_receipt_id: otherId, scout_receipt_digest: "f".repeat(64),
      source_digest: "1".repeat(64), record_digest: "2".repeat(64), omitted_elements: 4,
      coverage: "bounded-feed-response-only", items: [
        { ordinal: 0, title: "<img src=x onerror=alert(1)> É GPU", link: "https://pc.bazos.sk/inzerat/1/?x=1", duplicate_of: null },
        { ordinal: 1, title: null, link: "https://pc.bazos.sk/inzerat/1/?x=1", duplicate_of: 0 },
        { ordinal: 2, title: "Keyboard", link: "https://pc.bazos.sk/inzerat/2/", duplicate_of: null }
      ] },
    view: { observation_id: admissionId, observation_digest: "b".repeat(64), field_digest: "3".repeat(64),
      filter: request().initial_filter, casefold_unicode_version: "17.0.0", visible_ordinals: [0],
      total_count: 3, visible_count: 1, unmatched_count: 2, duplicate_count: 1, missing_title_count: 1 } };
}

export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
