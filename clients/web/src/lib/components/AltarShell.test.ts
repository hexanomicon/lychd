import { act, fireEvent, render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AltarStatus } from "$lib/api/models";

vi.mock("$app/state", async () => {
  const { SvelteURL } = await import("svelte/reactivity");
  return { page: { url: new SvelteURL("http://localhost/bridge") } };
});
vi.mock("$app/navigation", () => ({ goto: vi.fn(), replaceState: vi.fn(), beforeNavigate: vi.fn(), afterNavigate: vi.fn() }));
vi.mock("$lib/api/client", () => ({
  getBridgeSnapshot: vi.fn(() => new Promise(() => {})),
  getAltarStatus: vi.fn()
}));

import { page } from "$app/state";
import { getAltarStatus } from "$lib/api/client";
import AltarShell from "./AltarShell.svelte";

const children = createRawSnippet(() => ({ render: () => "<p>Instrument</p>" }));

function status(pendingConsents: number): AltarStatus {
  return {
    csrf: { cookie_name: "csrf", header_name: "X-CSRF-Token" },
    pending_consents: pendingConsents
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((accept, decline) => {
    resolve = accept;
    reject = decline;
  });
  return { promise, reject, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  page.url.href = "http://localhost/bridge";
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Altar consent status", () => {
  it("does not report consent clear until status loads successfully", async () => {
    const pendingStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus).mockReturnValue(pendingStatus.promise);
    const view = render(AltarShell, { children });

    expect(screen.queryByText("Consent clear")).toBeNull();
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();

    await act(() => pendingStatus.resolve(status(0)));
    expect(screen.getByText(/Consent clear/)).toBeTruthy();
    view.unmount();
  });

  it("keeps consent unknown when status loading fails", async () => {
    const pendingStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus).mockReturnValue(pendingStatus.promise);
    const view = render(AltarShell, { children });

    await act(() => pendingStatus.reject(new Error("Status unavailable")));

    expect(screen.queryByText("Consent clear")).toBeNull();
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();
    expect(screen.getByText("Status unavailable")).toBeTruthy();
    view.unmount();
  });

  it("returns consent status to unknown when a refresh fails", async () => {
    vi.mocked(getAltarStatus)
      .mockResolvedValueOnce(status(0))
      .mockRejectedValueOnce(new Error("Refresh unavailable"));
    const view = render(AltarShell, { children });

    expect(await screen.findByText(/Consent clear/)).toBeTruthy();
    window.dispatchEvent(new CustomEvent("altar:attention"));

    expect(await screen.findByText(/Consent status unknown/)).toBeTruthy();
    expect(screen.getByText("Refresh unavailable")).toBeTruthy();
    view.unmount();
  });

  it("treats consent events as invalidations and fences older status responses", async () => {
    const initialStatus = deferred<AltarStatus>();
    const refreshedStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus)
      .mockReturnValueOnce(initialStatus.promise)
      .mockReturnValueOnce(refreshedStatus.promise);
    const view = render(AltarShell, { children });

    window.dispatchEvent(new CustomEvent("altar:attention", { detail: 0 }));
    window.dispatchEvent(new CustomEvent("altar:attention", { detail: 0 }));
    expect(getAltarStatus).toHaveBeenCalledOnce();

    await act(() => initialStatus.resolve(status(0)));
    expect(getAltarStatus).toHaveBeenCalledTimes(2);
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();
    await act(() => refreshedStatus.resolve(status(1)));
    expect(screen.getByText(/1 awaiting/)).toBeTruthy();
    expect(screen.queryByText("Consent clear")).toBeNull();
    view.unmount();
  });

  it("refreshes consent across instruments without overlapping reads or showing a stale clear status", async () => {
    vi.useFakeTimers();
    const refreshedStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus)
      .mockResolvedValueOnce(status(0))
      .mockReturnValueOnce(refreshedStatus.promise);
    const view = render(AltarShell, { children });
    await act(() => Promise.resolve());
    expect(screen.getByText(/Consent clear/)).toBeTruthy();

    await act(() => { page.url.href = "http://localhost/loom"; });
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(getAltarStatus).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(/Consent clear/)).toBeNull();
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();
    await act(() => vi.advanceTimersByTimeAsync(15000));
    expect(getAltarStatus).toHaveBeenCalledTimes(2);

    await act(() => refreshedStatus.resolve(status(2)));
    expect(screen.getByRole("link", { name: /2 awaiting/ }).getAttribute("href"))
      .toBe("/bridge?attention=pending");
    view.unmount();
  });

  it("ignores hidden-tab responses and wakes consent reads on visibility and focus", async () => {
    vi.useFakeTimers();
    let visibility: DocumentVisibilityState = "visible";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility);
    const initialStatus = deferred<AltarStatus>();
    const visibleStatus = deferred<AltarStatus>();
    const focusedStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus)
      .mockReturnValueOnce(initialStatus.promise)
      .mockReturnValueOnce(visibleStatus.promise)
      .mockReturnValueOnce(focusedStatus.promise);
    const view = render(AltarShell, { children });

    visibility = "hidden";
    await act(() => document.dispatchEvent(new Event("visibilitychange")));
    await act(() => initialStatus.resolve(status(0)));
    await act(() => window.dispatchEvent(new Event("focus")));
    await act(() => vi.advanceTimersByTimeAsync(15000));
    expect(getAltarStatus).toHaveBeenCalledOnce();
    expect(screen.queryByText(/Consent clear/)).toBeNull();

    visibility = "visible";
    await act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(getAltarStatus).toHaveBeenCalledTimes(2);
    await act(() => visibleStatus.resolve(status(1)));
    expect(screen.getByText(/1 awaiting/)).toBeTruthy();

    await act(() => window.dispatchEvent(new Event("focus")));
    expect(getAltarStatus).toHaveBeenCalledTimes(3);
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();
    await act(() => focusedStatus.resolve(status(2)));
    expect(screen.getByText(/2 awaiting/)).toBeTruthy();
    view.unmount();
  });

  it("keeps failed polls unknown without repeating the same notice and recovers on a later poll", async () => {
    vi.useFakeTimers();
    vi.mocked(getAltarStatus)
      .mockResolvedValueOnce(status(0))
      .mockRejectedValueOnce(new Error("Status unavailable"))
      .mockRejectedValueOnce(new Error("Status unavailable"))
      .mockResolvedValueOnce(status(1));
    page.url.href = "http://localhost/orb";
    const view = render(AltarShell, { children });
    await act(() => Promise.resolve());

    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(screen.queryByText(/Consent clear/)).toBeNull();
    expect(screen.getByText(/Consent status unknown/)).toBeTruthy();
    expect(screen.getAllByText("Status unavailable")).toHaveLength(1);
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(screen.getByText(/1 awaiting/)).toBeTruthy();
    view.unmount();
  });

  it("stops timers, queued reads, and wake listeners when the shell unmounts", async () => {
    vi.useFakeTimers();
    const delayedStatus = deferred<AltarStatus>();
    vi.mocked(getAltarStatus)
      .mockResolvedValueOnce(status(0))
      .mockReturnValueOnce(delayedStatus.promise);
    const view = render(AltarShell, { children });
    await act(() => Promise.resolve());
    await act(() => vi.advanceTimersByTimeAsync(5000));
    window.dispatchEvent(new CustomEvent("altar:attention"));
    view.unmount();

    await act(() => delayedStatus.resolve(status(1)));
    window.dispatchEvent(new CustomEvent("altar:attention"));
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
    await act(() => vi.advanceTimersByTimeAsync(15000));
    expect(getAltarStatus).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
  });
});


