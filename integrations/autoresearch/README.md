# verdicto-autoresearch

Cryptographic audit trails for autonomous AI research. Every experiment signed. Every hypothesis recorded. Every decision tamper-evident.

[![PyPI](https://img.shields.io/pypi/v/verdicto-autoresearch)](https://pypi.org/project/verdicto-autoresearch/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/LICENSE)

## The Problem

Karpathy's autoresearch runs 700 experiments overnight. Shopify CEO got 19% performance gains from 37 automated experiments. But when an autonomous agent modifies model code, trains it, and decides what to keep:

- Who authorized this research scope?
- Did the agent stay within the approved search space?
- Can you reproduce experiment #347?
- If an agent discovers a dangerous capability, is there an audit trail?

## The Solution

**verdicto-autoresearch** generates a TrustProof for every experiment:

- **Signed** (Ed25519) — cryptographically attributable to a specific researcher/agent
- **Chain-linked** — tamper with one proof and the entire chain breaks
- **Policy-aware** — records approved scope, constraints, and metric targets
- **Git-integrated** — includes code diff hashes for reproducibility

## Install

```bash
pip install verdicto-autoresearch
```

## Add to any experiment loop (3 lines)

```python
from verdicto_autoresearch import ExperimentCallback

callback = ExperimentCallback(researcher_id="my-agent")

# In your loop:
callback.record_experiment(
    experiment_num=step,
    hypothesis="increase learning rate",
    code_changes="lr: 3e-4 -> 1e-3",
    metric_value=val_bpb,
    decision="keep" if improved else "discard",
)
```

## Verify the chain

```python
result = callback.verify_chain()
assert result["ok"]  # Entire experiment history is intact

summary = callback.get_summary()
print(f"Experiments: {summary['total_experiments']}, Best: {summary['best_metric']}")
```

## Configuration

```python
from verdicto_autoresearch import ExperimentCallback, AutoresearchConfig

config = AutoresearchConfig(
    researcher_id="gpt-4o-researcher",
    principal_id="human:alice@lab.org",      # KYH: who authorized this
    metric_name="val_bpb",
    metric_direction="lower",
    max_experiments=500,
    allowed_file_modifications=["train.py"],
    track_git=True,                          # Include git diff hashes
)

callback = ExperimentCallback(config=config)
```

## For autoresearch specifically

Generate a `program.md` snippet:

```python
from verdicto_autoresearch import generate_program_md_snippet
print(generate_program_md_snippet())
```

Paste the output into your `program.md` — the agent will record TrustProofs automatically.

## Export audit report

```python
report = callback.export_audit_report()
# Contains: summary, all proofs, config snapshot
```

## Optional: Dashboard

Connect to Verdicto API for real-time monitoring:

```python
config = AutoresearchConfig(
    verdicto_api_url="http://127.0.0.1:8000",
    verdicto_api_key="vk_...",
)
```

## Part of TrustProof Protocol

Open standard: [github.com/ataraxia-labs-ai/TrustProof-Protocol](https://github.com/ataraxia-labs-ai/TrustProof-Protocol)

## License

Apache-2.0
