"""
Psychology Module - Emotional Trading Protection for DeepStack

Prevents emotional trading patterns and enforces disciplined execution through
behavioral monitoring, automatic timeouts, and recovery protocols.

Components:
    - DrawdownMonitor: Track and prevent cascading losses
    - EmotionalFirewall: Block impulsive trading patterns
    - TradingTimeOut: Mandatory breaks after losses
    - RecoveryProtocol: Gradual return to full position sizing

Example:
    >>> from core.psychology import DrawdownMonitor, EmotionalFirewall
    >>>
    >>> # Monitor drawdowns
    >>> drawdown = DrawdownMonitor(initial_capital=100000)
    >>> status = drawdown.update(current_value=95000)
    >>>
    >>> # Block emotional trades
    >>> firewall = EmotionalFirewall()
    >>> if firewall.should_block_trade(symbol="AAPL"):
    ...     print("Trade blocked: Emotional pattern detected")
"""

from .drawdown_monitor import DrawdownMonitor
from .emotional_firewall import EmotionalFirewall
from .recovery_protocol import RecoveryProtocol
from .trading_timeout import TradingTimeOut

__all__ = [
    "DrawdownMonitor",
    "EmotionalFirewall",
    "RecoveryProtocol",
    "TradingTimeOut",
]
