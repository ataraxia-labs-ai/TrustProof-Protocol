"""Tests for experiment proof builder."""

from verdicto_autoresearch.experiment_proof import build_experiment_claims


def test_build_claims_structure() -> None:
    claims = build_experiment_claims(
        experiment_num=1,
        researcher_id="test-agent",
        hypothesis="increase lr",
        metric_name="val_bpb",
        metric_value=1.234,
        decision="keep",
        policy_snapshot={"policy_v": "v0", "scopes": ["autoresearch.experiment"], "constraints": {}},
    )

    assert claims["subject"] == {"type": "agent", "id": "test-agent"}
    assert claims["action"] == "autoresearch.experiment"
    assert claims["resource"]["type"] == "experiment"
    assert claims["result"]["decision"] == "allow"
    assert "input_hash" in claims["hashes"]
    assert "output_hash" in claims["hashes"]
    assert len(claims["hashes"]["input_hash"]) == 64
    assert len(claims["hashes"]["output_hash"]) == 64
    assert claims["jti"]
    assert claims["timestamp"]


def test_input_output_hashes_deterministic() -> None:
    c1 = build_experiment_claims(
        experiment_num=1, researcher_id="a", hypothesis="test",
        metric_value=1.0, decision="keep",
        policy_snapshot={"policy_v": "v0", "scopes": [], "constraints": {}},
    )
    c2 = build_experiment_claims(
        experiment_num=1, researcher_id="a", hypothesis="test",
        metric_value=1.0, decision="keep",
        policy_snapshot={"policy_v": "v0", "scopes": [], "constraints": {}},
    )
    assert c1["hashes"]["input_hash"] == c2["hashes"]["input_hash"]
    assert c1["hashes"]["output_hash"] == c2["hashes"]["output_hash"]


def test_v02_fields() -> None:
    claims = build_experiment_claims(
        experiment_num=1,
        researcher_id="agent",
        principal_id="did:key:z6Mk...",
        hypothesis="test",
        metric_value=1.0,
        decision="keep",
        commit_hash="abc123",
        policy_snapshot={"policy_v": "v0", "scopes": [], "constraints": {}},
    )
    assert claims["vc_profile"]["delegation_did"] == "did:key:z6Mk..."
    assert claims["protocol_refs"]["upstream_proof"] == "abc123"


def test_reason_codes() -> None:
    claims = build_experiment_claims(
        experiment_num=1, researcher_id="a", hypothesis="test",
        metric_name="val_bpb", metric_value=1.234, decision="keep",
        policy_snapshot={"policy_v": "v0", "scopes": [], "constraints": {}},
    )
    codes = claims["result"]["reason_codes"]
    assert "metric.val_bpb=1.234" in codes
    assert "decision.keep" in codes
