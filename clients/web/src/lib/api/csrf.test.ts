import { describe, expect, it } from "vitest";

import { csrfHeadersFromCookie } from "./csrf";

describe("configured CSRF browser contract", () => {
  it("reads the backend-named cookie and emits the backend-named header", () => {
    const headers = csrfHeadersFromCookie(
      { cookie_name: "lychd-ward", header_name: "x-lychd-ward" },
      "csrftoken=stale; lychd-ward=live%20token"
    );

    expect(headers).toEqual({ "x-lychd-ward": "live token" });
  });

  it("does not invent a header when the configured cookie is absent", () => {
    expect(
      csrfHeadersFromCookie(
        { cookie_name: "lychd-ward", header_name: "x-lychd-ward" },
        "csrftoken=unrelated"
      )
    ).toEqual({});
  });
});
