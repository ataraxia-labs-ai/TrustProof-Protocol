/**
 * verdicto-openclaw — TrustProof plugin for OpenClaw.
 *
 * Generates cryptographic audit trails for every agent action.
 * Every tool call and browser action gets a signed, tamper-evident TrustProof.
 *
 * @example
 * ```json
 * // openclaw.json
 * {
 *   "plugins": {
 *     "entries": {
 *       "verdicto-trustproof": {
 *         "enabled": true,
 *         "config": { "agentId": "my-agent", "traceTools": true }
 *       }
 *     }
 *   }
 * }
 * ```
 */

import { TrustHook } from "./trust-hook.js";
import { registerTrustTools } from "./trust-tool.js";
import { ProofChain } from "./proof-chain.js";
import { APIBridge } from "./api-bridge.js";
import { resolveConfig } from "./config.js";
import type { OpenClawPluginAPI, VerdictoPluginConfig } from "./types.js";

export { TrustHook } from "./trust-hook.js";
export { ProofChain, computeInputHash, computeOutputHash } from "./proof-chain.js";
export { APIBridge } from "./api-bridge.js";
export { resolveConfig } from "./config.js";
export type { VerdictoPluginConfig, OpenClawPluginAPI, ProofChainStatus } from "./types.js";

/**
 * Plugin entry point for OpenClaw.
 *
 * OpenClaw loads plugins via definePluginEntry({ id, name, register(api) }).
 * Since we can't import the OpenClaw SDK at build time (it's a peer dep),
 * we export a plain object matching the expected shape.
 *
 * TODO: wrap with definePluginEntry() when openclaw/plugin-sdk/core is available
 */
export default {
  id: "verdicto-trustproof",
  name: "Verdicto TrustProof",

  register(api: OpenClawPluginAPI): ProofChain {
    const rawConfig = api.getConfig?.() ?? {};
    const config = resolveConfig(rawConfig);

    const proofChain = new ProofChain();
    const apiBridge =
      config.verdictoApiUrl && config.verdictoApiKey
        ? new APIBridge(config.verdictoApiUrl, config.verdictoApiKey)
        : null;

    const trustHook = new TrustHook({
      agentId: config.agentId ?? "openclaw-agent",
      proofChain,
      apiBridge,
      traceTools: config.traceTools ?? true,
      traceBrowser: config.traceBrowser ?? true,
      policyPath: config.policyPath,
    });

    trustHook.registerHooks(api);
    registerTrustTools(api, proofChain);

    api.log?.info?.(
      "[verdicto] TrustProof plugin loaded. Generating proofs for agent actions."
    );

    return proofChain;
  },
};
