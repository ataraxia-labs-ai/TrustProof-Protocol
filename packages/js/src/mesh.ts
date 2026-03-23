/**
 * Proof Mesh: Cross-platform trust federation for TrustProof Protocol.
 *
 * Enables verification of Trust Proof chains that span multiple issuers,
 * platforms, and signing keys.
 *
 * Concepts:
 * - Issuer: An entity that signs Trust Proofs (identified by kid or iss claim)
 * - IssuerRegistry: Maps issuer IDs to their Ed25519 public keys
 * - MeshVerifier: Validates chains across issuer boundaries
 *
 * Trust model:
 * - Each proof's issuer is resolved from the JWT header (kid) or payload (iss)
 * - The registry provides the correct public key per issuer
 * - Chain integrity (prev_hash/entry_hash) is verified the same way as single-issuer
 * - Cross-references via protocol_refs.upstream_proof are tracked but not recursively resolved in v0
 */

import {
  computeCanonicalEventMaterial,
  computeEntryHash,
  normalizeHex,
} from "./chain";
import { verify } from "./verify";

const GENESIS_PREV_HASH = "0".repeat(64);
const HEX_64_RE = /^[a-fA-F0-9]{64}$/;

// ── Types ──────────────────────────────────────────────────────────

export type IssuerTrust = "verified" | "self_declared" | "untrusted";

export interface Issuer {
  issuerId: string;
  publicKeyPem: string;
  displayName: string;
  trustLevel: IssuerTrust;
  metadata?: Record<string, unknown>;
}

export interface MeshLink {
  index: number;
  proofJwt: string;
  issuerId: string;
  issuer: Issuer | null;
  claims: Record<string, unknown>;
  signatureValid: boolean;
  chainValid: boolean;
  crossRefs: string[];
  errors: string[];
}

export interface MeshVerification {
  valid: boolean;
  links: MeshLink[];
  issuersInvolved: string[];
  chainLength: number;
  crossPlatformHops: number;
  trustSummary: Record<string, IssuerTrust>;
  errors: string[];
  warnings: string[];
}

// ── Helpers ────────────────────────────────────────────────────────

function decodeBase64Url(segment: string): string {
  const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(
    base64.length + ((4 - (base64.length % 4)) % 4),
    "="
  );
  return Buffer.from(padded, "base64").toString("utf8");
}

function extractIssuerId(jwtStr: string): string {
  try {
    const parts = jwtStr.split(".");
    if (parts.length !== 3) return "unknown";

    // Check header for kid
    const header: unknown = JSON.parse(decodeBase64Url(parts[0]));
    if (header && typeof header === "object" && !Array.isArray(header)) {
      const kid = (header as Record<string, unknown>).kid;
      if (typeof kid === "string" && kid) return kid;
    }

    // Check payload for iss
    const payload: unknown = JSON.parse(decodeBase64Url(parts[1]));
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      const iss = (payload as Record<string, unknown>).iss;
      if (typeof iss === "string" && iss) return iss;
    }

    return "unknown";
  } catch {
    return "unknown";
  }
}

