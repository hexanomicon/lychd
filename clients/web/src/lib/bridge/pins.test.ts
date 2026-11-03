import { describe, expect, it } from "vitest";
import {
  parsePinnedConversations,
  togglePinnedConversation
} from "./pins";

describe("Bridge pinned conversation preferences", () => {
  it.each([null, "", "not-json", "[", "null", "true", "42", '"session-a"'])
    ("rejects absent, malformed, and non-array storage: %s", (raw) => {
      expect(parsePinnedConversations(raw)).toEqual([]);
    });

  it.each([
    { "session-a": true },
    { pins: ["session-a"], title: "private title", body: "private body", draft: "private draft" },
    ["session-a", { id: "session-b", draft: "private draft" }],
    ["session-a", ["session-b"]],
    ["session-a", null],
    ["session-a", 12],
    ["session-a", true]
  ].map((value) => ({ value })))
    ("rejects the entire stored shape instead of recovering content fields: %j", ({ value }) => {
      expect(parsePinnedConversations(JSON.stringify(value))).toEqual([]);
    });

  it.each([
    "", " session-a", "session-a ", "session-a\n", "session-a\r", "../session-a",
    "/bridge/session-a", "session-a?draft=private", "session%2Da", "séance-a", "a".repeat(129)
  ])("rejects every pin when one identity is invalid: %j", (id) => {
    expect(parsePinnedConversations(JSON.stringify(["session-before", id, "session-after"]))).toEqual([]);
  });

  it("preserves exact identities and first occurrence order without duplicates", () => {
    const longestId = "a".repeat(128);
    expect(parsePinnedConversations(JSON.stringify([
      "Session-c._~-", "session-a", "Session-c._~-", longestId, "session-a"
    ]))).toEqual(["Session-c._~-", "session-a", longestId]);
    expect(parsePinnedConversations("[]")).toEqual([]);
  });

  it("bounds raw storage before parsing even when excess characters are whitespace", () => {
    const raw = JSON.stringify(["session-a"]);
    expect(parsePinnedConversations(raw.padEnd(8192, " "))).toEqual(["session-a"]);
    expect(parsePinnedConversations(raw.padEnd(8193, " "))).toEqual([]);
  });

  it("rejects more than 32 entries before deduplication", () => {
    const current = Array.from({ length: 32 }, (_, index) => `session-${index}`);
    expect(parsePinnedConversations(JSON.stringify(current))).toEqual(current);
    expect(parsePinnedConversations(JSON.stringify([...current, "session-extra"]))).toEqual([]);
    expect(parsePinnedConversations(JSON.stringify(Array(33).fill("session-a")))).toEqual([]);
  });

  it("adds and removes pins without mutating the input or changing other identities", () => {
    const current = Object.freeze(["session-b", "session-a"]);
    const added = togglePinnedConversation(current, "session-c");
    expect(added).toEqual(["session-b", "session-a", "session-c"]);
    expect(added).not.toBe(current);
    expect(togglePinnedConversation(current, "session-b")).toEqual(["session-a"]);
    expect(current).toEqual(["session-b", "session-a"]);
  });

  it.each(["", " session-a", "session-a\n", "../session-a", "session-a?body=private", "a".repeat(129)])
    ("refuses to toggle an invalid identity: %j", (id) => {
      const current = Object.freeze(["session-a"]);
      expect(togglePinnedConversation(current, id)).toBe(current);
    });

  it("keeps a full preference unchanged for additions but permits removal and replacement", () => {
    const current = Object.freeze(Array.from({ length: 32 }, (_, index) => `session-${index}`));
    expect(togglePinnedConversation(current, "session-extra")).toBe(current);
    const removed = togglePinnedConversation(current, "session-0");
    expect(removed).toEqual(current.slice(1));
    expect(togglePinnedConversation(removed, "session-extra")).toEqual([...current.slice(1), "session-extra"]);
    expect(current).toHaveLength(32);
  });
});
