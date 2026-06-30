import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const DEFAULT_API_BASE =
  process.env.SUPPORT_KNOWLEDGE_CLAW_API_BASE ?? "http://127.0.0.1:8000";

const apiBaseParameter = Type.Optional(
  Type.String({
    description:
      "Base URL for the Support Knowledge Claw FastAPI server.",
  }),
);

export async function callSupportApi(path: string, init?: RequestInit) {
  const response = await fetch(path, init);

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Support Knowledge Claw API failed (${response.status}): ${body}`,
    );
  }

  return response.json();
}

export function makeUrl(apiBase: string | undefined, path: string) {
  return new URL(path, apiBase ?? DEFAULT_API_BASE).toString();
}

export default defineToolPlugin({
  id: "support-knowledge-claw",
  name: "Support Knowledge Claw",
  description:
    "OpenClaw tools for the Eko Support Knowledge Claw automation workflow.",
  tools: (tool) => [
    tool({
      name: "eko_support_chat",
      description:
        "Run the Eko support agent for a retailer query. Creates or updates a persistent ticket and returns escalation details when needed.",
      parameters: Type.Object({
        query: Type.String({
          minLength: 1,
          description: "Retailer support query.",
        }),
        retailer_id: Type.Optional(
          Type.String({
            description:
              "Retailer identifier used for multi-turn memory and escalation history.",
          }),
        ),
        session_id: Type.Optional(
          Type.String({
            description:
              "Conversation/session identifier used for multi-turn memory.",
          }),
        ),
        api_base: apiBaseParameter,
      }),
      execute: async ({ query, retailer_id, session_id, api_base }) =>
        callSupportApi(makeUrl(api_base, "/api/chat"), {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ query, retailer_id, session_id }),
        }),
    }),
    tool({
      name: "eko_claw_manifest",
      description:
        "Fetch the formal OpenClaw/NemoClaw/NanoClaw/Hermes runtime mapping for the support workflow.",
      parameters: Type.Object({
        api_base: apiBaseParameter,
      }),
      execute: async ({ api_base }) =>
        callSupportApi(makeUrl(api_base, "/api/claw/manifest")),
    }),
    tool({
      name: "eko_tool_contracts",
      description:
        "Fetch explicit input/output schemas for each Eko support agent node.",
      parameters: Type.Object({
        api_base: apiBaseParameter,
      }),
      execute: async ({ api_base }) =>
        callSupportApi(makeUrl(api_base, "/api/claw/tools")),
    }),
    tool({
      name: "eko_update_ticket_status",
      description:
        "Move a support ticket through open, assigned, resolved, or closed lifecycle states.",
      parameters: Type.Object({
        log_id: Type.Number({
          description: "Support log / ticket id returned by eko_support_chat.",
        }),
        status: Type.Union([
          Type.Literal("open"),
          Type.Literal("assigned"),
          Type.Literal("resolved"),
          Type.Literal("closed"),
        ]),
        api_base: apiBaseParameter,
      }),
      execute: async ({ log_id, status, api_base }) =>
        callSupportApi(makeUrl(api_base, `/api/logs/${log_id}/status`), {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ status }),
        }),
    }),
  ],
});
