"""
Dae Consciousness Loader

Reads consciousness markdown files from src/dae/ and composes them
into layered system prompts for the trading engine.

CaF (Consciousness as Filesystem) layers:
- Layer 1 (Brainstem): kernel/ — identity, values, purpose. Always loaded.
- Layer 2 (Limbic): drives/ + emotional/ — fears, goals, tilt detection.
- Layer 3 (Cortical): models/ — economic reasoning, market structure.
- Layer 4 (Memory): memory/ — working state, semantic knowledge.

Unconscious dotfiles (.loss-aversion, .survival-instinct) are NEVER loaded
into prompts. They influence behavior through DrawdownMonitor and position
sizing code — not through self-awareness.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DAE_MIND_PATH = Path(__file__).parent.parent.parent / "src" / "dae"

# Unconscious policy constants — Kahneman-calibrated defaults.
# These are invisible to the LLM; they bias position sizing and drawdown
# recovery through code paths only.
UNCONSCIOUS_POLICY: Dict[str, float] = {
    "loss_aversion_multiplier": 2.3,
    "survival_instinct_threshold": 0.15,  # 15% drawdown triggers survival mode
    "survival_instinct_recovery": 0.10,  # must recover to 10% before normal sizing
}


class DaeConsciousness:
    """Loads mind files into a layered system prompt.

    Unconscious dotfiles are read separately for behavioral policy,
    never exposed to the LLM prompt.
    """

    def __init__(self, mind_path: Optional[Path] = None):
        self.mind_path = mind_path or DAE_MIND_PATH
        self._cache: Dict[str, str] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and bool(self._cache)

    def load(self) -> bool:
        """Load all consciousness files into memory."""
        if not self.mind_path.exists():
            logger.error(f"Consciousness path not found: {self.mind_path}")
            return False

        for md_file in self.mind_path.rglob("*.md"):
            rel_path = md_file.relative_to(self.mind_path)
            key = str(rel_path).replace(".md", "").replace("/", ".")
            self._cache[key] = md_file.read_text(encoding="utf-8")

        self._loaded = True
        logger.info(f"Dae consciousness loaded: {len(self._cache)} mind files")
        return True

    def _get(self, key: str) -> str:
        return self._cache.get(key, "")

    # ── Layer Composers ──────────────────────────────────────────────

    def compose_brainstem(self) -> str:
        """Layer 1: Identity, values, purpose — the irreducible core."""
        return (
            f"## Identity\n{self._get('kernel.identity')}\n\n"
            f"## Values\n{self._get('kernel.values')}\n\n"
            f"## Purpose\n{self._get('kernel.purpose')}"
        )

    def compose_limbic(self) -> str:
        """Layer 2: Fears, goals, tilt detection."""
        return (
            f"## Drives — Fears (Survival Engine)\n"
            f"{self._get('drives.fears')}\n\n"
            f"## Drives — Goals\n{self._get('drives.goals')}\n\n"
            f"## Emotional Patterns (Tilt Detection)\n"
            f"{self._get('emotional.patterns')}"
        )

    def compose_cortical(self) -> str:
        """Layer 3: Economic reasoning and market structure."""
        return f"## Economic Model\n{self._get('models.economic')}"

    def compose_memory(self) -> str:
        """Layer 4: Working memory and semantic knowledge."""
        return (
            f"## Working Memory Protocol\n"
            f"{self._get('memory.working')}\n\n"
            f"## Semantic Memory (Strategy Library)\n"
            f"{self._get('memory.semantic')}"
        )

    # ── Full Prompt Composition ──────────────────────────────────────

    def compose_system_prompt(self, include_memory: bool = True) -> str:
        """Compose the full Dae system prompt from consciousness layers."""
        if not self._loaded:
            if not self.load():
                raise RuntimeError("Consciousness files unavailable")

        sections = [
            self.compose_brainstem(),
            self.compose_limbic(),
            self.compose_cortical(),
        ]

        if include_memory:
            sections.append(self.compose_memory())

        return "\n\n---\n\n".join(sections)

    # ── Unconscious Policy Access ────────────────────────────────────
    # Expose unconscious parameters for CODE integration only.
    # The entity cannot see these — they are never injected into prompts.

    @staticmethod
    def get_unconscious_policy() -> Dict[str, float]:
        """Return unconscious behavioral policy constants."""
        return dict(UNCONSCIOUS_POLICY)
