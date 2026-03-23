import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, unlinkSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { readPolicy, snapshotPolicy } from "../src/policy-reader.js";

describe("readPolicy", () => {
  it("returns default policy for undefined path", () => {
    const policy = readPolicy(undefined);
    assert.equal(policy.policy_v, "v0");
    assert.deepEqual(policy.scopes, ["openclaw.tool_call"]);
    assert.deepEqual(policy.constraints, {});
  });

  it("returns default policy for missing file", () => {
    const policy = readPolicy("/nonexistent/path/policy.yaml");
    assert.equal(policy.policy_v, "v0");
    assert.deepEqual(policy.scopes, ["openclaw.tool_call"]);
  });

  it("reads a valid YAML-like policy file", () => {
    const dir = mkdtempSync(join(tmpdir(), "tp-test-"));
    const filePath = join(dir, "policy.yaml");
    writeFileSync(
      filePath,
      [
        "permissions:",
        "  - web_search",
        "  - file_read",
        "  - code_execute",
        "constraints:",
        "  max_amount_cents: 5000",
      ].join("\n")
    );

    try {
      const policy = readPolicy(filePath);
      assert.equal(policy.policy_v, "v0");
      assert.ok(policy.scopes.includes("web_search"));
      assert.ok(policy.scopes.includes("file_read"));
      assert.ok(policy.scopes.includes("code_execute"));
      assert.equal(policy.constraints.max_amount_cents, 5000);
    } finally {
      unlinkSync(filePath);
    }
  });
});

describe("snapshotPolicy", () => {
  it("returns a copy of the policy", () => {
    const original = {
      policy_v: "v0" as const,
      scopes: ["test"],
      constraints: { max_amount_cents: 100 },
    };
    const snapshot = snapshotPolicy(original);
    assert.deepEqual(snapshot, original);
    assert.notEqual(snapshot, original); // different reference
  });
});
