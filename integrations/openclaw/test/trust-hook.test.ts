import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { TrustHook } from "../src/trust-hook.js";
import { ProofChain } from "../src/proof-chain.js";
import type { OpenClawPluginAPI } from "../src/types.js";

function mockApi(): OpenClawPluginAPI & { hooks: Map<string, Function> } {
  const hooks = new Map<string, Function>();
  return {
    hooks,
    registerHook(name: string, handler: Function) {
      hooks.set(name, handler);
    },
    registerTool() {},
    log: {
      info() {},
      warn() {},
      error() {},
    },
  };
}

describe("TrustHook", () => {
  it("creates with config", () => {
    const chain = new ProofChain();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: false,
    });
    assert.ok(hook);
  });

  it("registers tool hooks", () => {
    const chain = new ProofChain();
    const api = mockApi();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: false,
    });

    hook.registerHooks(api);
    assert.ok(api.hooks.has("tool:before"));
    assert.ok(api.hooks.has("tool:after"));
    assert.ok(api.hooks.has("tool:error"));
    assert.ok(api.hooks.has("session:end"));
  });

  it("registers browser hooks when enabled", () => {
    const chain = new ProofChain();
    const api = mockApi();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: true,
    });

    hook.registerHooks(api);
    assert.ok(api.hooks.has("browser:action"));
  });

  it("simulated tool call generates proof with correct action", async () => {
    const chain = new ProofChain();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: false,
    });

    await hook.simulateToolCall("web_search", "query: AI safety", "results found");

    assert.equal(chain.length, 1);
    const status = chain.getStatus();
    assert.equal(status.latestAction, "openclaw.tool_call.web_search");
  });

  it("proof chain is valid after multiple tool calls", async () => {
    const chain = new ProofChain();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: false,
    });

    await hook.simulateToolCall("search", "query", "results");
    await hook.simulateToolCall("browse", "url", "page content");
    await hook.simulateToolCall("code_run", "script", "output");

    assert.equal(chain.length, 3);
    const result = await chain.verify();
    assert.equal(result.ok, true);
  });

  it("no crash when API bridge is null", async () => {
    const chain = new ProofChain();
    const hook = new TrustHook({
      agentId: "test-agent",
      proofChain: chain,
      apiBridge: null,
      traceTools: true,
      traceBrowser: false,
    });

    // Should not throw
    await hook.simulateToolCall("test_tool", "input", "output");
    assert.equal(chain.length, 1);
  });
});
