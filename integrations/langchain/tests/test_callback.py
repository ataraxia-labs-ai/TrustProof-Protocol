"""Tests for VerdictoCallbackHandler — real crypto, no mocks."""

from __future__ import annotations

import json
import threading
import uuid

from trustproof import verify

from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig


def _make_handler(**kwargs) -> VerdictoCallbackHandler:
    return VerdictoCallbackHandler(**kwargs)


def test_tool_call_generates_valid_proof() -> None:
    handler = _make_handler(agent_id="test-agent")
    run_id = uuid.uuid4()

    handler.on_tool_start({"name": "search"}, "running shoes", run_id=run_id)
    handler.on_tool_end("Nike Air Max - $120", run_id=run_id)

    chain = handler.get_proof_chain()
    assert len(chain) == 1

    result = verify(chain[0], handler._public_pem)
    assert result["ok"] is True
    claims = result["claims"]
    assert claims["action"] == "langchain.tool_call.search"
    assert claims["result"]["decision"] == "allow"
    assert claims["subject"]["id"] == "test-agent"
    assert claims["subject"]["type"] == "agent"


def test_tool_error_generates_deny_proof() -> None:
    handler = _make_handler()
    run_id = uuid.uuid4()

    handler.on_tool_start({"name": "api_call"}, "request data", run_id=run_id)
    handler.on_tool_error(RuntimeError("Connection timeout"), run_id=run_id)

    chain = handler.get_proof_chain()
    assert len(chain) == 1

    result = verify(chain[0], handler._public_pem)
    assert result["ok"] is True
    assert result["claims"]["result"]["decision"] == "deny"
    assert "tool_error" in result["claims"]["result"]["reason_codes"]


def test_chain_building_three_tools() -> None:
    handler = _make_handler()

    for i, tool_name in enumerate(["search", "checkout", "confirm"]):
        rid = uuid.uuid4()
        handler.on_tool_start({"name": tool_name}, f"input_{i}", run_id=rid)
        handler.on_tool_end(f"output_{i}", run_id=rid)

    chain = handler.get_proof_chain()
    assert len(chain) == 3

    chain_result = handler.verify_chain()
    assert chain_result["ok"] is True
    assert chain_result["errors"] == []


def test_tamper_detection() -> None:
    handler = _make_handler()

    rid1 = uuid.uuid4()
    handler.on_tool_start({"name": "step1"}, "input1", run_id=rid1)
    handler.on_tool_end("output1", run_id=rid1)

    rid2 = uuid.uuid4()
    handler.on_tool_start({"name": "step2"}, "input2", run_id=rid2)
    handler.on_tool_end("output2", run_id=rid2)

    chain = handler.get_proof_chain()
    assert len(chain) == 2

    # Tamper with the first proof
    parts = chain[0].split(".")
    payload_bytes = bytearray(parts[1].encode())
    if payload_bytes[-1] == ord("A"):
        payload_bytes[-1] = ord("B")
    else:
        payload_bytes[-1] = ord("A")
    tampered = f"{parts[0]}.{payload_bytes.decode()}.{parts[2]}"

    from trustproof import verify_chain as vc

    result = vc([tampered, chain[1]], handler._public_pem)
    assert result["ok"] is False


def test_thread_safety() -> None:
    handler = _make_handler()
    errors: list[Exception] = []

    def run_tool(i: int) -> None:
        try:
            rid = uuid.uuid4()
            handler.on_tool_start({"name": f"tool_{i}"}, f"input_{i}", run_id=rid)
            handler.on_tool_end(f"output_{i}", run_id=rid)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run_tool, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(handler.get_proof_chain()) == 10


def test_config_defaults() -> None:
    handler = _make_handler()
    assert handler.config.agent_id == "langchain-agent"
    assert handler.config.private_key is not None
    assert handler.config.public_key is not None
    assert handler._private_pem.startswith("-----BEGIN PRIVATE KEY-----")


def test_protocol_refs_pass_through() -> None:
    config = VerdictoConfig(
        protocol_refs={"ap2_mandate_id": "mandate_123", "ap2_mandate_type": "cart"},
    )
    handler = VerdictoCallbackHandler(config=config)
    rid = uuid.uuid4()
    handler.on_tool_start({"name": "buy"}, "shoes", run_id=rid)
    handler.on_tool_end("purchased", run_id=rid)

    chain = handler.get_proof_chain()
    result = verify(chain[0], handler._public_pem)
    assert result["ok"] is True
    assert result["claims"]["protocol_refs"]["ap2_mandate_id"] == "mandate_123"


def test_export_bundle() -> None:
    handler = _make_handler()
    rid = uuid.uuid4()
    handler.on_tool_start({"name": "test"}, "data", run_id=rid)
    handler.on_tool_end("result", run_id=rid)

    bundle = handler.export_bundle()
    assert bundle["bundle_v"] == "0.1"
    assert bundle["proof_count"] == 1
    assert len(bundle["proofs"]) == 1

    json_str = handler.export_json()
    parsed = json.loads(json_str)
    assert len(parsed) == 1


def test_clear_resets_state() -> None:
    handler = _make_handler()
    rid = uuid.uuid4()
    handler.on_tool_start({"name": "test"}, "data", run_id=rid)
    handler.on_tool_end("result", run_id=rid)
    assert len(handler.get_proof_chain()) == 1

    handler.clear()
    assert len(handler.get_proof_chain()) == 0


def test_chain_step_tracing() -> None:
    config = VerdictoConfig(trace_chain_steps=True)
    handler = VerdictoCallbackHandler(config=config)
    rid = uuid.uuid4()
    handler.on_chain_start({"name": "AgentExecutor"}, {"input": "test"}, run_id=rid)
    handler.on_chain_end({"output": "result"}, run_id=rid)

    chain = handler.get_proof_chain()
    assert len(chain) == 1
    result = verify(chain[0], handler._public_pem)
    assert result["ok"] is True
    assert "chain_step" in result["claims"]["action"]
