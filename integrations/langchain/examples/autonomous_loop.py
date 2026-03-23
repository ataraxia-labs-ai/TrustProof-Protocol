"""TrustProof-enabled autonomous experiment loop (autoresearch pattern).

Every experiment gets a signed, chained proof. The final report includes
a complete cryptographic audit trail.

Inspired by Karpathy's autoresearch — but with verifiable provenance.
"""

import uuid

from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig

config = VerdictoConfig(
    agent_id="autoresearch-optimizer-v1",
    policy_scopes=["autoresearch.experiment", "autoresearch.code_modification"],
)
handler = VerdictoCallbackHandler(config=config)

# Simulate an experiment loop
experiments = [
    ("modify_train_py", "learning_rate=0.001", "val_bpb: 1.234, decision: keep"),
    ("modify_train_py", "batch_size=64", "val_bpb: 1.198, decision: keep"),
    ("modify_train_py", "dropout=0.3", "val_bpb: 1.301, decision: revert"),
    ("run_evaluation", "full_benchmark", "score: 87.2, baseline: 85.1"),
]

for tool_name, input_data, output_data in experiments:
    rid = uuid.uuid4()
    handler.on_tool_start({"name": tool_name}, input_data, run_id=rid)
    handler.on_tool_end(output_data, run_id=rid)

# Export the complete audit trail
bundle = handler.export_bundle()
verification = handler.verify_chain()

print(f"Completed {bundle['proof_count']} experiments")
print(f"Chain integrity: {'VALID' if verification['ok'] else 'BROKEN'}")
print(f"Bundle: {len(handler.export_json())} bytes")
