import type { ObservationRequest } from "./observation";

export type ObservationDraft = {
  subject: "" | "Technology@1" | "Bazaar@1";
  need: string;
  inventory: string;
  criteria: string;
  preferences: Array<{ key: string; criterion: string; weight: string }>;
  budget: string;
  region: string;
  deadline: string;
  evidence: string;
  delivery: string;
  filter: string;
};

export function emptyObservationDraft(): ObservationDraft {
  return { subject: "", need: "", inventory: "", criteria: "", preferences: [], budget: "", region: "",
    deadline: "", evidence: "", delivery: "", filter: "" };
}

/** Input assistance only; the server owns complete validation and admission. */
export function prepareObservation(draft: ObservationDraft, id: string, now = Date.now()): {
  request: ObservationRequest | null; errors: string[];
} {
  const errors: string[] = [];
  const bytes = (value: string) => new TextEncoder().encode(value).length;
  const entries = (value: string) => value === "" ? [] : value.split(/\r?\n/).filter((line) => line.trim() !== "");
  const inventory = entries(draft.inventory), criteria = entries(draft.criteria);
  const preferences = draft.preferences.map((p) => ({ criterion: p.criterion, weight: Number(p.weight) }));
  if (!draft.subject) errors.push("Choose a subject profile.");
  if (!draft.need.trim() || bytes(draft.need) > 2048) errors.push("Need is required, up to 2048 UTF-8 bytes.");
  for (const [name, values] of [["Inventory", inventory], ["Hard criteria", criteria]] as const) {
    if (values.length > 16 || values.some((value) => bytes(value) > 1024)) errors.push(`${name}: at most 16 entries, each up to 1024 UTF-8 bytes.`);
  }
  if (preferences.length > 16 || preferences.some((p, i) => !p.criterion.trim() || bytes(p.criterion) > 1024 ||
      !/^\d+$/.test(draft.preferences[i]!.weight) || !Number.isSafeInteger(p.weight))) {
    errors.push("Preferences require a nonempty criterion and a nonnegative safe integer weight; at most 16.");
  }
  let budget: number | null = null;
  if (draft.budget !== "") {
    if (!/^\d+(?:\.\d{1,2})?$/.test(draft.budget)) errors.push("Budget must be empty (not assessed) or nonnegative EUR with at most two decimals.");
    else {
      const [whole = "", fraction = ""] = draft.budget.split(".");
      budget = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
      if (!Number.isSafeInteger(budget)) errors.push("Budget exceeds the supported exact integer range.");
    }
  }
  const deadline = new Date(draft.deadline);
  if (!draft.deadline || !Number.isFinite(deadline.getTime()) || deadline.getTime() <= now) errors.push("Choose a future deadline in your displayed local timezone.");
  if (draft.region !== "" && (!draft.region.trim() || bytes(draft.region) > 256)) errors.push("Region is empty (not assessed) or nonblank, up to 256 UTF-8 bytes.");
  if (!draft.evidence.trim() || bytes(draft.evidence) > 1024) errors.push("Supply an evidence standard, up to 1024 UTF-8 bytes.");
  if (!draft.delivery.trim() || bytes(draft.delivery) > 1024) errors.push("Supply travel/delivery facts, up to 1024 UTF-8 bytes.");
  if (bytes(draft.filter) > 256) errors.push("The literal filter permits 256 UTF-8 bytes.");
  if (errors.length || !draft.subject) return { request: null, errors };
  const request: ObservationRequest = { request_id: id, initial_filter: { revision: "literal-casefold@1", query: draft.filter },
    seed: { schema_version: "CampaignSeed@1", subject_profile: draft.subject, need: draft.need, inventory,
      hard_criteria: criteria, preferences, budget_minor: budget, currency: "EUR", deadline: deadline.toISOString(),
      region: draft.region || null, evidence_standard: draft.evidence, travel_delivery: draft.delivery,
      source_policy: "admitted-public-feed-only@1", disclosure_policy: "none", learning_mode: "none", operating_mode: "Watch" } };
  if (bytes(JSON.stringify(request.seed)) > 16 * 1024) errors.push("The complete seed exceeds 16 KiB.");
  return { request: errors.length ? null : request, errors };
}
