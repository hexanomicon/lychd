import { act, cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import OrbTimeline from "./OrbTimeline.svelte";
import { appendFieldFrame, type FieldFrame } from "$lib/orb/field-history";
import { fixtureRun, pattern } from "$lib/orb/__fixtures__/snapshot";

function history(): readonly FieldFrame[] {
  const snapshot = fixtureRun("run-a");
  const first = appendFieldFrame([], [snapshot.run], new Map([[snapshot.run.run_id, { snapshot, pattern }]]), 1000, 90);
  const changed = { ...snapshot, run: { ...snapshot.run, status: "done" } };
  const second = appendFieldFrame(first, [changed.run], new Map([[snapshot.run.run_id, { snapshot: changed, pattern }]]), 2000, 90);
  return appendFieldFrame(second, [changed.run], new Map(), 4000, 90);
}

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("Orb tab timeline", () => {
  it("labels actual tab coverage, transport and repeated workflow identities", () => {
    const frames = history();
    const duplicate = fixtureRun("run-b").run;
    const expanded = appendFieldFrame(frames, [...frames.at(-1)!.runs, duplicate], frames.at(-1)!.lenses, 5000, 90);
    render(OrbTimeline, { frames: expanded, cursorId: null, onseeking: vi.fn(), onlive: vi.fn(), connectionLabel: "closed · stale", windowSeconds: 3600 });
    expect(screen.getByText("observed updates · cleared on reload")).toBeTruthy();
    expect(screen.getByText("4 captures · 4.0s available")).toBeTruthy();
    expect(screen.getByText(/closed · stale/)).toBeTruthy();
    expect(screen.getByRole("group", { name: "review · run-a observed updates" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "review · run-b observed updates" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "Tab history retention window" }).getAttribute("disabled")).not.toBeNull();
  });

  it("requests pause, floor seeks, stepping and LIVE only through public callbacks", async () => {
    const frames = history();
    const onseeking = vi.fn(), onlive = vi.fn(), onpause = vi.fn(), onwindowchange = vi.fn();
    const view = render(OrbTimeline, { frames, cursorId: null, onseeking, onlive, onpause, onwindowchange });
    await fireEvent.click(screen.getByRole("button", { name: "Pause live field" }));
    expect(onpause).toHaveBeenCalledOnce();
    await fireEvent.input(screen.getByRole("slider", { name: "Seek tab observation time" }), { target: { value: "1999" } });
    expect(onseeking).toHaveBeenLastCalledWith(2);
    await view.rerender({ cursorId: 2 });
    await fireEvent.click(screen.getByRole("button", { name: "Previous capture" }));
    expect(onseeking).toHaveBeenLastCalledWith(1);
    await fireEvent.click(screen.getByRole("button", { name: "Next capture" }));
    expect(onseeking).toHaveBeenLastCalledWith(3);
    await fireEvent.change(screen.getByRole("combobox", { name: "Tab history retention window" }), { target: { value: "30" } });
    expect(onwindowchange).toHaveBeenCalledWith(30);
    await fireEvent.click(screen.getByRole("button", { name: "LIVE" }));
    expect(onlive).toHaveBeenCalledOnce();
  });


  it("holds pointer seek bounds during incoming captures and releases on pointer end or blur", async () => {
    const frames = history();
    const run = frames.at(-1)!.runs[0]!;
    const expanded = appendFieldFrame(frames, [{ ...run, status: "updated" }], new Map(), 6000, 90);
    const onseeking = vi.fn(), onpause = vi.fn();
    const view = render(OrbTimeline, { frames, cursorId: null, onseeking, onlive: vi.fn(), onpause });
    const slider = screen.getByRole("slider", { name: "Seek tab observation time" });
    await fireEvent.pointerDown(slider);
    expect(onpause).toHaveBeenCalledOnce();
    await view.rerender({ frames: expanded });
    expect(slider.getAttribute("min")).toBe("0");
    expect(slider.getAttribute("max")).toBe("3000");
    await fireEvent.input(slider, { target: { value: "2000" } });
    expect(onseeking).toHaveBeenLastCalledWith(2);
    await fireEvent.pointerUp(window);
    expect(slider.getAttribute("max")).toBe("5000");
    await fireEvent.keyDown(slider, { key: "ArrowRight" });
    await fireEvent.input(slider, { target: { value: "5000" } });
    expect(onseeking).toHaveBeenLastCalledWith(4);
    for (const finish of [() => fireEvent.pointerCancel(window), () => fireEvent.blur(slider)]) {
      await view.rerender({ frames });
      await fireEvent.pointerDown(slider);
      await view.rerender({ frames: expanded });
      expect(slider.getAttribute("max")).toBe("3000");
      await finish();
      expect(slider.getAttribute("max")).toBe("5000");
    }
  });

  it("never resurrects evicted captures during a drag and discards bounds on authority clear", async () => {
    const frames = history();
    const run = frames.at(-1)!.runs[0]!;
    const current = appendFieldFrame(frames, [{ ...run, status: "updated" }], new Map(), 6000, 90).slice(-1);
    const onseeking = vi.fn();
    const view = render(OrbTimeline, { frames, cursorId: 1, onseeking, onlive: vi.fn() });
    const slider = screen.getByRole("slider", { name: "Seek tab observation time" });
    await fireEvent.pointerDown(slider);
    await view.rerender({ frames: current });
    expect(screen.getByText("Pinned capture outside window")).toBeTruthy();
    expect(onseeking).not.toHaveBeenCalled();
    expect(slider.getAttribute("min")).toBe("0");
    expect(slider.getAttribute("max")).toBe("3000");
    await fireEvent.input(slider, { target: { value: "0" } });
    expect(onseeking).toHaveBeenLastCalledWith(4);
    await view.rerender({ frames: [] });
    expect(slider.getAttribute("min")).toBe("0");
    expect(slider.getAttribute("max")).toBe("0");
    await view.rerender({ frames: current });
    expect(slider.getAttribute("min")).toBe("0");
    expect(slider.getAttribute("max")).toBe("0");
  });

  it("keeps an evicted pinned capture explicit until an operator chooses another", async () => {
    const onseeking = vi.fn();
    render(OrbTimeline, { frames: history().slice(1), cursorId: 1, onseeking, onlive: vi.fn() });
    expect(screen.getByText("Pinned capture outside window")).toBeTruthy();
    expect(onseeking).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole("button", { name: "Next capture" }));
    expect(onseeking).toHaveBeenCalledWith(2);
  });

  it("plays actual receipt gaps at selected speed, stops at last capture and cleans timers", async () => {
    vi.useFakeTimers();
    const frames = history();
    const seek = vi.fn((id: number) => { void view.rerender({ cursorId: id }); });
    const view = render(OrbTimeline, { frames, cursorId: 1, onseeking: seek, onlive: vi.fn() });
    await fireEvent.change(screen.getByRole("combobox", { name: "Playback speed" }), { target: { value: "2" } });
    await fireEvent.click(screen.getByRole("button", { name: "Play captured updates" }));
    await act(() => vi.advanceTimersByTime(499));
    expect(seek).toHaveBeenLastCalledWith(1);
    await act(() => vi.advanceTimersByTime(1));
    expect(seek).toHaveBeenLastCalledWith(2);
    await act(() => vi.advanceTimersByTime(1000));
    expect(seek).toHaveBeenLastCalledWith(3);
    expect(screen.getByRole("button", { name: "Play captured updates" })).toBeTruthy();
    expect(vi.getTimerCount()).toBe(0);
    await fireEvent.click(screen.getByRole("button", { name: "Play captured updates" }));
    expect(vi.getTimerCount()).toBe(1);
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("cancels pending playback when cursor changes externally or its capture is evicted", async () => {
    vi.useFakeTimers();
    const frames = history();
    const seek = vi.fn();
    const view = render(OrbTimeline, { frames, cursorId: 1, onseeking: seek, onlive: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: "Play captured updates" }));
    expect(vi.getTimerCount()).toBe(1);
    await view.rerender({ cursorId: null });
    expect(vi.getTimerCount()).toBe(0);
    await act(() => vi.advanceTimersByTime(5000));
    expect(seek).toHaveBeenCalledTimes(1);
    await view.rerender({ cursorId: 1 });
    await fireEvent.click(screen.getByRole("button", { name: "Play captured updates" }));
    await view.rerender({ frames: frames.slice(1) });
    expect(vi.getTimerCount()).toBe(0);
    await act(() => vi.advanceTimersByTime(5000));
    expect(seek).toHaveBeenCalledTimes(2);
  });
});
