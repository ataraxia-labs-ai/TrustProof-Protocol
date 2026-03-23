/**
 * Optional references to artifacts in external trust/commerce protocols.
 * Enables cross-protocol verification chains.
 */
export interface ProtocolRefs {
  verifiable_intent_id?: string;
  ap2_mandate_id?: string;
  ap2_mandate_type?: "intent" | "cart" | "payment";
  a2a_task_id?: string;
  acp_checkout_id?: string;
  x402_payment_hash?: string;
  mcp_tool_call_id?: string;
  upstream_proof?: string;
  [key: string]: unknown;
}

/**
 * Optional W3C Verifiable Credential compatible profile.
 * Maps TrustProof claims to the VC data model for interoperability.
 */
export interface VCProfile {
  vc_version?: "2.0";
  credential_type?: string[];
  issuer_did?: string;
  subject_did?: string;
  delegation_did?: string;
}

/**
 * TrustProof Claims envelope with optional v0.2 extension fields.
 */
export interface Claims {
  subject: { type: "human" | "agent"; id: string };
  action: string;
  resource: { type: string; id: string };
  policy: {
    policy_v: "v0";
    scopes: string[];
    constraints: {
      max_amount_cents?: number;
      currency_allowlist?: string[];
      merchant_allowlist?: string[];
    };
  };
  result: {
    decision: "allow" | "deny" | "step_up";
    reason_codes: string[];
  };
  hashes: {
    input_hash: string;
    output_hash: string;
  };
  timestamp: string;
  jti: string;
  chain: {
    prev_hash: string;
    entry_hash: string;
  };
  protocol_refs?: ProtocolRefs;
  vc_profile?: VCProfile;
}

export interface ErrorInfo {
  code: string;
  message: string;
  details?: unknown;
}
