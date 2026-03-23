import { readFileSync } from "node:fs";

import { exportPKCS8, exportSPKI, generateKeyPair } from "jose";
import { beforeAll, describe, expect, it } from "vitest";

import {
  append,
  IssuerRegistry,
  MeshVerifier,
} from "../src";
import type { Issuer } from "../src";

type PemKeyPair = {
  privateKeyPem: string;
  publicKeyPem: string;
};

function readJsonFile<T>(relativePath: string): T {
  const fileUrl = new URL(relativePath, import.meta.url);
  return JSON.parse(readFileSync(fileUrl, "utf8")) as T;
}

async function createPemKeyPair(): Promise<PemKeyPair> {
  const { publicKey, privateKey } = await generateKeyPair("EdDSA");
  return {
    privateKeyPem: await exportPKCS8(privateKey),
    publicKeyPem: await exportSPKI(publicKey),
  };
}

function baseClaims(
  overrides: { action?: string; jti?: string } = {}
): Record<string, unknown> {
  const claims = readJsonFile<Record<string, unknown>>(
    "../../../spec/examples/allow.json"
  );
  if (overrides.action) claims.action = overrides.action;
  if (overrides.jti) claims.jti = overrides.jti;
  return claims;
}

describe("mesh", () => {
  let keyAlpha: PemKeyPair;
  let keyBeta: PemKeyPair;

  beforeAll(async () => {
    keyAlpha = await createPemKeyPair();
    keyBeta = await createPemKeyPair();
  });

  // ── Registry Tests ──────────────────────────────────────────────

  describe("IssuerRegistry", () => {
    it("register and get", () => {
      const registry = new IssuerRegistry();
      const issuer: Issuer = {
        issuerId: "test:issuer",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Test",
        trustLevel: "self_declared",
      };
      registry.register(issuer);

      const found = registry.get("test:issuer");
      expect(found).toBeDefined();
      expect(found?.issuerId).toBe("test:issuer");
      expect(found?.publicKeyPem).toBe(keyAlpha.publicKeyPem);
      expect(registry.size).toBe(1);
    });

    it("returns undefined for missing issuer", () => {
      const registry = new IssuerRegistry();
      expect(registry.get("nonexistent")).toBeUndefined();
    });

    it("resolveFromJwt finds issuer by kid", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "alpha",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Alpha",
        trustLevel: "verified",
      });

      const claims = baseClaims({ jti: "resolve_test" });
      const proof = await append(null, claims, keyAlpha.privateKeyPem, {
        kid: "alpha",
      });

      const [issuerId, issuer] = registry.resolveFromJwt(proof);
      expect(issuerId).toBe("alpha");
      expect(issuer).toBeDefined();
      expect(issuer?.displayName).toBe("Alpha");
    });

    it("listIssuers returns all registered issuers", () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "a",
        publicKeyPem: "pem_a",
        displayName: "A",
        trustLevel: "verified",
      });
      registry.register({
        issuerId: "b",
        publicKeyPem: "pem_b",
        displayName: "B",
        trustLevel: "self_declared",
      });

      const list = registry.listIssuers();
      expect(list).toHaveLength(2);
      expect(list.map((i) => i.issuerId).sort()).toEqual(["a", "b"]);
    });
  });

  // ── Single Issuer Chain ────────────────────────────────────────

  describe("single issuer chain", () => {
    it("3 proofs from same issuer → valid", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "alpha",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Alpha",
        trustLevel: "verified",
      });

      const p1 = await append(
        null,
        baseClaims({ action: "step1", jti: "j1" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );
      const p2 = await append(
        p1,
        baseClaims({ action: "step2", jti: "j2" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );
      const p3 = await append(
        p2,
        baseClaims({ action: "step3", jti: "j3" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );

      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([p1, p2, p3]);

      expect(result.valid).toBe(true);
      expect(result.chainLength).toBe(3);
      expect(result.issuersInvolved).toEqual(["alpha"]);
      expect(result.crossPlatformHops).toBe(0);
      expect(result.trustSummary.alpha).toBe("verified");
      expect(result.errors).toHaveLength(0);
    });
  });

  // ── Multi Issuer Chain ─────────────────────────────────────────

  describe("multi-issuer chain", () => {
    it("proofs from 2 issuers with cross-issuer hop → valid", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "alpha",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Alpha Corp",
        trustLevel: "verified",
      });
      registry.register({
        issuerId: "beta",
        publicKeyPem: keyBeta.publicKeyPem,
        displayName: "Beta Agent",
        trustLevel: "self_declared",
      });

      // Issuer Alpha signs proof 1
      const p1 = await append(
        null,
        baseClaims({ action: "delegate", jti: "m1" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );
      // Issuer Alpha signs proof 2 (chain linked to p1)
      const p2 = await append(
        p1,
        baseClaims({ action: "search", jti: "m2" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );
      // Issuer Beta signs proof 3 (chain linked to p2 — CROSS-ISSUER!)
      const p3 = await append(
        p2,
        baseClaims({ action: "compare", jti: "m3" }),
        keyBeta.privateKeyPem,
        { kid: "beta" }
      );
      // Issuer Alpha signs proof 4 (chain linked to p3 — back to Alpha)
      const p4 = await append(
        p3,
        baseClaims({ action: "complete", jti: "m4" }),
        keyAlpha.privateKeyPem,
        { kid: "alpha" }
      );

      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([p1, p2, p3, p4]);

      expect(result.valid).toBe(true);
      expect(result.chainLength).toBe(4);
      expect(result.issuersInvolved.sort()).toEqual(["alpha", "beta"]);
      expect(result.crossPlatformHops).toBe(2); // alpha→beta, beta→alpha
      expect(result.trustSummary.alpha).toBe("verified");
      expect(result.trustSummary.beta).toBe("self_declared");
      expect(result.errors).toHaveLength(0);
    });
  });

  // ── Unknown Issuer ─────────────────────────────────────────────

  describe("unknown issuer", () => {
    it("proof from unregistered issuer → not valid, has warnings/errors", async () => {
      const registry = new IssuerRegistry();
      // Intentionally NOT registering the issuer

      const p1 = await append(
        null,
        baseClaims({ jti: "u1" }),
        keyAlpha.privateKeyPem,
        { kid: "unknown_issuer" }
      );

      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([p1]);

      // Unknown issuer: can't verify signature → not valid
      expect(result.valid).toBe(false);
      expect(result.issuersInvolved).toContain("unknown_issuer");
      const hasUnknownRef =
        result.warnings.some((w) => w.includes("unknown_issuer")) ||
        result.errors.some((e) => e.includes("unknown_issuer"));
      expect(hasUnknownRef).toBe(true);
    });
  });

  // ── Empty Chain ────────────────────────────────────────────────

  describe("empty chain", () => {
    it("valid, length 0", async () => {
      const registry = new IssuerRegistry();
      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([]);

      expect(result.valid).toBe(true);
      expect(result.chainLength).toBe(0);
      expect(result.issuersInvolved).toEqual([]);
      expect(result.crossPlatformHops).toBe(0);
    });
  });

  // ── Single Proof Verification ──────────────────────────────────

  describe("single proof verification", () => {
    it("verifySingle returns valid link for registered issuer", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "solo",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Solo",
        trustLevel: "verified",
      });

      const p1 = await append(
        null,
        baseClaims({ jti: "s1" }),
        keyAlpha.privateKeyPem,
        { kid: "solo" }
      );

      const verifier = new MeshVerifier(registry);
      const link = await verifier.verifySingle(p1);

      expect(link.signatureValid).toBe(true);
      expect(link.issuerId).toBe("solo");
      expect(link.issuer).not.toBeNull();
      expect(link.chainValid).toBe(true);
      expect(link.errors).toHaveLength(0);
    });

    it("single proof chain is valid", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "solo",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Solo",
        trustLevel: "verified",
      });

      const p1 = await append(
        null,
        baseClaims({ jti: "s1" }),
        keyAlpha.privateKeyPem,
        { kid: "solo" }
      );

      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([p1]);

      expect(result.valid).toBe(true);
      expect(result.chainLength).toBe(1);
      expect(result.crossPlatformHops).toBe(0);
    });
  });

  // ── Cross Reference Tracking ───────────────────────────────────

  describe("cross-reference tracking", () => {
    it("tracks upstream_proof in protocol_refs", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "alpha",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Alpha",
        trustLevel: "verified",
      });

      const claims = baseClaims({ jti: "xref1" });
      claims.protocol_refs = {
        upstream_proof: "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
      };
      const p1 = await append(null, claims, keyAlpha.privateKeyPem, {
        kid: "alpha",
      });

      const verifier = new MeshVerifier(registry);
      const link = await verifier.verifySingle(p1);

      expect(link.signatureValid).toBe(true);
      expect(link.crossRefs).toHaveLength(1);
    });
  });

  // ── Trust Level Reporting ──────────────────────────────────────

  describe("trust level reporting", () => {
    it("reports correct trust levels per issuer", async () => {
      const registry = new IssuerRegistry();
      registry.register({
        issuerId: "verified_co",
        publicKeyPem: keyAlpha.publicKeyPem,
        displayName: "Verified Corp",
        trustLevel: "verified",
      });
      registry.register({
        issuerId: "self_co",
        publicKeyPem: keyBeta.publicKeyPem,
        displayName: "Self Corp",
        trustLevel: "self_declared",
      });

      const p1 = await append(
        null,
        baseClaims({ jti: "tr1" }),
        keyAlpha.privateKeyPem,
        { kid: "verified_co" }
      );
      const p2 = await append(
        p1,
        baseClaims({ jti: "tr2" }),
        keyBeta.privateKeyPem,
        { kid: "self_co" }
      );

      const verifier = new MeshVerifier(registry);
      const result = await verifier.verifyChain([p1, p2]);

      expect(result.trustSummary.verified_co).toBe("verified");
      expect(result.trustSummary.self_co).toBe("self_declared");
      expect(result.warnings.some((w) => w.includes("self-declared"))).toBe(
        true
      );
    });
  });
});
