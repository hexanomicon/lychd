import { render, screen } from "@testing-library/svelte";
import { expect, it } from "vitest";
import type { OrbRunSnapshot } from "$lib/api/models";
import StationOutput from "./StationOutput.svelte";

const job: OrbRunSnapshot["delegated_jobs"][number] = {
  job_id: "job-local", request_id: "request", step_id: "dispatch_delegate",
  runtime:"reference",profile:"read",status:"succeeded", output_present:true,
  error_present:false,artifact_count:1,events_truncated:false,events:[]
};

it("keeps the latest AgentJob counters out of a historical output inspection", async () => {
  const view = render(StationOutput,{schema:'{"type":"string"}',jobs:[job],historical:true});
  expect(screen.getByRole("heading",{name:"Declared output schema"})).toBeTruthy();
  expect(screen.getByText(/Historical output values are unavailable/)).toBeTruthy();
  expect(screen.queryByText("job-local")).toBeNull();
  await view.rerender({schema:undefined,jobs:[job],historical:false});
  expect(screen.getByText("job-local")).toBeTruthy();
  expect(screen.queryByRole("heading",{name:"Declared output schema"})).toBeNull();
});
