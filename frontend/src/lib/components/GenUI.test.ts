import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import GenUI from "./GenUI.svelte";

describe("closed GenUI registry", () => {
  it("renders a validated checklist descriptor as text", () => {
    render(GenUI, {
      descriptor: {
        kind: "genui.plan_checklist",
        props: { title: "Rite", steps: ["Name the intent"] }
      }
    });
    expect(screen.getByText("Rite")).toBeTruthy();
    expect(screen.getByText("Name the intent")).toBeTruthy();
  });

  it("fails visibly for an unknown descriptor", () => {
    render(GenUI, { descriptor: { kind: "genui.not-admitted", props: {} } });
    expect(screen.getByText("Unknown projection")).toBeTruthy();
  });
});