describe("shell contextual navigation", () => {
  it("opens the parallel Run field across instrument switches", async () => {
    vi.mocked(getAltarStatus).mockResolvedValue(status(1));
    page.url.href = "http://localhost/orb/run-a?event=event-a";
    const view = render(AltarShell, { children });
    await act(() => Promise.resolve());
    expect(screen.getByRole("link", { name: "Orb" }).getAttribute("href"))
      .toBe("/orb");
    await act(() => { page.url.search = "?event=event-b&job=job-a"; });
    await act(() => { page.url.href = "http://localhost/atlas/project-a"; });
    expect(screen.getByRole("link", { name: "Orb" }).getAttribute("href"))
      .toBe("/orb");
    await act(() => { page.url.href = "http://localhost/orb"; });
    expect(page.url.pathname).toBe("/orb");
    expect(screen.getByRole("link", { name: "Orb" }).getAttribute("href"))
      .toBe("/orb");
    expect(screen.getByRole("link", { name: /1 awaiting/ }).getAttribute("href"))
      .toBe("/bridge?attention=pending");
    view.unmount();
    page.url.href = "http://localhost/bridge";
    const newShell = render(AltarShell, { children });
    expect(screen.getByRole("link", { name: "Orb" }).getAttribute("href")).toBe("/orb");
    newShell.unmount();
  });
});

it("closes the About disclosure on Escape and restores focus to its trigger", async () => {
  vi.mocked(getAltarStatus).mockResolvedValue(status(0));
  const view = render(AltarShell, { children });
  const trigger = screen.getByLabelText("About LychD — The Altar");
  const disclosure = trigger.closest("details");
  if (!(disclosure instanceof HTMLDetailsElement)) {
    throw new Error("The About trigger must belong to a details disclosure.");
  }

  await fireEvent.click(trigger);
  expect(disclosure.open).toBe(true);
  const aboutLink = screen.getByRole("link", { name: __LYCHD_SOURCE_LABEL__ });
  aboutLink.focus();
  expect(document.activeElement).toBe(aboutLink);
  await fireEvent.keyDown(window, { key: "Escape" });

  expect(disclosure.open).toBe(false);
  expect(document.activeElement).toBe(trigger);
  view.unmount();
});

it("opens Applications by hover, pins a click, and keeps menu traversal and Escape reachable", async () => {
  vi.mocked(getAltarStatus).mockResolvedValue(status(0));
  const view = render(AltarShell, { children });
  const trigger = screen.getByText("Applications");
  const disclosure = trigger.closest("details")!;
  await fireEvent.pointerEnter(disclosure);
  expect(disclosure.open).toBe(true);
  await fireEvent.click(trigger);
  expect(disclosure.open).toBe(true);
  const canvas = screen.getByRole("link", { name: "Canvas" });
  canvas.focus();
  await fireEvent.pointerLeave(disclosure);
  expect(disclosure.open).toBe(true);
  expect(canvas.getAttribute("href")).toBe("/canvas");
  expect(screen.getByRole("link", { name: "Scavenger market" }).getAttribute("href")).toBe("/scavenger");
  await fireEvent.keyDown(window, { key: "Escape" });
  expect(disclosure.open).toBe(false);
  expect(document.activeElement).toBe(trigger.closest("summary"));
  view.unmount();
});
