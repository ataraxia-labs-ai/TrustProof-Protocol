"""Tests for program.md snippet generation."""

from verdicto_autoresearch import AutoresearchConfig, generate_program_md_snippet


def test_generates_markdown() -> None:
    snippet = generate_program_md_snippet()
    assert "## Trust & Audit Trail" in snippet
    assert "ExperimentCallback" in snippet
    assert "record_experiment" in snippet


def test_includes_config() -> None:
    config = AutoresearchConfig(researcher_id="custom-agent-v2")
    snippet = generate_program_md_snippet(config)
    assert "custom-agent-v2" in snippet
