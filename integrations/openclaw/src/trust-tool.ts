/**
 * Agent-facing trust tools: let the agent inspect its own proof chain.
 */

import type { ProofChain } from "./proof-chain.js";
import type { OpenClawPluginAPI, OpenClawToolDef } from "./types.js";

/**
 * Register trust-related tools that the OpenClaw agent can invoke.
 *
 * These tools let the agent reason about its own trustworthiness,
 * e.g., "Verify my trust chain is intact before proceeding."
 */
export function registerTrustTools(api: OpenClawPluginAPI, chain: ProofChain): void {
  const tools: OpenClawToolDef[] = [
    {
      name: "trustproof_status",
      description:
        "Returns the current TrustProof chain status: proof count, latest action, and latest timestamp.",
      async execute() {
        const status = chain.getStatus();
        return {
          proof_count: status.proofCount,
          latest_action: status.latestAction,
          latest_timestamp: status.latestTimestamp,
        };
      },
    },

    {
      name: "trustproof_verify_chain",
      description:
        "Verifies the entire TrustProof chain for tamper evidence. Returns valid/invalid with error details.",
      async execute() {
        const result = await chain.verify();
        return {
          valid: result.ok,
          proof_count: chain.length,
          errors: result.errors,
        };
      },
    },

    {
      name: "trustproof_export",
      description:
        "Exports the full TrustProof chain as a JSON array of signed JWT strings.",
      parameters: {
        type: "object",
        properties: {
          format: {
            type: "string",
            enum: ["json", "jwt_array"],
            default: "json",
          },
        },
      },
      async execute(input: Record<string, unknown>) {
        const format = input.format ?? "json";
        if (format === "jwt_array") {
          return { proofs: chain.getChain() };
        }
        return JSON.parse(chain.exportJSON());
      },
    },
  ];

  for (const tool of tools) {
    api.registerTool?.(tool);
  }
}
