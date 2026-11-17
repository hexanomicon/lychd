import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { describe, expect, it, vi } from "vitest";

import Button from "./Button.svelte";
import Disclosure from "./Disclosure.svelte";
import FaultNotice from "./FaultNotice.svelte";
import InspectorLinks from "./InspectorLinks.svelte";
import InspectorPanel from "./InspectorPanel.svelte";
import InspectorSection from "./InspectorSection.svelte";
import KeyValueList from "./KeyValueList.svelte";
import LoadingState from "./LoadingState.svelte";
import SegmentedControl from "./SegmentedControl.svelte";
import StatusPill from "./StatusPill.svelte";

const text = (value: string) => createRawSnippet(() => ({ render: () => `<span>${value}</span>` }));

describe("Button", () => {
  it("disables and announces busy work, and defaults to type=button", () => {
    render(Button, { busy: true, children: text("Refresh") });
    const button = screen.getByRole("button", { name: "Refresh" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect(button.type).toBe("button");
  });

  it("renders a link when given an href", () => {
    render(Button, { href: "/atlas", variant: "primary", children: text("Open Atlas") });
    expect(screen.getByRole("link", { name: "Open Atlas" }).getAttribute("href")).toBe("/atlas");
  });
});

describe("StatusPill", () => {
  it("keeps the dot decorative so text carries the meaning", () => {
    const { container } = render(StatusPill, { tone: "attention", dot: true, children: text("1 awaiting consent") });
    expect(screen.getByText("1 awaiting consent")).toBeTruthy();
    expect(container.querySelector(".status-pill__dot")?.getAttribute("aria-hidden")).toBe("true");
    expect(container.querySelector(".status-pill")?.getAttribute("data-tone")).toBe("attention");
  });
});

describe("FaultNotice", () => {
  it("puts the live role on the message and offers a busy-aware retry", async () => {
    const onretry = vi.fn();
    const view = render(FaultNotice, { message: "The Altar cannot be reached.", onretry, id: "fault" });
    expect(screen.getByRole("alert").id).toBe("fault");
    await fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onretry).toHaveBeenCalledOnce();
    await view.rerender({ message: "The Altar cannot be reached.", onretry, retrying: true });
    expect((screen.getByRole("button", { name: "Retrying…" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("uses a polite status for soft notices", () => {
    render(FaultNotice, { message: "Link unavailable.", severity: "status" });
    expect(screen.getByRole("status").textContent).toBe("Link unavailable.");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("LoadingState", () => {
  it("labels the wait and hides the mist from assistive technology", () => {
    const { container } = render(LoadingState, { label: "Loading conversation…", lines: 3 });
    expect(screen.getByRole("status").textContent).toBe("Loading conversation…");
    const mist = container.querySelectorAll(".mist");
    expect(mist).toHaveLength(3);
    expect([...mist].every((bar) => bar.getAttribute("aria-hidden") === "true")).toBe(true);
  });
});

describe("SegmentedControl", () => {
  it("exposes a labelled group of pressed toggles and reports changes", async () => {
    const onchange = vi.fn();
    render(SegmentedControl, {
      label: "Graph level",
      options: [{ value: "pattern", label: "Whole Pattern" }, { value: "stations", label: "Stations", count: 4 }],
      value: "pattern",
      onchange
    });
    const group = screen.getByRole("group", { name: "Graph level" });
    const stations = within(group).getByRole("button", { name: /^Stations/ });
    expect(within(group).getByRole("button", { name: "Whole Pattern" }).getAttribute("aria-pressed")).toBe("true");
    expect(stations.getAttribute("aria-pressed")).toBe("false");
    await fireEvent.click(stations);
    expect(onchange).toHaveBeenCalledWith("stations");
    expect(stations.getAttribute("aria-pressed")).toBe("true");
  });
});

describe("Disclosure", () => {
  it("closes a popover on Escape and returns focus to its summary", async () => {
    render(Disclosure, { variant: "popover", open: true, summary: text("Tools"), children: text("Naming ceremony") });
    const details = screen.getByText("Tools").closest("details")!;
    expect(details.open).toBe(true);
    await fireEvent.keyDown(window, { key: "Escape" });
    expect(details.open).toBe(false);
    expect(document.activeElement).toBe(details.querySelector("summary"));
  });

  it("leaves an in-place section open on Escape", async () => {
    render(Disclosure, { open: true, summary: text("Graph outline"), children: text("Stations") });
    await fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByText("Graph outline").closest("details")!.open).toBe(true);
  });
});

describe("KeyValueList", () => {
  it("renders plain facts as term and description pairs", () => {
    const { container } = render(KeyValueList, { label: "Run identity", items: [{ term: "Run", value: "run_a", glyph: true }, { term: "Sigil", value: "Local · Magus" }] });
    const list = screen.getByLabelText("Run identity");
    expect([...list.querySelectorAll("dt")].map((term) => term.textContent)).toEqual(["Run", "Sigil"]);
    expect(container.querySelector("dd.glyph")?.textContent).toBe("run_a");
  });
});

describe("Inspector", () => {
  it("names the landmark by its title and offers an optional dismiss", async () => {
    const ondismiss = vi.fn();
    render(InspectorPanel, { title: "Selected station", eyebrow: "Loom", ondismiss, children: text("Body") });
    expect(screen.getByRole("complementary", { name: "Selected station" })).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Close inspector" }));
    expect(ondismiss).toHaveBeenCalledOnce();
  });

  it("labels a titled section by its heading", () => {
    render(InspectorSection, { title: "Incoming permissions", meta: "0", children: text("None") });
    expect(screen.getByRole("region", { name: "Incoming permissions" })).toBeTruthy();
  });

  it("skips links whose targets are unavailable", () => {
    render(InspectorLinks, { label: "Run inspection", links: [{ href: null, label: "Open score in Loom" }, { href: "/orb/run_a", label: "Inspect Run in Orb" }] });
    const nav = screen.getByRole("navigation", { name: "Run inspection" });
    expect(within(nav).getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual(["/orb/run_a"]);
  });
});
