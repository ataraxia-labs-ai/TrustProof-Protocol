/**
 * Core lifecycle hook: generates TrustProofs for OpenClaw agent actions.
 *
 * Hooks into the OpenClaw plugin API to intercept tool calls and browser
 * actions, generating a signed, chained TrustProof for each.
 */

import { randomUUID } from "node:crypto";
import { ProofChain, computeInputHash, computeOutputHash } from "./proof-chain.js";
import { readPolicy, snapshotPolicy } from "./policy-reader.js";
import type { APIBridge } from "./api-bridge.js";
import type { OpenClawPluginAPI, PendingAction, VerdictoPluginConfig } from "./types.js";

export interface TrustHookOptions {
  agentId: string;
  proofChain: ProofChain;
  apiBridge: APIBridge | null;
  traceTools: boolean;
  traceBrowser: boolean;
  policyPath?: string;
}

export class TrustHook {
  private _agentId: string;
  private _chain: ProofChain;
  private _apiBridge: APIBridge | null;
  private _traceTools: boolean;
  private _traceBrowser: boolean;
  private _policy: ReturnType<typeof readPolicy>;
  private _pending = new Map<string, PendingAction>();

  constructor(opts: TrustHookOptions) {
    this._agentId = opts.agentId;
    this._chain = opts.proofChain;
    this._apiBridge = opts.apiBridge;
    this._traceTools = opts.traceTools;
    this._traceBrowser = opts.traceBrowser;
    this._policy = readPolicy(opts.policyPath);
  }

  /**
   * Register lifecycle hooks with the OpenClaw plugin API.
   *
   * Hook names follow the patterns observed in OpenClaw community plugins.
   * TODO: verify hook API names against openclaw/plugin-sdk/core types
   */
  registerHooks(api: OpenClawPluginAPI): void {
    if (this._traceTools) {
      api.registerHook?.("tool:before", (...args: unknown[]) => {
        this._onToolStart(args[0] as Record<string, unknown>);
      });

      api.registerHook?.("tool:after", (...args: unknown[]) => {
        this._onToolEnd(args[0] as Record<string, unknown>);
      });

      api.registerHook?.("tool:error", (...args: unknown[]) => {
        this._onToolError(args[0] as Record<string, unknown>);
      });
    }

    if (this._traceBrowser) {
      api.registerHook?.("browser:action", (...args: unknown[]) => {
        void this._onBrowserAction(args[0] as Record<string, unknown>);
      });
    }

    // Session lifecycle
    api.registerHook?.("session:end", () => {
      void this._onSessionEnd();
    });
  }

  // ── Tool hooks ──────────────────────────────────────────────────

  private _onToolStart(event: Record<string, unknown>): void {
    const toolName = String(event.name ?? event.toolName ?? "unknown");
    const runId = String(event.runId ?? event.id ?? randomUUID());
    const input = event.input ?? event.args ?? "";

    this._pending.set(runId, {
      action: `openclaw.tool_call.${toolName}`,
      toolName,
      inputHash: computeInputHash(toolName, input),
      startedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    });
  }

  private _onToolEnd(event: Record<string, unknown>): void {
    const runId = String(event.runId ?? event.id ?? "");
    const pending = this._pending.get(runId);
    if (!pending) return;
    this._pending.delete(runId);

    const output = event.output ?? event.result ?? "";
    const outputHash = computeOutputHash(output);

    void this._generateProof({
      action: pending.action,
      inputHash: pending.inputHash,
      outputHash,
      decision: "allow",
      reasonCodes: [],
      timestamp: pending.startedAt,
    });
  }

  private _onToolError(event: Record<string, unknown>): void {
    const runId = String(event.runId ?? event.id ?? "");
    const pending = this._pending.get(runId);
    if (!pending) return;
    this._pending.delete(runId);

    const error = event.error ?? event.message ?? "unknown error";
    const outputHash = computeOutputHash({ error: String(error) });

    void this._generateProof({
      action: pending.action,
      inputHash: pending.inputHash,
      outputHash,
      decision: "deny",
      reasonCodes: ["tool_error"],
      timestamp: pending.startedAt,
    });
  }

  // ── Browser hooks ───────────────────────────────────────────────

  private async _onBrowserAction(event: Record<string, unknown>): Promise<void> {
    const actionType = String(event.type ?? event.action ?? "navigate");
    const url = String(event.url ?? "");
    const action = `openclaw.web_browse.${actionType}`;

    const inputHash = computeInputHash(actionType, { url, ...event });
    const outputHash = computeOutputHash({ completed: true, url });

    await this._generateProof({
      action,
      inputHash,
      outputHash,
      decision: "allow",
      reasonCodes: [],
      timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    });
  }

  // ── Session hooks ───────────────────────────────────────────────

  private async _onSessionEnd(): Promise<void> {
    const status = this._chain.getStatus();
    if (status.proofCount > 0) {
      const result = await this._chain.verify();
      console.log(
        `[verdicto] Session ended: ${status.proofCount} proofs, chain integrity: ${result.ok ? "VALID" : "BROKEN"}`
      );
    }
  }

  // ── Proof generation ────────────────────────────────────────────

  private async _generateProof(opts: {
    action: string;
    inputHash: string;
    outputHash: string;
    decision: "allow" | "deny" | "step_up";
    reasonCodes: string[];
    timestamp: string;
  }): Promise<void> {
    const claims: Record<string, unknown> = {
      subject: { type: "agent", id: this._agentId },
      action: opts.action,
      resource: { type: "openclaw", id: opts.action },
      policy: snapshotPolicy(this._policy),
      result: { decision: opts.decision, reason_codes: opts.reasonCodes },
      hashes: { input_hash: opts.inputHash, output_hash: opts.outputHash },
      timestamp: opts.timestamp,
      jti: randomUUID(),
    };

    try {
      await this._chain.appendProof(claims);
      console.log(
        `[verdicto] TrustProof generated: ${opts.action} (chain: ${this._chain.length} proofs)`
      );
    } catch (err) {
      console.warn(`[verdicto] Proof generation failed: ${err}`);
    }

    // Send to Verdicto API if configured (non-blocking)
    if (this._apiBridge?.enabled) {
      this._apiBridge
        .sendVerification({
          action: opts.action,
          agentId: this._agentId,
          context: { source: "verdicto-openclaw", action: opts.action },
        })
        .catch((err) => {
          console.warn(`[verdicto] API send failed (non-fatal): ${err}`);
        });
    }
  }

  /** Expose for direct testing. */
  simulateToolCall(toolName: string, input: unknown, output: unknown): Promise<void> {
    const runId = randomUUID();
    this._onToolStart({ name: toolName, runId, input });
    this._onToolEnd({ runId, output });
    // Wait a tick for the async proof generation
    return new Promise((resolve) => setTimeout(resolve, 50));
  }
}
