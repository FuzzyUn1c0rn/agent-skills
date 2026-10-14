#!/usr/bin/env node

const DEFAULT_URL = "http://127.0.0.1:9876/";
const DEFAULT_TIMEOUT_MS = 15_000;
const PROTOCOL_VERSION = "2024-11-05";

function usage() {
  return [
    "Usage:",
    "  burp-mcp-client.mjs status",
    "  burp-mcp-client.mjs tools",
    "  burp-mcp-client.mjs call <tool-name> [--args-json <json-object>]",
    "",
    "Environment:",
    `  BURP_MCP_URL         SSE endpoint (default: ${DEFAULT_URL})`,
    `  BURP_MCP_TIMEOUT_MS  Command timeout (default: ${DEFAULT_TIMEOUT_MS})`,
  ].join("\n");
}

function parsePositiveInteger(value, name) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return parsed;
}

function parseArguments(argv) {
  const [command, ...rest] = argv;
  if (!command || command === "--help" || command === "-h") {
    return { command: "help" };
  }

  if (command === "status" || command === "tools") {
    if (rest.length !== 0) {
      throw new Error(`${command} does not accept arguments`);
    }
    return { command };
  }

  if (command !== "call") {
    throw new Error(`Unknown command: ${command}`);
  }

  const toolName = rest.shift();
  if (!toolName) {
    throw new Error("call requires a tool name");
  }

  let toolArguments = {};
  while (rest.length > 0) {
    const option = rest.shift();
    if (option !== "--args-json") {
      throw new Error(`Unknown option: ${option}`);
    }
    const rawJson = rest.shift();
    if (rawJson === undefined) {
      throw new Error("--args-json requires a JSON object");
    }
    toolArguments = JSON.parse(rawJson);
    if (toolArguments === null || Array.isArray(toolArguments) || typeof toolArguments !== "object") {
      throw new Error("--args-json must contain a JSON object");
    }
  }

  return { command, toolName, toolArguments };
}

class LegacySseMcpClient {
  constructor(baseUrl, timeoutMs) {
    this.baseUrl = new URL(baseUrl);
    this.timeoutMs = timeoutMs;
    this.abortController = new AbortController();
    this.endpoint = null;
    this.nextId = 1;
    this.pending = new Map();
    this.endpointPromise = new Promise((resolve, reject) => {
      this.resolveEndpoint = resolve;
      this.rejectEndpoint = reject;
    });
    this.timeout = setTimeout(() => {
      this.fail(new Error(`Burp MCP command timed out after ${this.timeoutMs} ms`));
      this.abortController.abort();
    }, this.timeoutMs);
  }

  async connect() {
    let response;
    try {
      response = await fetch(this.baseUrl, {
        headers: { Accept: "text/event-stream" },
        signal: this.abortController.signal,
      });
    } catch (error) {
      throw new Error(`Could not connect to Burp MCP at ${this.baseUrl}: ${error.message}`);
    }

    if (!response.ok || !response.body) {
      throw new Error(`Burp MCP SSE connection returned HTTP ${response.status}`);
    }

    this.pumpPromise = this.pumpEvents(response.body).catch((error) => {
      if (error?.name !== "AbortError") {
        this.fail(error);
      }
    });

    this.endpoint = await this.endpointPromise;
    const initializeResult = await this.request("initialize", {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: "codex-burp-skill", version: "1.0.0" },
    });
    await this.notify("notifications/initialized", {});
    return initializeResult;
  }

  async pumpEvents(body) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });

      let boundary;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const block = buffer.slice(0, boundary);
        const delimiter = buffer.slice(boundary).match(/^\r?\n\r?\n/)[0];
        buffer = buffer.slice(boundary + delimiter.length);
        this.handleEvent(block);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      this.handleEvent(buffer);
    }
    throw new Error("Burp MCP closed the SSE connection unexpectedly");
  }

  handleEvent(block) {
    let eventType = "message";
    const dataLines = [];

    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length === 0) {
      return;
    }
    const data = dataLines.join("\n");

    if (eventType === "endpoint") {
      try {
        this.resolveEndpoint(new URL(data, this.baseUrl));
      } catch (error) {
        this.rejectEndpoint(new Error(`Burp MCP returned an invalid session endpoint: ${error.message}`));
      }
      return;
    }

    if (eventType !== "message") {
      return;
    }

    let message;
    try {
      message = JSON.parse(data);
    } catch (error) {
      this.fail(new Error(`Burp MCP returned invalid JSON: ${error.message}`));
      return;
    }

    if (message.id === undefined || message.id === null) {
      return;
    }
    const pending = this.pending.get(String(message.id));
    if (!pending) {
      return;
    }
    this.pending.delete(String(message.id));

    if (message.error) {
      const details = typeof message.error === "object" ? JSON.stringify(message.error) : String(message.error);
      pending.reject(new Error(`Burp MCP error: ${details}`));
    } else {
      pending.resolve(message.result);
    }
  }

  async post(message) {
    if (!this.endpoint) {
      throw new Error("Burp MCP session endpoint is not ready");
    }
    const response = await fetch(this.endpoint, {
      method: "POST",
      headers: {
        Accept: "application/json, text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(message),
      signal: this.abortController.signal,
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Burp MCP request returned HTTP ${response.status}${body ? `: ${body}` : ""}`);
    }
    await response.arrayBuffer();
  }

  async request(method, params) {
    const id = this.nextId++;
    const resultPromise = new Promise((resolve, reject) => {
      this.pending.set(String(id), { resolve, reject });
    });

    try {
      await this.post({ jsonrpc: "2.0", id, method, params });
    } catch (error) {
      this.pending.delete(String(id));
      throw error;
    }
    return resultPromise;
  }

  async notify(method, params) {
    await this.post({ jsonrpc: "2.0", method, params });
  }

  fail(error) {
    this.rejectEndpoint(error);
    for (const pending of this.pending.values()) {
      pending.reject(error);
    }
    this.pending.clear();
  }

  async close() {
    clearTimeout(this.timeout);
    this.abortController.abort();
    await this.pumpPromise;
  }
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.command === "help") {
    process.stdout.write(`${usage()}\n`);
    return;
  }

  const baseUrl = process.env.BURP_MCP_URL || DEFAULT_URL;
  const timeoutMs = parsePositiveInteger(
    process.env.BURP_MCP_TIMEOUT_MS || String(DEFAULT_TIMEOUT_MS),
    "BURP_MCP_TIMEOUT_MS",
  );
  const client = new LegacySseMcpClient(baseUrl, timeoutMs);

  try {
    const initializeResult = await client.connect();
    let output;
    if (options.command === "status") {
      output = {
        ok: true,
        url: new URL(baseUrl).toString(),
        protocolVersion: initializeResult.protocolVersion,
        serverInfo: initializeResult.serverInfo,
        capabilities: initializeResult.capabilities,
      };
    } else if (options.command === "tools") {
      output = await client.request("tools/list", {});
    } else {
      output = await client.request("tools/call", {
        name: options.toolName,
        arguments: options.toolArguments,
      });
    }
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  } finally {
    await client.close();
  }
}

main().catch((error) => {
  process.stderr.write(`burp-mcp-client: ${error.message}\n`);
  process.exitCode = 1;
});
