import type { InspectionBinding } from "./models";

export type InspectionSelection = Pick<InspectionBinding, "source_id" | "source_generation" | "profile_id" | "profile_revision">;
const fields = ["source_id", "generation", "profile_id", "profile_revision"] as const;
const identifier = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

export function inspectionSelection(search: string): { binding?: InspectionSelection; error?: string } {
  const params = new URLSearchParams(search);
  if (!fields.some(field => params.has(field))) return {};
  if (!fields.every(field => params.getAll(field).length === 1 && identifier.test(params.get(field)!))) {
    return { error: "Inspection context unavailable — source, generation and exact profile must all be supplied once." };
  }
  return { binding: { source_id: params.get("source_id")!, source_generation: params.get("generation")!,
    profile_id: params.get("profile_id")!, profile_revision: params.get("profile_revision")! } };
}

export function sameInspectionBinding(left: InspectionSelection | undefined | null, right: InspectionSelection | undefined | null): boolean {
  if (!left || !right) return !left && !right;
  return left.source_id === right.source_id && left.source_generation === right.source_generation &&
    left.profile_id === right.profile_id && left.profile_revision === right.profile_revision;
}

export function inspectionQuery(binding: InspectionSelection | undefined | null): string {
  return binding ? `?${new URLSearchParams({ source_id: binding.source_id, generation: binding.source_generation,
    profile_id: binding.profile_id, profile_revision: binding.profile_revision })}` : "";
}
