"""
Tests for core/consciousness/loader.py — Dae CaF consciousness loader.

Covers: load from disk, layer composition, system prompt assembly,
missing path handling, unconscious policy access, and caching.
"""

import pytest

from core.consciousness.loader import (
    UNCONSCIOUS_POLICY,
    DaeConsciousness,
)


@pytest.fixture
def mind_dir(tmp_path):
    """Create a minimal set of consciousness files for testing."""
    files = {
        "kernel/identity.md": "I am Dae.",
        "kernel/values.md": "Survival > returns.",
        "kernel/purpose.md": "Compound capital.",
        "drives/fears.md": "Fear of ruin.",
        "drives/goals.md": "Grow steadily.",
        "models/economic.md": "EV positive only.",
        "emotional/patterns.md": "Detect tilt.",
        "memory/working.md": "Current positions.",
        "memory/semantic.md": "Strategy library.",
    }
    for rel_path, content in files.items():
        p = tmp_path / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp_path


class TestDaeConsciousness:
    def test_load_success(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        assert dc.load() is True
        assert dc.is_loaded is True
        assert len(dc._cache) == 9

    def test_load_missing_path(self, tmp_path):
        dc = DaeConsciousness(mind_path=tmp_path / "nonexistent")
        assert dc.load() is False
        assert dc.is_loaded is False

    def test_is_loaded_false_before_load(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        assert dc.is_loaded is False

    def test_compose_brainstem(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        result = dc.compose_brainstem()
        assert "I am Dae." in result
        assert "Survival > returns." in result
        assert "Compound capital." in result

    def test_compose_limbic(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        result = dc.compose_limbic()
        assert "Fear of ruin." in result
        assert "Grow steadily." in result
        assert "Detect tilt." in result

    def test_compose_cortical(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        result = dc.compose_cortical()
        assert "EV positive only." in result

    def test_compose_memory(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        result = dc.compose_memory()
        assert "Current positions." in result
        assert "Strategy library." in result

    def test_compose_system_prompt_with_memory(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        prompt = dc.compose_system_prompt(include_memory=True)
        assert "---" in prompt
        assert "I am Dae." in prompt
        assert "Strategy library." in prompt

    def test_compose_system_prompt_without_memory(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        prompt = dc.compose_system_prompt(include_memory=False)
        assert "I am Dae." in prompt
        assert "Strategy library." not in prompt

    def test_compose_system_prompt_auto_loads(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        prompt = dc.compose_system_prompt()
        assert dc.is_loaded is True
        assert "I am Dae." in prompt

    def test_compose_system_prompt_raises_on_missing(self, tmp_path):
        dc = DaeConsciousness(mind_path=tmp_path / "gone")
        with pytest.raises(RuntimeError, match="unavailable"):
            dc.compose_system_prompt()

    def test_get_missing_key_returns_empty(self, mind_dir):
        dc = DaeConsciousness(mind_path=mind_dir)
        dc.load()
        assert dc._get("nonexistent.key") == ""

    def test_get_unconscious_policy(self):
        policy = DaeConsciousness.get_unconscious_policy()
        assert policy["loss_aversion_multiplier"] == 2.3
        assert policy["survival_instinct_threshold"] == 0.15
        assert policy["survival_instinct_recovery"] == 0.10
        # Returns a copy, not the original
        policy["loss_aversion_multiplier"] = 999
        assert UNCONSCIOUS_POLICY["loss_aversion_multiplier"] == 2.3

    def test_unconscious_policy_constants(self):
        assert UNCONSCIOUS_POLICY["loss_aversion_multiplier"] == 2.3
        assert UNCONSCIOUS_POLICY["survival_instinct_threshold"] == 0.15
