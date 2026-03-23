/**
 * Shared types for the verdicto-openclaw plugin.
 */

/** Plugin configuration from openclaw.plugin.json / openclaw.json. */
export interface VerdictoPluginConfig {
  agentId?: string;
  traceTools?: boolean;
  traceBrowser?: boolean;
  traceApiCalls?: boolean;
  verdictoApiUrl?: string;
  verdictoApiKey?: string;
  policyPath?: string;
}

/** A pending action awaiting completion. */
export interface PendingAction {
  action: string;
  toolName: string;
  inputHash: string;
  startedAt: string;
}

/** Summary of the proof chain status. */
export interface ProofChainStatus {
  proofCount: number;
  chainValid: boolean;
  latestAction: string | null;
  latestTimestamp: string | null;
}

/**
 * Minimal OpenClaw plugin API surface.
 *
 * Based on the OpenClaw plugin-sdk/core patterns. Hook and tool registration
 * methods are modeled after the community plugin conventions.
 *
 * TODO: verify exact method signatures against openclaw/plugin-sdk/core types
 * when integrating with a live OpenClaw installation.
 */
export interface OpenClawPluginAPI {
  getConfig?(): Record<string, unknown>;
  registerHook?(hookName: string, handler: (...args: unknown[]) => void | Promise<void>): void;
  registerTool?(toolDef: OpenClawToolDef): void;
  log?: {
    info?(...args: unknown[]): void;
    warn?(...args: unknown[]): void;
    error?(...args: unknown[]): void;
  };
}

export interface OpenClawToolDef {
  name: string;
  description: string;
  parameters?: Record<string, unknown>;
  execute(input: Record<string, unknown>): Promise<unknown>;
}
