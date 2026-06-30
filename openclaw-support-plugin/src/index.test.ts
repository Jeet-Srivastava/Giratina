import { afterEach, describe, expect, it, vi } from "vitest";
import entry, { callSupportApi, makeUrl } from "./index.js";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

describe("support-knowledge-claw", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("declares tool metadata", () => {
    expect(getToolPluginMetadata(entry)?.tools.map((tool) => tool.name)).toEqual([
      "eko_support_chat",
      "eko_claw_manifest",
      "eko_tool_contracts",
      "eko_update_ticket_status",
    ]);
  });

  it("builds support API URLs", () => {
    expect(makeUrl(undefined, "/api/claw/manifest")).toBe(
      "http://127.0.0.1:8000/api/claw/manifest",
    );
    expect(makeUrl("http://localhost:9000", "/api/chat")).toBe(
      "http://localhost:9000/api/chat",
    );
  });

  it("returns JSON from the support API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ workflow: ["classify_intent"] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(callSupportApi("http://127.0.0.1:8000/api/claw/manifest")).resolves.toEqual({
      workflow: ["classify_intent"],
    });
  });

  it("throws a useful error when the support API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("backend unavailable", { status: 503 })),
    );

    await expect(callSupportApi("http://127.0.0.1:8000/api/chat")).rejects.toThrow(
      "Support Knowledge Claw API failed (503): backend unavailable",
    );
  });
});