function decodePayloadUntrusted(jwtStr: string): Record<string, unknown> {
  try {
    const parts = jwtStr.split(".");
    if (parts.length !== 3) return {};
    const payload: unknown = JSON.parse(decodeBase64Url(parts[1]));
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      return payload as Record<string, unknown>;
    }
    return {};
  } catch {
    return {};
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

// ── IssuerRegistry ─────────────────────────────────────────────────

export class IssuerRegistry {
  private _issuers = new Map<string, Issuer>();

  register(issuer: Issuer): void {
    this._issuers.set(issuer.issuerId, issuer);
  }

  get(issuerId: string): Issuer | undefined {
    return this._issuers.get(issuerId);
  }

  resolveFromJwt(proofJwt: string): [string, Issuer | undefined] {
    const issuerId = extractIssuerId(proofJwt);
    return [issuerId, this._issuers.get(issuerId)];
  }

  listIssuers(): Issuer[] {
    return Array.from(this._issuers.values());
  }

  get size(): number {
    return this._issuers.size;
  }
}

// ── MeshVerifier ───────────────────────────────────────────────────

export class MeshVerifier {
  constructor(public readonly registry: IssuerRegistry) {}

  async verifyChain(proofJwts: string[]): Promise<MeshVerification> {
    if (proofJwts.length === 0) {
      return {
        valid: true,
        links: [],
        issuersInvolved: [],
        chainLength: 0,
        crossPlatformHops: 0,
        trustSummary: {},
        errors: [],
        warnings: [],
      };
    }

    const links: MeshLink[] = [];
    const errors: string[] = [];
    const warnings: string[] = [];
    const issuerSet = new Set<string>();
    let prevEntryHash: string | null = null;
    let hops = 0;

    for (let i = 0; i < proofJwts.length; i++) {
      const link = await this._verifySingleLink(i, proofJwts[i], prevEntryHash);
      links.push(link);
      issuerSet.add(link.issuerId);

      if (!link.signatureValid) {
        errors.push(
          `Link ${i}: signature verification failed for issuer '${link.issuerId}'`
        );
      }
      if (!link.chainValid) {
        errors.push(
          `Link ${i}: chain integrity failed (prev_hash mismatch)`
        );
      }
      if (link.issuer === null) {
        warnings.push(`Link ${i}: issuer '${link.issuerId}' not in registry`);
      } else if (link.issuer.trustLevel === "self_declared") {
        warnings.push(
          `Link ${i}: issuer '${link.issuerId}' is self-declared (not independently verified)`
        );
      }

      errors.push(...link.errors);

      // Track cross-platform hops
      if (i > 0 && link.issuerId !== links[i - 1].issuerId) {
        hops++;
      }

      // Extract entry_hash for next link
      const chain = link.claims.chain;
      if (isRecord(chain)) {
        const entryHash = chain.entry_hash;
        if (typeof entryHash === "string" && HEX_64_RE.test(entryHash)) {
          prevEntryHash = normalizeHex(entryHash);
        } else {
          prevEntryHash = null;
        }
      } else {
        prevEntryHash = null;
      }
    }

    const trustSummary: Record<string, IssuerTrust> = {};
    for (const iid of issuerSet) {
      const issuer = this.registry.get(iid);
      trustSummary[iid] = issuer ? issuer.trustLevel : "untrusted";
    }

    const allValid = links.every((l) => l.signatureValid && l.chainValid);

    return {
      valid: allValid && errors.length === 0,
      links,
      issuersInvolved: Array.from(issuerSet).sort(),
      chainLength: links.length,
      crossPlatformHops: hops,
      trustSummary,
      errors,
      warnings,
    };
  }

  async verifySingle(proofJwt: string): Promise<MeshLink> {
    return this._verifySingleLink(0, proofJwt, null);
  }

  private async _verifySingleLink(
    index: number,
    jwtStr: string,
    expectedPrevHash: string | null
  ): Promise<MeshLink> {
    const [issuerId, issuer] = this.registry.resolveFromJwt(jwtStr);
    const crossRefs: string[] = [];
    const linkErrors: string[] = [];

    // 1. Signature verification
    let signatureValid = false;
    let claims: Record<string, unknown> = {};

    if (issuer !== undefined) {
      const result = await verify(jwtStr, issuer.publicKeyPem);
      if (result.ok && result.claims) {
        claims = result.claims as Record<string, unknown>;
        signatureValid = true;
      } else {
        linkErrors.push(
          `Signature invalid: ${result.errors.map((e) => e.message).join("; ")}`
        );
        // Still decode for chain analysis
        claims = decodePayloadUntrusted(jwtStr);
      }
    } else {
      // Unknown issuer — can't verify signature, decode untrusted
      claims = decodePayloadUntrusted(jwtStr);
      linkErrors.push(
        `Unknown issuer: '${issuerId}' — cannot verify signature`
      );
    }

    // 2. Chain integrity
    let chainValid = true;
    const chainData = isRecord(claims.chain) ? claims.chain : {};
    const prevHash =
      typeof (chainData as Record<string, unknown>).prev_hash === "string"
        ? ((chainData as Record<string, unknown>).prev_hash as string)
        : "";
    const entryHash =
      typeof (chainData as Record<string, unknown>).entry_hash === "string"
        ? ((chainData as Record<string, unknown>).entry_hash as string)
        : "";

    if (index === 0) {
      // Genesis: prev_hash must be 64 zeros
      if (prevHash !== GENESIS_PREV_HASH) {
        // In mesh context, first proof might not be genesis if it's a sub-chain
        if (expectedPrevHash === null) {
          // Allow non-genesis first proof in mesh
        } else if (normalizeHex(prevHash) !== expectedPrevHash) {
          chainValid = false;
        }
      }
    } else {
      if (expectedPrevHash !== null) {
        if (!prevHash || normalizeHex(prevHash) !== expectedPrevHash) {
          chainValid = false;
        }
      }
    }

    // Verify entry_hash integrity
    if (signatureValid && Object.keys(claims).length > 0) {
      try {
        const cem = computeCanonicalEventMaterial(claims);
        const recomputed = computeEntryHash(normalizeHex(prevHash), cem);
        if (normalizeHex(entryHash) !== recomputed) {
          chainValid = false;
          linkErrors.push("entry_hash does not match recomputed hash");
        }
      } catch {
        // Missing fields — already caught by schema validation
      }
    }

    // 3. Cross-references
    const protocolRefs = claims.protocol_refs;
    if (isRecord(protocolRefs)) {
      const upstream = protocolRefs.upstream_proof;
      if (typeof upstream === "string" && upstream) {
        crossRefs.push(upstream);
      }
    }

    return {
      index,
      proofJwt: jwtStr,
      issuerId,
      issuer: issuer ?? null,
      claims,
      signatureValid,
      chainValid,
      crossRefs,
      errors: linkErrors,
    };
  }
}
