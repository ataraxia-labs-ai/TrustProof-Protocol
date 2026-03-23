"""ExperimentCallback — TrustProof generation for autonomous experiment loops.

Generates signed, chained proofs for every experiment in an autoresearch-style loop.
"""

from __future__ import annotations

from typing import Any

from .api_bridge import APIBridge
from .config import AutoresearchConfig, ensure_keypair
from .experiment_proof import build_experiment_claims
from .git_integration import get_diff_hash, get_latest_commit_hash
from .proof_chain import ProofChain


class ExperimentCallback:
    """Generates chained TrustProofs for autonomous experiment loops.

    Usage (3 lines)::

        from verdicto_autoresearch import ExperimentCallback
        callback = ExperimentCallback(researcher_id="my-agent")
        callback.record_experiment(
            experiment_num=1,
            hypothesis="increase lr to 0.003",
            metric_value=1.234,
            decision="keep",
        )

    Or use lifecycle hooks::

        callback.on_experiment_start(experiment_num=1, hypothesis="increase lr")
        # ... run experiment ...
        callback.on_experiment_end(metric_value=1.234, decision="keep")
    """

    def __init__(
        self,
        config: AutoresearchConfig | None = None,
        *,
        researcher_id: str | None = None,
    ) -> None:
        self.config = config or AutoresearchConfig()
        if researcher_id is not None:
            self.config.researcher_id = researcher_id

        self._private_pem, self._public_pem = ensure_keypair(self.config)
        self._chain = ProofChain()
        self._pending: dict[str, Any] | None = None
        self._kept = 0
        self._discarded = 0
        self._best_metric: float | None = None
        self._api_bridge: APIBridge | None = (
            APIBridge(self.config) if self.config.api_enabled else None
        )

    # ── Lifecycle hooks ─────────────────────────────────────────────

    def on_experiment_start(
        self,
        experiment_num: int,
        hypothesis: str,
        code_changes: str | None = None,
    ) -> None:
        """Record the start of an experiment. Call on_experiment_end after."""
        diff_hash = None
        if self.config.track_git:
            for f in self.config.allowed_file_modifications:
                diff_hash = get_diff_hash(self.config.repo_path, f)
                if diff_hash:
                    break

        self._pending = {
            "experiment_num": experiment_num,
            "hypothesis": hypothesis,
            "code_changes": code_changes,
            "code_diff_hash": diff_hash,
        }

    def on_experiment_end(
        self,
        metric_value: float | None = None,
        decision: str = "discard",
        commit_hash: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Finalize the experiment and generate a chained TrustProof. Returns JWT."""
        if self._pending is None:
            raise RuntimeError("on_experiment_start must be called before on_experiment_end")

        if commit_hash is None and self.config.track_git and decision == "keep":
            commit_hash = get_latest_commit_hash(self.config.repo_path)

        jwt_token = self._sign_experiment(
            experiment_num=self._pending["experiment_num"],
            hypothesis=self._pending["hypothesis"],
            code_changes=self._pending.get("code_changes"),
            code_diff_hash=self._pending.get("code_diff_hash"),
            metric_value=metric_value,
            decision=decision,
            commit_hash=commit_hash,
            notes=notes,
        )
        self._pending = None
        return jwt_token

    def on_experiment_error(self, error_message: str) -> str:
        """Record a failed experiment. Returns JWT."""
        if self._pending is None:
            raise RuntimeError("on_experiment_start must be called before on_experiment_error")

        jwt_token = self._sign_experiment(
            experiment_num=self._pending["experiment_num"],
            hypothesis=self._pending["hypothesis"],
            code_changes=self._pending.get("code_changes"),
            code_diff_hash=self._pending.get("code_diff_hash"),
            metric_value=None,
            decision="error",
            commit_hash=None,
            notes=error_message,
        )
        self._pending = None
        return jwt_token

    # ── Convenience method ──────────────────────────────────────────

    def record_experiment(
        self,
        experiment_num: int,
        hypothesis: str,
        code_changes: str | None = None,
        metric_value: float | None = None,
        decision: str = "discard",
        commit_hash: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Record a complete experiment in one call. Returns the signed proof JWT."""
        diff_hash = None
        if self.config.track_git:
            for f in self.config.allowed_file_modifications:
                diff_hash = get_diff_hash(self.config.repo_path, f)
                if diff_hash:
                    break

        return self._sign_experiment(
            experiment_num=experiment_num,
            hypothesis=hypothesis,
            code_changes=code_changes,
            code_diff_hash=diff_hash,
            metric_value=metric_value,
            decision=decision,
            commit_hash=commit_hash,
            notes=notes,
        )

    # ── Core signing ────────────────────────────────────────────────

    def _sign_experiment(
        self,
        *,
        experiment_num: int,
        hypothesis: str,
        code_changes: str | None,
        code_diff_hash: str | None,
        metric_value: float | None,
        decision: str,
        commit_hash: str | None,
        notes: str | None,
    ) -> str:
        claims = build_experiment_claims(
            experiment_num=experiment_num,
            researcher_id=self.config.researcher_id,
            principal_id=self.config.principal_id,
            hypothesis=hypothesis,
            code_changes=code_changes,
            code_diff_hash=code_diff_hash,
            metric_name=self.config.metric_name,
            metric_value=metric_value,
            decision=decision,
            commit_hash=commit_hash,
            policy_snapshot=self.config.get_policy_snapshot(),
            session_id=self.config.session_id,
            notes=notes,
        )

        jwt_token = self._chain.append_proof(claims, self._private_pem)

        # Track stats
        if decision == "keep":
            self._kept += 1
        else:
            self._discarded += 1

        if metric_value is not None:
            if self._best_metric is None:
                self._best_metric = metric_value
            elif self.config.metric_direction == "lower":
                self._best_metric = min(self._best_metric, metric_value)
            else:
                self._best_metric = max(self._best_metric, metric_value)

        # API bridge (non-blocking)
        if self._api_bridge is not None:
            self._api_bridge.send_verification(
                action="autoresearch.experiment",
                context={
                    "experiment_num": experiment_num,
                    "hypothesis": hypothesis,
                    "decision": decision,
                    "metric_value": metric_value,
                },
            )

        return jwt_token

    # ── Public API ──────────────────────────────────────────────────

    def get_proof_chain(self) -> list[str]:
        """Return all signed proof JWTs in order."""
        return self._chain.get_chain()

    def verify_chain(self) -> dict[str, Any]:
        """Verify the entire proof chain for tamper evidence."""
        return self._chain.verify(self._public_pem)

    def get_summary(self) -> dict[str, Any]:
        """Get experiment session summary."""
        chain = self._chain.get_chain()
        result = self._chain.verify(self._public_pem)
        return {
            "total_experiments": len(chain),
            "kept": self._kept,
            "discarded": self._discarded,
            "best_metric": self._best_metric,
            "chain_valid": result["ok"],
            "researcher_id": self.config.researcher_id,
            "metric_name": self.config.metric_name,
        }

    def export_audit_report(self) -> dict[str, Any]:
        """Export full audit report with proofs + metadata."""
        return {
            "report_v": "0.1",
            "summary": self.get_summary(),
            "proofs": self._chain.get_chain(),
            "config": {
                "researcher_id": self.config.researcher_id,
                "principal_id": self.config.principal_id,
                "session_id": self.config.session_id,
                "approved_scopes": self.config.approved_scopes,
                "metric_name": self.config.metric_name,
                "metric_direction": self.config.metric_direction,
            },
        }

    def close(self) -> None:
        """Cleanup."""
        if self._api_bridge is not None:
            self._api_bridge.close()

    def __enter__(self) -> ExperimentCallback:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
