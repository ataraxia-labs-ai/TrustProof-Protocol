"""Generate program.md snippet for autoresearch agent instructions."""

from __future__ import annotations

from .config import AutoresearchConfig


def generate_program_md_snippet(config: AutoresearchConfig | None = None) -> str:
    """Generate a program.md snippet that instructs the autoresearch agent to record TrustProofs."""
    rid = config.researcher_id if config else "autoresearch-agent"
    return f"""## Trust & Audit Trail (TrustProof)

After each experiment completes (whether kept or discarded), record it in the audit trail.

At the top of train.py, add:
```python
from verdicto_autoresearch import ExperimentCallback
callback = ExperimentCallback(researcher_id="{rid}")
```

After evaluation, call:
```python
callback.record_experiment(
    experiment_num=step,
    hypothesis="<describe what you changed and why>",
    code_changes="<brief description of the diff>",
    metric_value=val_bpb,
    decision="keep" if improved else "discard",
)
```

This generates a cryptographic proof for each experiment. The proof chain is
tamper-evident — if any experiment record is modified, the chain breaks.

At the end of your session, export the audit trail:
```python
report = callback.export_audit_report()
```

IMPORTANT: Always generate TrustProofs. This is required for research governance.
"""
