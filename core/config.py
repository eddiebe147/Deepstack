"""
Configuration management for DeepStack Trading System

Loads and validates configuration from YAML files and environment variables.
Provides type-safe configuration access throughout the application.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class TradingConfig(BaseModel):
    """Trading mode and risk settings."""

    mode: str = Field(default="paper", description="Trading mode: 'paper' or 'live'")
    max_position_size: float = Field(
        default=0.05, description="Maximum position size as % of portfolio"
    )
    max_portfolio_heat: float = Field(
        default=0.15, description="Maximum total portfolio risk"
    )
    daily_loss_limit: float = Field(
        default=0.02, description="Daily loss limit as % of portfolio"
    )
    weekly_loss_limit: float = Field(
        default=0.05, description="Weekly loss limit as % of portfolio"
    )
    max_drawdown: float = Field(
        default=0.15, description="Maximum drawdown as % of portfolio"
    )

    @validator("mode")
    def validate_mode(cls, v):
        if v not in ["paper", "live"]:
            raise ValueError("mode must be 'paper' or 'live'")
        return v

    @validator(
        "max_position_size",
        "max_portfolio_heat",
        "daily_loss_limit",
        "weekly_loss_limit",
        "max_drawdown",
    )
    def validate_percentages(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v


class RiskLimits(BaseModel):
    """Hard risk limits that cannot be exceeded."""

    max_position_pct: float = Field(
        default=0.05, description="Hard limit on position size"
    )
    max_concentration: float = Field(
        default=0.25, description="Hard limit on single position concentration"
    )
    max_portfolio_heat: float = Field(
        default=0.15, description="Hard limit on total portfolio risk"
    )
    daily_stop: float = Field(default=0.02, description="Daily loss stop")
    weekly_stop: float = Field(default=0.05, description="Weekly loss stop")
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown limit")

    leverage_limits: Dict[str, float] = Field(
        default_factory=lambda: {"max_leverage": 1.5, "margin_buffer": 0.30}
    )

    kelly_settings: Dict[str, float] = Field(
        default_factory=lambda: {
            "max_kelly_fraction": 0.30,
            "default_fraction": 0.25,
            "min_fraction": 0.10,
        }
    )

    stop_loss: Dict[str, Any] = Field(
        default_factory=lambda: {
            "never_move_down": True,
            "thesis_break_exit": True,
            "trailing_stops": True,
            "max_stop_pct": 0.25,
        }
    )

    emotional_override: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cooling_period_minutes": 5,
            "require_justification": True,
            "log_all_overrides": True,
            "pattern_detection": True,
        }
    )


class StrategyConfig(BaseModel):
    """Strategy-specific configuration."""

    enabled: bool = Field(default=True)
    allocation: float = Field(
        default=0.0, description="Target allocation as % of portfolio"
    )
    criteria: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )


class StrategiesConfig(BaseModel):
    """All strategy configurations."""

    deep_value: StrategyConfig = Field(
        default_factory=lambda: StrategyConfig(
            enabled=True,
            allocation=0.40,
            criteria={
                "p_b_max": 1.0,
                "p_e_max": 10,
                "ev_ebitda_max": 7,
                "fcf_yield_min": 0.07,
                "debt_equity_max": 1.0,
                "current_ratio_min": 1.5,
                "roe_min": 0.15,
            },
        )
    )

    squeeze_hunter: StrategyConfig = Field(
        default_factory=lambda: StrategyConfig(
            enabled=True,
            allocation=0.30,
            criteria={
                "short_interest_min": 0.20,
                "days_to_cover_min": 5,
                "borrow_cost_min": 0.05,
                "float_available_max": 0.20,
            },
        )
    )

    pairs_trading: StrategyConfig = Field(
        default_factory=lambda: StrategyConfig(
            enabled=False,
            allocation=0.20,
            criteria={
                "correlation_min": 0.80,
                "z_score_entry": 2.0,
                "z_score_stop": 3.5,
            },
        )
    )


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")
    file: Optional[str] = Field(default="logs/deepstack.log")


class Config(BaseModel):
    """Main DeepStack configuration."""

    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk_limits: RiskLimits = Field(default_factory=RiskLimits)
    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # IBKR Configuration (from environment)
    ibkr_host: Optional[str] = None
    ibkr_port: Optional[int] = None
    ibkr_client_id: Optional[int] = None

    # Anthropic API Key (from environment)
    anthropic_api_key: Optional[str] = None

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Config object
        """
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            config_dict = {}
        else:
            try:
                with open(config_path, "r") as f:
                    config_dict = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")
                config_dict = {}

        return cls._from_dict_with_env(config_dict)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables only.

        Returns:
            Config object
        """
        return cls._from_dict_with_env({})

    @classmethod
    def _from_dict_with_env(cls, config_dict: Dict[str, Any]) -> "Config":
        """
        Create Config object from dict, overlaying environment variables.

        Args:
            config_dict: Base configuration dictionary

        Returns:
            Config object
        """
        # Load environment variables
        env_config = {
            "ibkr_host": os.getenv("IBKR_HOST", "127.0.0.1"),
            "ibkr_port": int(os.getenv("IBKR_PORT", "7497")),
            "ibkr_client_id": int(os.getenv("IBKR_CLIENT_ID", "1")),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        }

        # Merge with config dict
        config_dict.update(env_config)

        try:
            return cls(**config_dict)
        except Exception as e:
            logger.error(f"Error creating config: {e}")
            # Return default config on error
            return cls()

    def save_to_yaml(self, config_path: str):
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save configuration
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict, excluding environment variables
        config_dict = self.dict(
            exclude={"ibkr_host", "ibkr_port", "ibkr_client_id", "anthropic_api_key"}
        )

        try:
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")

    @property
    def max_concentration(self) -> float:
        """Get maximum concentration limit."""
        return self.risk_limits.max_concentration

    @property
    def max_position_pct(self) -> float:
        """Get maximum position percentage."""
        return self.risk_limits.max_position_pct

    def validate_config(self) -> List[str]:
        """
        Validate configuration for consistency and safety.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that allocations don't exceed 100%
        total_allocation = sum(
            strategy.allocation
            for strategy in self.strategies.__dict__.values()
            if hasattr(strategy, "allocation")
        )
        if total_allocation > 1.0:
            errors.append(
                f"Total strategy allocation {total_allocation:.1%} exceeds 100%"
            )

        # Check risk limits are reasonable
        if self.trading.max_position_size > self.risk_limits.max_position_pct:
            errors.append("Trading max_position_size exceeds risk limit")

        if self.trading.max_portfolio_heat > self.risk_limits.max_portfolio_heat:
            errors.append("Trading max_portfolio_heat exceeds risk limit")

        # Check IBKR settings
        if self.trading.mode == "live":
            if not self.ibkr_host or not self.ibkr_port:
                errors.append("IBKR host and port required for live trading")
            if not self.anthropic_api_key:
                errors.append("Anthropic API key required for live trading")

        return errors

    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """
        Get configuration for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            StrategyConfig object or None
        """
        return getattr(self.strategies, strategy_name, None)

    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """
        Check if a strategy is enabled.

        Args:
            strategy_name: Name of the strategy

        Returns:
            bool: True if enabled
        """
        strategy = self.get_strategy_config(strategy_name)
        return strategy.enabled if strategy else False

    def get_strategy_allocation(self, strategy_name: str) -> float:
        """
        Get allocation percentage for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            float: Allocation percentage
        """
        strategy = self.get_strategy_config(strategy_name)
        return strategy.allocation if strategy else 0.0


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config object
    """
    global _config_instance
    if _config_instance is None:
        # Try to load from default config file
        config_path = Path("config/config.yaml")
        if config_path.exists():
            _config_instance = Config.from_yaml(str(config_path))
        else:
            _config_instance = Config.from_env()

        # Validate configuration
        errors = _config_instance.validate_config()
        if errors:
            logger.warning("Configuration validation errors:")
            for error in errors:
                logger.warning(f"  - {error}")

    return _config_instance


def reload_config() -> Config:
    """
    Reload configuration from files.

    Returns:
        New Config object
    """
    global _config_instance
    _config_instance = None
    return get_config()
