/**
 * Read OpenShell YAML policy files for inclusion in TrustProof claims.
 *
 * We read the policy for CONTEXT only — enforcement is handled by OpenShell.
 * If no policy file is configured, returns an empty policy snapshot.
 */

import { readFileSync } from "node:fs";

/** Minimal policy snapshot for proof context. */
export interface PolicySnapshot {
  policy_v: "v0";
  scopes: string[];
  constraints: {
    max_amount_cents?: number;
    currency_allowlist?: string[];
    merchant_allowlist?: string[];
  };
}

const DEFAULT_POLICY: PolicySnapshot = {
  policy_v: "v0",
  scopes: ["openclaw.tool_call"],
  constraints: {},
};

/**
 * Read an OpenShell YAML policy file and extract a policy snapshot.
 *
 * Falls back to a default policy if the file is missing or unparseable.
 * Uses basic YAML key-value parsing (no dependency on js-yaml for minimal footprint).
 */
export function readPolicy(filePath: string | undefined): PolicySnapshot {
  if (!filePath) return { ...DEFAULT_POLICY };

  try {
    const content = readFileSync(filePath, "utf-8");
    return parsePolicy(content);
  } catch {
    return { ...DEFAULT_POLICY };
  }
}

/**
 * Parse policy content and extract relevant constraints.
 *
 * Handles basic YAML-like policy files. For full YAML support,
 * consider adding js-yaml as a dependency.
 */
function parsePolicy(content: string): PolicySnapshot {
  const scopes: string[] = [];
  const constraints: PolicySnapshot["constraints"] = {};

  for (const line of content.split("\n")) {
    const trimmed = line.trim();

    // Extract scope-like entries (lines starting with "- " under a scopes/permissions section)
    if (trimmed.startsWith("- ") && !trimmed.includes(":")) {
      const value = trimmed.slice(2).trim().replace(/["']/g, "");
      if (value) scopes.push(value);
    }

    // Extract max_amount style constraints
    const amountMatch = trimmed.match(/max_amount[_\s]*(?:cents)?:\s*(\d+)/i);
    if (amountMatch) {
      constraints.max_amount_cents = parseInt(amountMatch[1], 10);
    }
  }

  return {
    policy_v: "v0",
    scopes: scopes.length > 0 ? scopes : ["openclaw.tool_call"],
    constraints,
  };
}

/** Create a snapshot suitable for embedding in a TrustProof claim. */
export function snapshotPolicy(policy: PolicySnapshot): PolicySnapshot {
  return { ...policy };
}
