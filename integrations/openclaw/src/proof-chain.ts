/**
 * In-memory proof chain manager for the OpenClaw plugin.
 *
 * Accumulates signed TrustProof JWTs during an agent session and provides
 * chain verification via the @trustproof/sdk.
 */

import { generateKeyPairSync } from "node:crypto";
import { append, verifyChain, canonicalJson, sha256Hex } from "@trustproof/sdk";

const GENESIS = "0".repeat(64);

export class ProofChain {
  private _chain: string[] = [];
  private _privateKeyPem: string;
  private _publicKeyPem: string;
  private _latestAction: string | null = null;
  private _latestTimestamp: string | null = null;

  constructor(privateKeyPem?: string, publicKeyPem?: string) {
    if (privateKeyPem && publicKeyPem) {
      this._privateKeyPem = privateKeyPem;
      this._publicKeyPem = publicKeyPem;
    } else {
      const { privateKey, publicKey } = generateKeyPairSync("ed25519");
      this._privateKeyPem = privateKey
        .export({ format: "pem", type: "pkcs8" })
        .toString();
      this._publicKeyPem = publicKey
        .export({ format: "pem", type: "spki" })
        .toString();
    }
  }

  get publicKeyPem(): string {
    return this._publicKeyPem;
  }

  get privateKeyPem(): string {
    return this._privateKeyPem;
  }

  get length(): number {
    return this._chain.length;
  }

  /** Append a new proof to the chain. Uses @trustproof/sdk append() for chaining. */
  async appendProof(claims: Record<string, unknown>): Promise<string> {
    const prev = this._chain.length > 0 ? this._chain[this._chain.length - 1] : null;
    const jwt = await append(prev, claims, this._privateKeyPem);
    this._chain.push(jwt);
    this._latestAction =
      typeof claims.action === "string" ? claims.action : null;
    this._latestTimestamp =
      typeof claims.timestamp === "string" ? claims.timestamp : null;
    return jwt;
  }

  /** Get all JWTs in order. */
  getChain(): string[] {
    return [...this._chain];
  }

  /** Get the most recent JWT for chain linking. */
  getLatest(): string | null {
    return this._chain.length > 0 ? this._chain[this._chain.length - 1] : null;
  }

  /** Verify the entire chain for tamper evidence. */
  async verify(): Promise<{ ok: boolean; errors: Array<{ code: string; message: string; index?: number }> }> {
    if (this._chain.length === 0) {
      return { ok: true, errors: [] };
    }
    return verifyChain(this._chain, this._publicKeyPem);
  }

  /** Export chain as JSON array. */
  exportJSON(): string {
    return JSON.stringify(this._chain);
  }

  /** Get chain status summary. */
  getStatus(): {
    proofCount: number;
    latestAction: string | null;
    latestTimestamp: string | null;
  } {
    return {
      proofCount: this._chain.length,
      latestAction: this._latestAction,
      latestTimestamp: this._latestTimestamp,
    };
  }

  /** Reset for new session. */
  clear(): void {
    this._chain = [];
    this._latestAction = null;
    this._latestTimestamp = null;
  }
}

/** Compute the input hash for a tool call. */
export function computeInputHash(toolName: string, input: unknown): string {
  return sha256Hex(canonicalJson({ tool: toolName, input }));
}

/** Compute the output hash for a tool result. */
export function computeOutputHash(output: unknown): string {
  return sha256Hex(canonicalJson({ output }));
}
