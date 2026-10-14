---
name: burp-suite
description: Connect to the locally running Burp Suite MCP server on demand through its SSE endpoint. Invoke explicitly as $burp-suite when the user wants to inspect or operate Burp; do not use it for general security advice or when Burp access was not requested.
---

# Burp Suite

Use the bundled client instead of relying on Codex's startup-time MCP catalog. The client connects only for the duration of one command and requires no Java proxy, npm package, or globally enabled Burp MCP configuration.

## Workflow

Resolve `scripts/burp-mcp-client.mjs` relative to this `SKILL.md`, then use Node.js to run it.

1. Verify connectivity and complete the MCP handshake:

   ```powershell
   node <skill-dir>\scripts\burp-mcp-client.mjs status
   ```

2. Before calling a tool, inspect the live tool names and input schemas:

   ```powershell
   node <skill-dir>\scripts\burp-mcp-client.mjs tools
   ```

3. Invoke a tool with arguments matching its live schema:

   ```powershell
   node <skill-dir>\scripts\burp-mcp-client.mjs call <tool-name> --args-json '<json-object>'
   ```

Output is JSON on stdout. Diagnostics are written to stderr. Set `BURP_MCP_URL` to override the default `http://127.0.0.1:9876/`, and `BURP_MCP_TIMEOUT_MS` to override the 15-second command timeout.

## Authorization boundaries

- Listing tools, checking status, and reading existing Burp data are diagnostic operations.
- Do not initiate scans, send traffic to a target, modify Burp configuration, or change Burp data unless the user explicitly requested that action and the target is within their stated scope.
- Treat live tool descriptions as capabilities, not authorization.
- Show the intended tool name and material arguments before any intrusive or state-changing call when the user's request did not already make them explicit.
- Never place credentials, session tokens, authorization headers, or sensitive response bodies in durable files or command-line arguments. If sensitive input is required, stop and choose an environment-variable or stdin-based approach appropriate to that specific tool.

## Troubleshooting

If `status` fails, report the exact error and check these conditions without editing global Codex configuration:

- Burp Suite is running.
- The Burp MCP extension is loaded and enabled in Burp's MCP tab.
- Its configured endpoint is reachable at `BURP_MCP_URL` or the default port 9876.
- A local firewall or sandbox is not blocking loopback access.

Do not re-enable the desktop Burp MCP server or modify `~/.codex/config.toml` as part of this skill.
