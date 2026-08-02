import { act, render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AltarStatus } from "$lib/api/models";

vi.mock("$app/state", () => ({
  page: { url: new URL("http://localhost/bridge") }
}));
vi.mock("$lib/api/client", () => ({
  getAltarStatus: vi.fn()
}));

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
    await act(() => refreshedStatus.resolve(status(1)));
    expect(screen.getByText(/1 awaiting/)).toBeTruthy();

    await act(() => initialStatus.resolve(status(0)));
    expect(screen.getByText(/1 awaiting/)).toBeTruthy();
    expect(screen.queryByText("Consent clear")).toBeNull();
    view.unmount();
  });
});
