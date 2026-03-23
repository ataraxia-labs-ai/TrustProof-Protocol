"""Tests for ExperimentCallback — real Ed25519 crypto, no mocks."""

from __future__ import annotations

from trustproof import verify

from verdicto_autoresearch import ExperimentCallback, AutoresearchConfig


def test_single_experiment_record() -> None:
    cb = ExperimentCallback(researcher_id="test-agent")
    jwt = cb.record_experiment(
        experiment_num=1,
        hypothesis="increase lr to 0.003",
        metric_value=1.234,
        decision="keep",
    )
    assert isinstance(jwt, str)
    assert jwt.count(".") == 2

    result = verify(jwt, cb._public_pem)
    assert result["ok"] is True
    assert result["claims"]["action"] == "autoresearch.experiment"


def test_lifecycle_hooks() -> None:
    cb = ExperimentCallback(researcher_id="hook-agent")
    cb.on_experiment_start(experiment_num=1, hypothesis="try dropout")
    jwt = cb.on_experiment_end(metric_value=1.5, decision="discard")

    result = verify(jwt, cb._public_pem)
    assert result["ok"] is True
    assert result["claims"]["result"]["decision"] == "deny"


def test_experiment_chain() -> None:
    cb = ExperimentCallback()
    for i in range(5):
        cb.record_experiment(
            experiment_num=i + 1,
            hypothesis=f"experiment {i + 1}",
            metric_value=2.0 - i * 0.1,
            decision="keep" if i % 2 == 0 else "discard",
        )

    chain = cb.get_proof_chain()
    assert len(chain) == 5

    result = cb.verify_chain()
    assert result["ok"] is True
    assert result["errors"] == []


def test_chain_tamper_detection() -> None:
    cb = ExperimentCallback()
    cb.record_experiment(experiment_num=1, hypothesis="exp1", metric_value=1.0, decision="keep")
    cb.record_experiment(experiment_num=2, hypothesis="exp2", metric_value=0.9, decision="keep")

    chain = cb.get_proof_chain()
    parts = chain[0].split(".")
    payload = bytearray(parts[1].encode())
    mid = len(payload) // 2
    payload[mid] = ord("X") if payload[mid] != ord("X") else ord("Y")
    tampered = f"{parts[0]}.{payload.decode()}.{parts[2]}"

    from trustproof import verify_chain as vc
    result = vc([tampered, chain[1]], cb._public_pem)
    assert result["ok"] is False


def test_keep_vs_discard() -> None:
    cb = ExperimentCallback()
    jwt_keep = cb.record_experiment(experiment_num=1, hypothesis="good", metric_value=1.0, decision="keep")
    jwt_discard = cb.record_experiment(experiment_num=2, hypothesis="bad", metric_value=2.0, decision="discard")

    r1 = verify(jwt_keep, cb._public_pem)
    r2 = verify(jwt_discard, cb._public_pem)
    assert r1["claims"]["result"]["decision"] == "allow"
    assert r2["claims"]["result"]["decision"] == "deny"


def test_summary() -> None:
    cb = ExperimentCallback(config=AutoresearchConfig(metric_name="val_bpb", metric_direction="lower"))
    cb.record_experiment(experiment_num=1, hypothesis="a", metric_value=1.5, decision="keep")
    cb.record_experiment(experiment_num=2, hypothesis="b", metric_value=1.2, decision="keep")
    cb.record_experiment(experiment_num=3, hypothesis="c", metric_value=1.8, decision="discard")

    summary = cb.get_summary()
    assert summary["total_experiments"] == 3
    assert summary["kept"] == 2
    assert summary["discarded"] == 1
    assert summary["best_metric"] == 1.2
    assert summary["chain_valid"] is True


def test_export_audit_report() -> None:
    cb = ExperimentCallback(researcher_id="report-agent")
    cb.record_experiment(experiment_num=1, hypothesis="test", metric_value=1.0, decision="keep")

    report = cb.export_audit_report()
    assert report["report_v"] == "0.1"
    assert report["summary"]["total_experiments"] == 1
    assert len(report["proofs"]) == 1
    assert report["config"]["researcher_id"] == "report-agent"


def test_auto_keygen() -> None:
    cb = ExperimentCallback()
    assert cb.config.private_key is not None
    assert cb._private_pem.startswith("-----BEGIN PRIVATE KEY-----")


def test_policy_in_proof() -> None:
    config = AutoresearchConfig(
        approved_scopes=["autoresearch.experiment"],
        max_experiments=50,
    )
    cb = ExperimentCallback(config=config)
    jwt = cb.record_experiment(experiment_num=1, hypothesis="test", metric_value=1.0, decision="keep")

    result = verify(jwt, cb._public_pem)
    policy = result["claims"]["policy"]
    assert policy["scopes"] == ["autoresearch.experiment"]
    assert policy["constraints"]["max_experiments"] == 50


def test_error_handling() -> None:
    cb = ExperimentCallback()
    cb.on_experiment_start(experiment_num=1, hypothesis="will fail")
    jwt = cb.on_experiment_error("OOM: GPU ran out of memory")

    result = verify(jwt, cb._public_pem)
    assert result["ok"] is True
    assert result["claims"]["result"]["decision"] == "deny"


def test_context_manager() -> None:
    with ExperimentCallback(researcher_id="ctx-agent") as cb:
        cb.record_experiment(experiment_num=1, hypothesis="test", metric_value=1.0, decision="keep")
        assert len(cb.get_proof_chain()) == 1
