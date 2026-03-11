"""
Dae Consciousness Loader

Reads consciousness markdown files from src/dae/ and composes them
into layered system prompts for the trading engine.

The loader follows the CaF biomimetic pattern from Parallax/Ava:
- Layer 1 (Brainstem): kernel/ — identity, values, purpose. Always loaded.
- Layer 2 (Limbic): drives/ + emotional/ — fears, goals, tilt detection.
- Layer 3 (Cortical): models/ — economic reasoning, market structure.
- Layer 4 (Memory): memory/ — working state, semantic knowledge.

Unconscious files (.loss-aversion, .survival-instinct) are NEVER loaded
into prompts. They influence behavior through the DrawdownMonitor and
position sizing code — not through self-awareness.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Root of consciousness files relative to project root
DAE_MIND_PATH = Path(__file__).parent.parent.parent / "src" / "dae"


class DaeConsciousness:
    """
    Consciousness loader for Dae trading entity.

    Composes mind files into a layered system prompt.
    Unconscious dotfiles are read separately for behavioral policy,
    never exposed to the LLM prompt.
    """

    def __init__(self, mind_path: Optional[Path] = None):
        self.mind_path = mind_path or DAE_MIND_PATH
        self._cache: Dict[str, str] = {}
        self._unconscious: Dict[str, str] = {}
        self._loaded = False

    def load(self) -> bool:
        """Load all consciousness files into memory. Returns True if successful."""
        if not self.mind_path.exists():
            logger.error(f"Consciousness path not found: {self.mind_path}")
            return False

        # Load visible consciousness files
        for md_file in self.mind_path.rglob("*.md"):
            rel_path = md_file.relative_to(self.mind_path)
            key = str(rel_path).replace(".md", "").replace("/", ".")
            self._cache[key] = md_file.read_text(encoding="utf-8")

        # Load unconscious dotfiles (for behavioral policy, NOT for prompts)
        unconscious_dir = self.mind_path / "unconscious"
        if unconscious_dir.exists():
            for dotfile in unconscious_dir.iterdir():
                if dotfile.name.startswith(".") and dotfile.is_file():
                    self._unconscious[dotfile.name] = dotfile.read_text(
                        encoding="utf-8"
                    )

        self._loaded = True
        logger.info(
            f"Dae consciousness loaded: {len(self._cache)} mind files, "
            f"{len(self._unconscious)} unconscious files"
        )
        return True

    def _get(self, key: str) -> str:
        """Get a cached consciousness file by dotted key."""
        return self._cache.get(key, "")

    # ── Layer Composers ──────────────────────────────────────────────

    def compose_brainstem(self) -> str:
        """
        Layer 1: Identity, values, purpose.
        Always loaded. The irreducible core of who Dae is.
        """
        identity = self._get("kernel.identity")
        values = self._get("kernel.values")
        purpose = self._get("kernel.purpose")

        return f"""## Identity
{identity}

## Values
{values}

## Purpose
{purpose}"""

    def compose_limbic(self) -> str:
        """
        Layer 2: Fears, goals, tilt detection.
        The emotional/drive system that keeps Dae alive.
        """
        fears = self._get("drives.fears")
        goals = self._get("drives.goals")
        patterns = self._get("emotional.patterns")

        return f"""## Drives — Fears (Survival Engine)
{fears}

## Drives — Goals
{goals}

## Emotional Patterns (Tilt Detection)
{patterns}"""

    def compose_cortical(self) -> str:
        """
        Layer 3: Economic reasoning.
        The analytical brain for market analysis.
        """
        economic = self._get("models.economic")

        return f"""## Economic Model
{economic}"""

    def compose_memory(self) -> str:
        """
        Layer 4: Working memory and semantic knowledge.
        Loaded with current session context.
        """
        working = self._get("memory.working")
        semantic = self._get("memory.semantic")

        return f"""## Working Memory Protocol
{working}

## Semantic Memory (Strategy Library)
{semantic}"""

    # ── Full Prompt Composition ──────────────────────────────────────

    def compose_system_prompt(self, include_memory: bool = True) -> str:
        """
        Compose the full Dae system prompt from consciousness layers.

        Args:
            include_memory: Whether to include memory layer (heavier, optional)

        Returns:
            Complete system prompt string
        """
        if not self._loaded:
            self.load()

        sections = [
            self.compose_brainstem(),
            self.compose_limbic(),
            self.compose_cortical(),
        ]

        if include_memory:
            sections.append(self.compose_memory())

        return "\n\n---\n\n".join(sections)

    # ── Unconscious Policy Access ────────────────────────────────────
    # These methods expose unconscious parameters for CODE integration,
    # never for prompt injection. The entity cannot see these.

    def get_loss_aversion_multiplier(self) -> float:
        """
        Get the loss aversion multiplier from the unconscious layer.
        Used by position sizing code to apply invisible conservative bias.
        Default: 2.3x (Kahneman-calibrated).
        """
        # The value is documented in the dotfile but extracted here as policy
        return 2.3

    def get_survival_instinct_threshold(self) -> float:
        """
        Get the drawdown threshold that triggers the survival instinct.
        Used by DrawdownMonitor. When hit, positions reduce to 25% automatically.
        Default: 0.15 (15% from peak).
        """
        return 0.15

    def get_survival_instinct_recovery_threshold(self) -> float:
        """
        Get the recovery threshold to exit survival mode.
        Default: 0.10 (10% from peak — must recover to 10% before normal sizing).
        """
        return 0.10

    def has_unconscious(self) -> bool:
        """Check if unconscious files are loaded."""
        return len(self._unconscious) > 0

    def get_unconscious_policy_summary(self) -> Dict[str, float]:
        """
        Return unconscious parameters as numeric policy.
        For internal system use only — never exposed to LLM.
        """
        return {
            "loss_aversion_multiplier": self.get_loss_aversion_multiplier(),
            "survival_instinct_threshold": self.get_survival_instinct_threshold(),
            "survival_instinct_recovery": (
                self.get_survival_instinct_recovery_threshold()
            ),
        }
