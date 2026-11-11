import { render, screen, within } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import { coldPreferredRoute } from "$lib/orb/__fixtures__/preference";
import BridgePreferenceSummary from "./BridgePreferenceSummary.svelte";

afterEach(() => vi.unstubAllGlobals());

describe("Routing preference admission observation", () => {
  it("shows the supplied selection despite a higher cold preference and explains its retained scope", () => {
    const view = render(BridgePreferenceSummary, { summary: coldPreferredRoute });
    const region = screen.getByRole("region", { name: "Routing preference" });
    const table = within(region).getByRole("table", { name: "Routes observed at admission" });
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(within(table).getByRole("columnheader", { name: "Preference (unitless)" })).toBeTruthy();
    const cold = within(table).getByRole("row", { name: /local-preferred:chat:model-a/ });
    expect(within(cold).getByText("1000")).toBeTruthy();
    expect(within(cold).getByText("Cold")).toBeTruthy();
    expect(within(cold).getByText("Not warm")).toBeTruthy();
    expect(within(cold).queryByText("Selected at admission")).toBeNull();
    const selected = within(table).getByRole("row", { name: /local-ready:chat:model-b/ });
    expect(within(selected).getByText("Selected at admission")).toBeTruthy();
    expect(within(region).getByText(/immutable admission observation.*Later readiness may differ/)).toBeTruthy();
    expect(within(region).getByText(/Settings affect new admissions.*Replay and restart.*fallback is unavailable/)).toBeTruthy();
    expect(within(region).getByText(coldPreferredRoute.policy_digest)).toBeTruthy();
    expect(region.querySelector('time[datetime="2026-10-17T12:00:00Z"]')).toBeTruthy();
    expect(region.querySelector('time[datetime="2026-10-17T12:00:01Z"]')).toBeTruthy();
    view.unmount();
  });

  it("replaces supplied weights, selection and identity details on rerender", async () => {
    const view = render(BridgePreferenceSummary, { summary: coldPreferredRoute });
    await view.rerender({ summary: { ...coldPreferredRoute, policy_digest: "b".repeat(64),
      selected_capability_key: "local-preferred:chat:model-a",
      routes: coldPreferredRoute.routes.map((route) => ({ ...route,
        weight: route.capability_key === "local-preferred:chat:model-a" ? 5 : 1,
        phase: "warm", exclusion_code: null
      }))
    } });
    const table = screen.getByRole("table");
    const selected = within(table).getByRole("row", { name: /local-preferred:chat:model-a/ });
    expect(within(selected).getByText("5")).toBeTruthy();
    expect(within(selected).getByText("Selected at admission")).toBeTruthy();
    expect(within(table).getByRole("row", { name: /local-ready:chat:model-b/ }).textContent).not.toContain("Selected at admission");
    expect(screen.queryByText("1000")).toBeNull();
    expect(screen.queryByText(coldPreferredRoute.policy_digest)).toBeNull();
    expect(screen.getByText("b".repeat(64))).toBeTruthy();
    view.unmount();
  });

  it("labels omitted observations for a disabled route and preserves long canonical keys without fetching", () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const longKey = "long-route:chat:" + "model-".repeat(80);
    const view = render(BridgePreferenceSummary, { summary: { ...coldPreferredRoute,
      routes: [{ ...coldPreferredRoute.routes[0]!, capability_key: longKey, weight: 0,
        phase: null, observed_at: null, admission_open: false, exclusion_code: "disabled" }, coldPreferredRoute.routes[1]!]
    } });
    const row = screen.getByRole("row", { name: new RegExp(longKey) });
    expect(within(row).getByRole("rowheader", { name: longKey })).toBeTruthy();
    expect(within(row).getByText("No retained observation")).toBeTruthy();
    expect(within(row).getByText("Disabled · ineligible")).toBeTruthy();
    expect(within(row).getByText("No retained observation time")).toBeTruthy();
    const scrollRegion = screen.getByRole("region", { name: "Routing preference routes" });
    scrollRegion.focus(); expect(document.activeElement).toBe(scrollRegion);
    expect(fetch).not.toHaveBeenCalled();
    view.unmount();
  });

  it("renders nothing for a legacy absent observation or a cleared summary", async () => {
    const view = render(BridgePreferenceSummary, { summary: undefined });
    expect(screen.queryByRole("region", { name: "Routing preference" })).toBeNull();
    await view.rerender({ summary: coldPreferredRoute });
    expect(screen.getByRole("region", { name: "Routing preference" })).toBeTruthy();
    await view.rerender({ summary: null });
    expect(screen.queryByRole("region", { name: "Routing preference" })).toBeNull();
    view.unmount();
  });
});
