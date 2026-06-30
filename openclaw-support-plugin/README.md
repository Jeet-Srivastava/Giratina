# Support Knowledge Claw

OpenClaw tool plugin for the Eko Support Knowledge Claw agent.

The plugin exposes the FastAPI/LangGraph support workflow as callable OpenClaw
tools:

- `eko_support_chat`: submit a retailer query, persist ticket state, and return the agent answer/escalation.
- `eko_claw_manifest`: fetch the formal OpenClaw/NemoClaw/NanoClaw/Hermes mapping.
- `eko_tool_contracts`: fetch per-node input/output schemas.
- `eko_update_ticket_status`: move tickets through `open`, `assigned`, `resolved`, and `closed`.

By default the plugin calls `http://127.0.0.1:8000`. Override this with the
`SUPPORT_KNOWLEDGE_CLAW_API_BASE` environment variable or the optional
`api_base` tool parameter.

## Build

```bash
npm install
npm run plugin:build
npm run plugin:validate
npm test
```

## Local Run Order

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
openclaw gateway run
```
