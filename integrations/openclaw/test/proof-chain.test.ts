import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ProofChain, computeInputHash, computeOutputHash } from "../src/proof-chain.js";

function makeClaims(action: string): Record<string, unknown> {
  return {
    subject: { type: "agent", id: "test-agent" },
    action,
    resource: { type: "openclaw", id: action },
    policy: { policy_v: "v0", scopes: ["openclaw.tool_call"], constraints: {} },
    result: { decision: "allow", reason_codes: [] },
    hashes: {
      input_hash: computeInputHash("test", `input_${action}`),
      output_hash: computeOutputHash(`output_${action}`),
    },
    timestamp: "2026-03-21T12:00:00Z",
    jti: `jti_${action}_${Date.now()}`,
  };
}

describe("ProofChain", () => {
  it("builds a chain of 3 proofs", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("step_1"));
    await chain.appendProof(makeClaims("step_2"));
    await chain.appendProof(makeClaims("step_3"));

    assert.equal(chain.length, 3);
    assert.equal(chain.getChain().length, 3);
  });

  it("verifies a valid chain", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("tool_a"));
    await chain.appendProof(makeClaims("tool_b"));
    await chain.appendProof(makeClaims("tool_c"));

    const result = await chain.verify();
    assert.equal(result.ok, true);
    assert.deepEqual(result.errors, []);
  });

  it("detects tampered proof", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("action_1"));
    await chain.appendProof(makeClaims("action_2"));

    // Tamper with the first proof
    const rawChain = chain.getChain();
    const parts = rawChain[0].split(".");
    const payload = Buffer.from(parts[1], "base64url");
    const tampered = Buffer.alloc(payload.length);
    payload.copy(tampered);
    tampered[tampered.length - 2] ^= 0xff; // flip a byte
    const tamperedJwt = `${parts[0]}.${tampered.toString("base64url")}.${parts[2]}`;

    // Create a new chain with tampered proof
    const tamperedChain = new ProofChain(chain.privateKeyPem, chain.publicKeyPem);
    (tamperedChain as any)._chain = [tamperedJwt, rawChain[1]];

    const result = await tamperedChain.verify();
    assert.equal(result.ok, false);
  });

  it("exports valid JSON", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("export_test"));

    const json = chain.exportJSON();
    const parsed = JSON.parse(json);
    assert.equal(Array.isArray(parsed), true);
    assert.equal(parsed.length, 1);
    assert.equal(typeof parsed[0], "string");
  });

  it("clear resets chain", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("clear_test"));
    assert.equal(chain.length, 1);

    chain.clear();
    assert.equal(chain.length, 0);
    assert.equal(chain.getLatest(), null);
  });

  it("getStatus returns correct summary", async () => {
    const chain = new ProofChain();
    await chain.appendProof(makeClaims("status_test"));

    const status = chain.getStatus();
    assert.equal(status.proofCount, 1);
    assert.equal(status.latestAction, "status_test");
  });

  it("empty chain verifies as valid", async () => {
    const chain = new ProofChain();
    const result = await chain.verify();
    assert.equal(result.ok, true);
  });
});

describe("hash functions", () => {
  it("computeInputHash is deterministic", () => {
    const h1 = computeInputHash("search", "query");
    const h2 = computeInputHash("search", "query");
    assert.equal(h1, h2);
    assert.equal(h1.length, 64);
  });

  it("computeOutputHash is deterministic", () => {
    const h1 = computeOutputHash("result");
    const h2 = computeOutputHash("result");
    assert.equal(h1, h2);
    assert.equal(h1.length, 64);
  });
});
