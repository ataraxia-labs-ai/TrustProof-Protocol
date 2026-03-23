"""Build TrustProof claims for experiment data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from trustproof.chain import canonical_json, sha256_hex


def _hash_input(experiment_num: int, hypothesis: str, code_changes: str | None) -> str:
    return sha256_hex(canonical_json({
        "experiment_num": experiment_num,
        "hypothesis": hypothesis,
        "code_changes": code_changes,
    }))


def _hash_output(
    metric_value: float | None,
    decision: str,
    commit_hash: str | None,
) -> str:
    return sha256_hex(canonical_json({
        "metric_value": metric_value,
        "decision": decision,
        "commit_hash": commit_hash,
    }))


def _build_reason_codes(
    metric_name: str,
    metric_value: float | None,
    decision: str,
) -> list[str]:
    codes: list[str] = []
    if metric_value is not None:
        codes.append(f"metric.{metric_name}={metric_value}")
    codes.append(f"decision.{decision}")
    return codes


def build_experiment_claims(
    *,
    experiment_num: int,
    researcher_id: str,
    principal_id: str | None = None,
    hypothesis: str,
    code_changes: str | None = None,
    code_diff_hash: str | None = None,
    metric_name: str = "val_bpb",
    metric_value: float | None = None,
    decision: str,
    commit_hash: str | None = None,
    policy_snapshot: dict[str, Any],
    session_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build TrustProof claims for a single experiment."""
    claims: dict[str, Any] = {
        "subject": {"type": "agent", "id": researcher_id},
        "action": "autoresearch.experiment",
        "resource": {"type": "experiment", "id": f"experiment_{experiment_num}"},
        "policy": policy_snapshot,
        "result": {
            "decision": "allow" if decision == "keep" else "deny",
            "reason_codes": _build_reason_codes(metric_name, metric_value, decision),
        },
        "hashes": {
            "input_hash": _hash_input(experiment_num, hypothesis, code_changes),
            "output_hash": _hash_output(metric_value, decision, commit_hash),
        },
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "jti": str(uuid4()),
    }

    # v0.2 fields
    if principal_id:
        claims["vc_profile"] = {"delegation_did": principal_id}

    protocol_refs: dict[str, str] = {}
    if commit_hash:
        protocol_refs["upstream_proof"] = commit_hash
    if code_diff_hash:
        protocol_refs["mcp_tool_call_id"] = code_diff_hash
    if protocol_refs:
        claims["protocol_refs"] = protocol_refs

    return claims
