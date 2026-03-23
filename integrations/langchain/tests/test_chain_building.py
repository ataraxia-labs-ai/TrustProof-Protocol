"""Tests for chain building and verification across multiple tool calls."""

from __future__ import annotations

import uuid

from trustproof import verify_chain as tp_verify_chain

from verdicto_langchain import VerdictoCallbackHandler


def test_chain_integrity_across_many_steps() -> None:
    handler = VerdictoCallbackHandler(agent_id="chain-test-agent")

    for i in range(5):
        rid = uuid.uuid4()
        handler.on_tool_start({"name": f"step_{i}"}, f"input_{i}", run_id=rid)
        handler.on_tool_end(f"output_{i}", run_id=rid)

    chain = handler.get_proof_chain()
    assert len(chain) == 5

    result = handler.verify_chain()
    assert result["ok"] is True

    # Also verify using the trustproof SDK directly
    direct_result = tp_verify_chain(chain, handler._public_pem)
    assert direct_result["ok"] is True


def test_mixed_success_and_error_chain() -> None:
    handler = VerdictoCallbackHandler()

    rid1 = uuid.uuid4()
    handler.on_tool_start({"name": "search"}, "query", run_id=rid1)
    handler.on_tool_end("results", run_id=rid1)

    rid2 = uuid.uuid4()
    handler.on_tool_start({"name": "api_call"}, "request", run_id=rid2)
    handler.on_tool_error(ValueError("bad request"), run_id=rid2)

    rid3 = uuid.uuid4()
    handler.on_tool_start({"name": "fallback"}, "retry", run_id=rid3)
    handler.on_tool_end("success", run_id=rid3)

    chain = handler.get_proof_chain()
    assert len(chain) == 3

    result = handler.verify_chain()
    assert result["ok"] is True


def test_export_and_reimport() -> None:
    handler = VerdictoCallbackHandler()

    rid = uuid.uuid4()
    handler.on_tool_start({"name": "test"}, "data", run_id=rid)
    handler.on_tool_end("result", run_id=rid)

    bundle = handler.export_bundle()
    assert bundle["proof_count"] == 1

    # Verify the exported chain independently
    result = tp_verify_chain(bundle["proofs"], handler._public_pem)
    assert result["ok"] is True
