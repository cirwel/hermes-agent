"""The Codex OAuth base URL outranks the provider label in the api_mode ladder.

``_resolve_api_mode`` used to rank ``agent.provider`` above the URL check, and
guarded the URL check with ``provider_name is None``. A live Codex endpoint
reached with a stale provider label therefore resolved to the wrong wire, while
an explicitly passed label suppressed the URL check outright.
"""

from types import SimpleNamespace

import pytest

from agent.agent_init import _resolve_api_mode

CODEX_URL = "https://chatgpt.com/backend-api/codex"


def _agent(provider):
    return SimpleNamespace(
        provider=provider,
        api_mode=None,
        _base_url_hostname="chatgpt.com",
        _base_url_lower=CODEX_URL,
    )


@pytest.mark.parametrize("stale_provider", ["anthropic", "openai", "xai", "nous", None])
def test_codex_url_wins_over_a_stale_provider_label(stale_provider):
    """Whatever the label says, a Codex OAuth URL routes as Codex."""
    agent = _agent(stale_provider)
    _resolve_api_mode(agent, None, stale_provider, CODEX_URL)
    assert agent.api_mode == "codex_responses"
    assert agent.provider == "openai-codex"


def test_codex_url_wins_even_when_provider_name_is_passed():
    """The old ``provider_name is None`` guard suppressed the URL check entirely."""
    agent = _agent("anthropic")
    _resolve_api_mode(agent, None, "anthropic", CODEX_URL)
    assert agent.api_mode == "codex_responses"
    assert agent.provider == "openai-codex"


def test_explicit_api_mode_still_outranks_the_url():
    """The explicit escape hatch stays one rung above the URL check."""
    agent = _agent("anthropic")
    _resolve_api_mode(agent, "anthropic_messages", "anthropic", CODEX_URL)
    assert agent.api_mode == "anthropic_messages"
    assert agent.provider == "anthropic"


def test_non_codex_url_leaves_the_provider_label_in_charge():
    """The reorder must not capture endpoints that are not Codex."""
    agent = SimpleNamespace(
        provider="xai",
        api_mode=None,
        _base_url_hostname="api.x.ai",
        _base_url_lower="https://api.x.ai/v1",
    )
    _resolve_api_mode(agent, None, None, "https://api.x.ai/v1")
    assert agent.api_mode == "codex_responses"
    assert agent.provider == "xai"
