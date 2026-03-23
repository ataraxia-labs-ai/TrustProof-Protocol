"""Demonstrate TrustProof generation for autonomous experiment loops.
No GPU, no autoresearch installation needed — just the proof pattern."""

from verdicto_autoresearch import ExperimentCallback, AutoresearchConfig

config = AutoresearchConfig(
    researcher_id="demo-researcher-v1",
    principal_id="human:edd@ataraxialab.ai",
    metric_name="val_bpb",
    metric_direction="lower",
    max_experiments=100,
    allowed_file_modifications=["train.py"],
    track_git=False,
)

callback = ExperimentCallback(config=config)

experiments = [
    {"num": 1, "hypothesis": "Baseline: lr=3e-4, d_model=256", "metric": 1.892, "decision": "keep"},
    {"num": 2, "hypothesis": "Increase lr to 1e-3", "metric": 1.756, "decision": "keep"},
    {"num": 3, "hypothesis": "Add dropout=0.1", "metric": 1.801, "decision": "discard"},
    {"num": 4, "hypothesis": "Wider model d_model=512", "metric": 1.698, "decision": "keep"},
    {"num": 5, "hypothesis": "Switch to Muon optimizer", "metric": 1.652, "decision": "keep"},
]

print("=" * 60)
print("AUTORESEARCH TRUST PROOF DEMO")
print("=" * 60)

for exp in experiments:
    proof = callback.record_experiment(
        experiment_num=exp["num"],
        hypothesis=exp["hypothesis"],
        code_changes=f"Modified train.py: {exp['hypothesis']}",
        metric_value=exp["metric"],
        decision=exp["decision"],
    )
    status = "KEPT" if exp["decision"] == "keep" else "DISCARDED"
    print(f"\nExperiment {exp['num']}: {exp['hypothesis']}")
    print(f"  val_bpb: {exp['metric']:.3f} -> {status}")
    print(f"  Proof: {proof[:50]}...")

result = callback.verify_chain()
summary = callback.get_summary()

print(f"\n{'=' * 60}")
print("AUDIT TRAIL SUMMARY")
print(f"{'=' * 60}")
print(f"Total experiments: {summary['total_experiments']}")
print(f"Kept: {summary['kept']}, Discarded: {summary['discarded']}")
print(f"Best {config.metric_name}: {summary['best_metric']:.3f}")
print(f"Chain integrity: {'VALID' if result['ok'] else 'BROKEN'} ({len(callback.get_proof_chain())} proofs)")
print(f"\nEvery experiment is cryptographically signed and chain-linked.")
print(f"Tamper with any proof and the entire chain breaks.")
