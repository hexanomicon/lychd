import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import GenUI from "./GenUI.svelte";

describe("closed GenUI registry", () => {
  it("renders a validated checklist descriptor as text", () => {
    render(GenUI, {
      descriptor: {
        kind: "genui.plan_checklist",
        schema_version: 1,
        props: { title: "Rite", steps: ["Name the intent"] }
      }
    });
    expect(screen.getByText("Rite")).toBeTruthy();
    expect(screen.getByText("Name the intent")).toBeTruthy();
  });

  it("fails visibly for an unknown descriptor", () => {
    render(GenUI, {
      descriptor: { kind: "genui.not-admitted", schema_version: 1, props: {} }
    });
    expect(screen.getByText("Unknown projection")).toBeTruthy();
  });

  it.each([0, 2])("keeps descriptor schema %i inert", (schemaVersion) => {
    render(GenUI, {
      descriptor: {
        kind: "genui.plan_checklist",
        schema_version: schemaVersion,
        props: { title: "Invented legacy title", steps: ["Do not render"] }
      }
    });

    expect(screen.getByText("Unsupported projection")).toBeTruthy();
    expect(screen.queryByText("Invented legacy title")).toBeNull();
    expect(screen.queryByText("Do not render")).toBeNull();
  });
});
