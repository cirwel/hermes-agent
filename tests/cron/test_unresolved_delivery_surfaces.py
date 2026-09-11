"""A non-local cron job with no resolvable target must not look successful.

``_unresolved_delivery_outcome`` returned None for every ``deliver=origin`` job,
silencing two different situations. Legacy CLI provenance (a free-form string in
``origin``) genuinely is local-only and should stay quiet. A missing origin is a
delivery request that resolved to nothing, and reporting that as a clean run hid
the fact that output only ever reached disk.
"""

import pytest

from cron.scheduler_delivery import _unresolved_delivery_outcome


def test_local_jobs_stay_silent():
    assert _unresolved_delivery_outcome({"deliver": "local"}, False) is None


@pytest.mark.parametrize("provenance", ["cli:session-abc", "tui", "local-session"])
def test_legacy_string_origin_stays_silent(provenance):
    """#43014: free-form provenance means local-only, not a failure."""
    job = {"id": "j1", "deliver": "origin", "origin": provenance}
    assert _unresolved_delivery_outcome(job, False) is None


@pytest.mark.parametrize("missing", [None, "", {}])
def test_missing_origin_surfaces_as_an_error(missing):
    """Delivery was requested and nothing resolved — say so."""
    job = {"id": "j2", "deliver": "origin", "origin": missing}
    outcome = _unresolved_delivery_outcome(job, False)
    assert outcome is not None
    assert "no delivery target resolved" in outcome
    assert "output saved locally only" in outcome


def test_absent_origin_key_surfaces_as_an_error():
    outcome = _unresolved_delivery_outcome({"id": "j3", "deliver": "origin"}, False)
    assert outcome is not None
    assert "no delivery target resolved" in outcome
