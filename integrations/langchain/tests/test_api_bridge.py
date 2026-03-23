"""Tests for the Verdicto API bridge integration.

Uses unittest.mock to mock the VerdictoClient — we test bridge logic,
not HTTP (that's covered by the verdicto client tests).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig


def test_api_bridge_disabled_by_default() -> None:
    """Handler with no API config → _api_bridge is None."""
    handler = VerdictoCallbackHandler()
    assert handler._api_bridge is None


def test_api_bridge_enabled_with_config() -> None:
    """Handler with api_url + api_key → _api_bridge is enabled."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
    )
    handler = VerdictoCallbackHandler(config=config)
    assert handler._api_bridge is not None
    assert handler._api_bridge.enabled is True
    handler.close()


def test_api_bridge_lazy_client_init() -> None:
    """Client is not created until first _get_client call."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
    )
    handler = VerdictoCallbackHandler(config=config)
    assert handler._api_bridge is not None
    assert handler._api_bridge._client is None  # not yet created
    handler.close()


def test_api_bridge_issues_agent_pass_once() -> None:
    """Multiple send_verification calls → issue_agent_pass called only once."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
        api_send_async=False,
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    # Mock the client
    mock_client = MagicMock()

    @dataclass
    class FakePass:
        agent_pass: str = "eyJ.fake.pass"

    @dataclass
    class FakeResult:
        decision: str = "allow"
        verification_id: str = "ver_1"

    mock_client.issue_agent_pass.return_value = FakePass()
    mock_client.verify_agent.return_value = FakeResult()
    bridge._client = mock_client

    # Two sends — issue should be called once
    bridge.send_verification(action="langchain.tool_call.search")
    bridge.send_verification(action="langchain.tool_call.checkout")

    assert mock_client.issue_agent_pass.call_count == 1
    assert mock_client.verify_agent.call_count == 2
    handler.close()


def test_api_bridge_send_verification_on_tool_end() -> None:
    """on_tool_start + on_tool_end → bridge.send_verification called."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
        api_send_async=False,
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    # Mock bridge.send_verification
    bridge.send_verification = MagicMock()

    rid = uuid.uuid4()
    handler.on_tool_start({"name": "search"}, "running shoes", run_id=rid)
    handler.on_tool_end("Nike Air Max", run_id=rid)

    assert bridge.send_verification.call_count == 1
    call_kwargs = bridge.send_verification.call_args
    assert "langchain.tool_call.search" in str(call_kwargs)

    # Local proof chain still works
    assert len(handler.get_proof_chain()) == 1
    handler.close()


def test_api_bridge_fail_silently() -> None:
    """API failure with fail_silently=True → no crash, warning logged."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
        api_send_async=False,
        api_fail_silently=True,
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    # Mock client that raises on verify_agent
    mock_client = MagicMock()

    @dataclass
    class FakePass:
        agent_pass: str = "eyJ.fake.pass"

    mock_client.issue_agent_pass.return_value = FakePass()
    mock_client.verify_agent.side_effect = ConnectionError("API unreachable")
    bridge._client = mock_client

    # Should not crash
    bridge.send_verification(action="langchain.tool_call.test")

    # Local proof chain still works
    rid = uuid.uuid4()
    handler.on_tool_start({"name": "test"}, "data", run_id=rid)
    handler.on_tool_end("result", run_id=rid)
    assert len(handler.get_proof_chain()) == 1
    handler.close()


def test_api_bridge_sync_mode() -> None:
    """api_send_async=False → send_verification runs synchronously."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
        api_send_async=False,
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    mock_client = MagicMock()

    @dataclass
    class FakePass:
        agent_pass: str = "eyJ.fake.pass"

    @dataclass
    class FakeResult:
        decision: str = "allow"
        verification_id: str = "ver_sync"

    mock_client.issue_agent_pass.return_value = FakePass()
    mock_client.verify_agent.return_value = FakeResult()
    bridge._client = mock_client

    bridge.send_verification(action="test.action")
    # Synchronous — verify was called by now
    assert mock_client.verify_agent.call_count == 1
    handler.close()


def test_local_proofs_still_generated_with_api() -> None:
    """Even with API enabled, local proof chain is complete and valid."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
        api_send_async=False,
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    # Mock bridge to do nothing (we're testing local proofs work)
    bridge.send_verification = MagicMock()

    for i, name in enumerate(["step1", "step2", "step3"]):
        rid = uuid.uuid4()
        handler.on_tool_start({"name": name}, f"input_{i}", run_id=rid)
        handler.on_tool_end(f"output_{i}", run_id=rid)

    chain = handler.get_proof_chain()
    assert len(chain) == 3

    result = handler.verify_chain()
    assert result["ok"] is True
    assert result["errors"] == []
    handler.close()


def test_close_cleans_up_bridge() -> None:
    """handler.close() → bridge client close called."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
    )
    handler = VerdictoCallbackHandler(config=config)
    bridge = handler._api_bridge
    assert bridge is not None

    mock_client = MagicMock()
    bridge._client = mock_client

    handler.close()
    mock_client.close.assert_called_once()


def test_context_manager_closes_bridge() -> None:
    """with handler: → close called on exit."""
    config = VerdictoConfig(
        verdicto_api_url="http://localhost:8000",
        verdicto_api_key="vk_test_key",
    )
    with VerdictoCallbackHandler(config=config) as handler:
        bridge = handler._api_bridge
        assert bridge is not None
        mock_client = MagicMock()
        bridge._client = mock_client

    mock_client.close.assert_called_once()


def test_api_enabled_property() -> None:
    """api_enabled returns False when only url is set, True when both are set."""
    config_url_only = VerdictoConfig(verdicto_api_url="http://localhost:8000")
    assert config_url_only.api_enabled is False

    config_key_only = VerdictoConfig(verdicto_api_key="vk_test")
    assert config_key_only.api_enabled is False

    config_both = VerdictoConfig(
        verdicto_api_url="http://localhost:8000", verdicto_api_key="vk_test"
    )
    assert config_both.api_enabled is True

    config_neither = VerdictoConfig()
    assert config_neither.api_enabled is False
