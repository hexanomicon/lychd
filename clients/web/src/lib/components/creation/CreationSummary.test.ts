import { render, screen, within } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import { incompleteCreation } from "$lib/orb/__fixtures__/creation";
import CreationSummary from "./CreationSummary.svelte";

describe("Creation outcome", () => {
  it("explains an incomplete case without turning retained response into adoption", () => {
    const view = render(CreationSummary, { summary: incompleteCreation });
    const region = screen.getByRole("region", { name: "Creation outcome" });
    expect(within(region).getByText("incomplete")).toBeTruthy();
    expect(within(region).getByText("Retained · not adopted")).toBeTruthy();
    expect(within(region).getByText("No native verdict")).toBeTruthy();
    expect(within(region).getByText("No external assessment")).toBeTruthy();
    expect(within(region).getByText("No current decision")).toBeTruthy();
    expect(within(region).getByText("output bytes")).toBeTruthy();
    expect(within(region).getByText(/After the Run feed settles, use Refresh/)).toBeTruthy();
    view.unmount();
  });

  it("updates separate judgments and labels case-current feedback on a historical admission", async () => {
    const view = render(CreationSummary, { summary: incompleteCreation });
    await view.rerender({ summary: { ...incompleteCreation, admission_current: false,
      native_status: "accepted", native_disposition: "accepted", verdict_present: true,
      constructor_adopted: true, verifier_present: true, verifier_adopted: true, candidate_present: true,
      external_disposition: "partial", feedback_status: "hold",
      current_assessment_id: "595cd306-9780-4d1c-8da7-82c435484e22",
      current_decision_id: "43a159ef-e563-485f-a5f9-772b52bf59d7"
    } });
    const region = screen.getByRole("region", { name: "Creation outcome" });
    expect(within(region).getByText("partial")).toBeTruthy();
    expect(within(region).getByText("hold")).toBeTruthy();
    expect(within(region).queryByText("No native verdict")).toBeNull();
    expect(within(region).getByText(/Historical admission.*earlier attempt/)).toBeTruthy();
    await view.rerender({ summary: null });
    expect(screen.queryByRole("region", { name: "Creation outcome" })).toBeNull();
    expect(screen.queryByText(incompleteCreation.case_id)).toBeNull();
    expect(screen.getByText(/does not establish whether a case exists/)).toBeTruthy();
    view.unmount();
  });
});
