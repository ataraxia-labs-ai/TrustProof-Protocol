/**
 * Plugin configuration with defaults.
 */

import type { VerdictoPluginConfig } from "./types.js";

const DEFAULTS: Required<Omit<VerdictoPluginConfig, "verdictoApiUrl" | "verdictoApiKey" | "policyPath">> = {
  agentId: "openclaw-agent",
  traceTools: true,
  traceBrowser: true,
  traceApiCalls: false,
};

export function resolveConfig(raw?: Record<string, unknown>): VerdictoPluginConfig {
  if (!raw) return { ...DEFAULTS };

  return {
    agentId: typeof raw.agentId === "string" ? raw.agentId : DEFAULTS.agentId,
    traceTools: typeof raw.traceTools === "boolean" ? raw.traceTools : DEFAULTS.traceTools,
    traceBrowser: typeof raw.traceBrowser === "boolean" ? raw.traceBrowser : DEFAULTS.traceBrowser,
    traceApiCalls: typeof raw.traceApiCalls === "boolean" ? raw.traceApiCalls : DEFAULTS.traceApiCalls,
    verdictoApiUrl: typeof raw.verdictoApiUrl === "string" ? raw.verdictoApiUrl : undefined,
    verdictoApiKey: typeof raw.verdictoApiKey === "string" ? raw.verdictoApiKey : undefined,
    policyPath: typeof raw.policyPath === "string" ? raw.policyPath : undefined,
  };
}
