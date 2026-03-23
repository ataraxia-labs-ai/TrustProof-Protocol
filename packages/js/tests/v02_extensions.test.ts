import { readFileSync } from "node:fs";

import { exportPKCS8, exportSPKI, generateKeyPair } from "jose";
import { beforeAll, describe, expect, it } from "vitest";

import {
  generate,
  validateEnvelopeSchema,
  verify,
  type Claims,
  type ProtocolRefs,
  type VCProfile
} from "../src";

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
    publicKeyPem: await exportSPKI(publicKey)
  };
}

describe("v0.2 extensions: protocol_refs and vc_profile", () => {
  let keyPair: PemKeyPair;
  let allowEnvelope: Record<string, unknown>;

  beforeAll(async () => {
    keyPair = await createPemKeyPair();
    allowEnvelope = readJsonFile<Record<string, unknown>>(
      "../../../spec/examples/allow.json"
    );
  });

  it("generates and verifies claims with protocol_refs", async () => {
    const protocolRefs: ProtocolRefs = {
      verifiable_intent_id: "vi_abc123",
      ap2_mandate_id: "mandate_xyz",
      ap2_mandate_type: "intent",
      a2a_task_id: "task_001",
      acp_checkout_id: "checkout_session_42",
      x402_payment_hash: "0xdeadbeef",
      mcp_tool_call_id: "call_99",
      upstream_proof: "a".repeat(64)
    };

    const envelope = {
      ...allowEnvelope,
      protocol_refs: protocolRefs
    };

    const schemaValidation = validateEnvelopeSchema(envelope);
    expect(schemaValidation.valid).toBe(true);

    const token = await generate(envelope, keyPair.privateKeyPem);
    const result = await verify(token, keyPair.publicKeyPem);

    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);
    expect(result.claims).toBeDefined();

    const claims = result.claims as Claims;
    expect(claims.protocol_refs).toBeDefined();
    expect(claims.protocol_refs!.verifiable_intent_id).toBe("vi_abc123");
    expect(claims.protocol_refs!.ap2_mandate_id).toBe("mandate_xyz");
    expect(claims.protocol_refs!.ap2_mandate_type).toBe("intent");
    expect(claims.protocol_refs!.a2a_task_id).toBe("task_001");
    expect(claims.protocol_refs!.acp_checkout_id).toBe("checkout_session_42");
    expect(claims.protocol_refs!.x402_payment_hash).toBe("0xdeadbeef");
    expect(claims.protocol_refs!.mcp_tool_call_id).toBe("call_99");
    expect(claims.protocol_refs!.upstream_proof).toBe("a".repeat(64));
  });

  it("generates and verifies claims with vc_profile", async () => {
    const vcProfile: VCProfile = {
      vc_version: "2.0",
      credential_type: ["VerifiableCredential", "TrustProofCredential"],
      issuer_did: "did:web:verdicto.dev",
      subject_did: "did:key:z6MkAgent123",
      delegation_did: "did:key:z6MkHuman456"
    };

    const envelope = {
      ...allowEnvelope,
      vc_profile: vcProfile
    };

    const schemaValidation = validateEnvelopeSchema(envelope);
    expect(schemaValidation.valid).toBe(true);

    const token = await generate(envelope, keyPair.privateKeyPem);
    const result = await verify(token, keyPair.publicKeyPem);

    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);
    expect(result.claims).toBeDefined();

    const claims = result.claims as Claims;
    expect(claims.vc_profile).toBeDefined();
    expect(claims.vc_profile!.vc_version).toBe("2.0");
    expect(claims.vc_profile!.credential_type).toEqual([
      "VerifiableCredential",
      "TrustProofCredential"
    ]);
    expect(claims.vc_profile!.issuer_did).toBe("did:web:verdicto.dev");
    expect(claims.vc_profile!.subject_did).toBe("did:key:z6MkAgent123");
    expect(claims.vc_profile!.delegation_did).toBe("did:key:z6MkHuman456");
  });

  it("generates and verifies claims with both protocol_refs and vc_profile", async () => {
    const envelope = {
      ...allowEnvelope,
      protocol_refs: {
        verifiable_intent_id: "vi_combined_test",
        a2a_task_id: "task_combined"
      },
      vc_profile: {
        vc_version: "2.0" as const,
        issuer_did: "did:web:example.com"
      }
    };

    const schemaValidation = validateEnvelopeSchema(envelope);
    expect(schemaValidation.valid).toBe(true);

    const token = await generate(envelope, keyPair.privateKeyPem);
    const result = await verify(token, keyPair.publicKeyPem);

    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);

    const claims = result.claims as Claims;
    expect(claims.protocol_refs!.verifiable_intent_id).toBe("vi_combined_test");
    expect(claims.protocol_refs!.a2a_task_id).toBe("task_combined");
    expect(claims.vc_profile!.vc_version).toBe("2.0");
    expect(claims.vc_profile!.issuer_did).toBe("did:web:example.com");
  });

  it("protocol_refs accepts custom additional properties", async () => {
    const envelope = {
      ...allowEnvelope,
      protocol_refs: {
        verifiable_intent_id: "vi_custom",
        custom_vendor_field: "vendor_value_123"
      }
    };

    const schemaValidation = validateEnvelopeSchema(envelope);
    expect(schemaValidation.valid).toBe(true);

    const token = await generate(envelope, keyPair.privateKeyPem);
    const result = await verify(token, keyPair.publicKeyPem);

    expect(result.ok).toBe(true);

    const claims = result.claims as Claims;
    expect(claims.protocol_refs!.verifiable_intent_id).toBe("vi_custom");
    expect(claims.protocol_refs!.custom_vendor_field).toBe("vendor_value_123");
  });

  it("envelope without protocol_refs or vc_profile still validates (backward compatible)", async () => {
    const schemaValidation = validateEnvelopeSchema(allowEnvelope);
    expect(schemaValidation.valid).toBe(true);

    const token = await generate(allowEnvelope, keyPair.privateKeyPem);
    const result = await verify(token, keyPair.publicKeyPem);

    expect(result.ok).toBe(true);

    const claims = result.claims as Claims;
    expect(claims.protocol_refs).toBeUndefined();
    expect(claims.vc_profile).toBeUndefined();
  });
});
