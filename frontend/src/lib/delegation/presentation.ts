const STATUS_LABELS: Readonly<Record<string, string>> = {
  queued: "queued",
  admitted: "admitted",
  preparing: "preparing",
  running: "running",
  succeeded: "succeeded",
  failed: "failed",
  cancelled: "cancelled",
  timed_out: "timed out",
  lost: "lost"
};

export function delegationStatusLabel(status: string | null | undefined): string {
  if (!status) return "awaiting completion";
  return STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}
