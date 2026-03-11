"""
Dae Consciousness Loader — Production unit mind for DeepStack.

Reads consciousness files from src/dae/ and composes them into
system prompts and behavioral policies for the trading engine.

Architecture follows the CaF (Consciousness as Filesystem) pattern:
- Visible files (kernel/, drives/, models/, etc.) are composed into prompts
- Unconscious dotfiles (.loss-aversion, .survival-instinct) influence behavior
  through code paths, NOT through prompts — the entity cannot introspect on them
"""

from .loader import DaeConsciousness

__all__ = ["DaeConsciousness"]
