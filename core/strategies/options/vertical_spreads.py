"""
Vertical spread options strategies.

Implements:
- Bull Call Spread: Bullish strategy using calls
- Bear Put Spread: Bearish strategy using puts

Both are directional strategies with defined risk and reward.
"""

from datetime import datetime, timedelta

from .base import OptionLeg, OptionsPosition, OptionsStrategy
from .pnl_modeling import calculate_pnl


class BullCallSpread(OptionsStrategy):
    """
    Bull Call Spread - Bullish directional strategy.

    Buy lower strike call, sell higher strike call.
    Profits when stock rises, with limited risk and reward.

    Example with stock at $100:
    - Buy 100 call @ $5
    - Sell 105 call @ $2
    - Net debit: $3 per share ($300 total)
    - Max profit: $2 per share ($200) if stock >= $105
    - Max loss: $3 per share ($300) if stock <= $100
    - Breakeven: $103

    Parameters:
        strike_width: Distance between strikes (default: 5.0)
        profit_target_pct: Close at X% of max profit (default: 70%)
        loss_limit_pct: Close at X% of max loss (default: 50%)
    """

    def __init__(
        self,
        strike_width: float = 5.0,
        profit_target_pct: float = 0.70,
        loss_limit_pct: float = 0.50,
    ):
        """
        Initialize Bull Call Spread strategy.

        Args:
            strike_width: Distance between strikes
            profit_target_pct: Close at this % of max profit
            loss_limit_pct: Close at this % of max loss
        """
        if strike_width <= 0:
            raise ValueError(f"strike_width must be positive, got {strike_width}")
        if profit_target_pct < 0 or profit_target_pct > 1:
            raise ValueError(
                f"profit_target_pct must be between 0 and 1, got {profit_target_pct}"
            )
        if loss_limit_pct < 0 or loss_limit_pct > 1:
            raise ValueError(
                f"loss_limit_pct must be between 0 and 1, got {loss_limit_pct}"
            )

        self.strike_width = strike_width
        self.profit_target_pct = profit_target_pct
        self.loss_limit_pct = loss_limit_pct

    def create_position(
        self,
        symbol: str,
        underlying_price: float,
        expiration_days: int = 45,
        contracts: int = 1,
        volatility: float = 0.30,
        atm_offset: float = 0.0,
    ) -> OptionsPosition:
        """
        Create Bull Call Spread position.

        Args:
            symbol: Underlying stock symbol
            underlying_price: Current price of underlying
            expiration_days: Days until expiration (default 45)
            contracts: Number of contracts (default 1)
            volatility: Implied volatility for premium calculation
            atm_offset: Offset from ATM for long strike (0 = ATM, positive = OTM)

        Returns:
            Complete Bull Call Spread position with 2 legs
        """
        if underlying_price <= 0:
            raise ValueError(
                f"underlying_price must be positive, got {underlying_price}"
            )
        if expiration_days <= 0:
            raise ValueError(f"expiration_days must be positive, got {expiration_days}")
        if contracts <= 0:
            raise ValueError(f"contracts must be positive, got {contracts}")

        # Calculate strikes
        # Long call at or slightly OTM
        long_strike = round(underlying_price + atm_offset, 2)
        short_strike = round(long_strike + self.strike_width, 2)

        # Calculate expiration date
        expiration = datetime.now() + timedelta(days=expiration_days)

        # Calculate premiums
        long_premium = self._estimate_premium(
            underlying_price, long_strike, expiration_days, volatility, "call"
        )
        short_premium = self._estimate_premium(
            underlying_price, short_strike, expiration_days, volatility, "call"
        )

        # Net debit = premium paid - premium received
        net_debit = (long_premium - short_premium) * contracts * 100

        # Create legs
        legs = [
            OptionLeg(
                symbol=symbol,
                strike=long_strike,
                expiration=expiration,
                option_type="call",
                action="buy",
                quantity=contracts,
                premium=long_premium,
            ),
            OptionLeg(
                symbol=symbol,
                strike=short_strike,
                expiration=expiration,
                option_type="call",
                action="sell",
                quantity=contracts,
                premium=short_premium,
            ),
        ]

        # Max profit = (strike width * contracts * 100) - net debit
        max_profit = (self.strike_width * contracts * 100) - net_debit

        # Max loss = net debit
        max_loss = net_debit

        # Breakeven = long strike + (debit / contracts / 100)
        debit_per_share = net_debit / (contracts * 100)
        breakeven = long_strike + debit_per_share

        return OptionsPosition(
            strategy_name="Bull Call Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=net_debit,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=[breakeven],
            profit_target_pct=self.profit_target_pct,
            loss_limit_pct=self.loss_limit_pct,
            metadata={
                "strike_width": self.strike_width,
                "long_strike": long_strike,
                "short_strike": short_strike,
                "underlying_price_at_entry": underlying_price,
            },
        )

    def calculate_pnl(
        self,
        position: OptionsPosition,
        current_price: float,
        days_to_expiration: int,
        volatility: float = 0.30,
    ) -> float:
        """Calculate current P&L for Bull Call Spread."""
        return calculate_pnl(
            position=position,
            current_price=current_price,
            days_to_expiration=days_to_expiration,
            volatility=volatility,
        )

    def should_close(
        self, position: OptionsPosition, current_pnl: float, days_to_expiration: int
    ) -> bool:
        """
        Determine if Bull Call Spread should be closed.

        Close conditions:
        1. Profit target reached
        2. Loss limit hit
        3. Expiration reached
        """
        if days_to_expiration <= 0:
            return True

        if self.profit_target_pct is not None:
            profit_target = position.max_profit * self.profit_target_pct
            if current_pnl >= profit_target:
                return True

        if self.loss_limit_pct is not None:
            loss_limit = -abs(position.max_loss * self.loss_limit_pct)
            if current_pnl <= loss_limit:
                return True

        return False

    def _estimate_premium(
        self,
        underlying_price: float,
        strike: float,
        days_to_expiration: int,
        volatility: float,
        option_type: str,
    ) -> float:
        """Estimate option premium using Black-Scholes."""
        from .greeks import calculate_black_scholes_greeks

        try:
            greeks = calculate_black_scholes_greeks(
                underlying_price=underlying_price,
                strike=strike,
                days_to_expiration=days_to_expiration,
                volatility=volatility,
                option_type=option_type,
            )
            return greeks["price"]
        except Exception:
            # Fallback to intrinsic value
            if option_type == "call":
                return max(underlying_price - strike, 0)
            else:
                return max(strike - underlying_price, 0)


class BearPutSpread(OptionsStrategy):
    """
    Bear Put Spread - Bearish directional strategy.

    Buy higher strike put, sell lower strike put.
    Profits when stock falls, with limited risk and reward.

    Example with stock at $100:
    - Buy 100 put @ $5
    - Sell 95 put @ $2
    - Net debit: $3 per share ($300 total)
    - Max profit: $2 per share ($200) if stock <= $95
    - Max loss: $3 per share ($300) if stock >= $100
    - Breakeven: $97

    Parameters:
        strike_width: Distance between strikes (default: 5.0)
        profit_target_pct: Close at X% of max profit (default: 70%)
        loss_limit_pct: Close at X% of max loss (default: 50%)
    """

    def __init__(
        self,
        strike_width: float = 5.0,
        profit_target_pct: float = 0.70,
        loss_limit_pct: float = 0.50,
    ):
        """
        Initialize Bear Put Spread strategy.

        Args:
            strike_width: Distance between strikes
            profit_target_pct: Close at this % of max profit
            loss_limit_pct: Close at this % of max loss
        """
        if strike_width <= 0:
            raise ValueError(f"strike_width must be positive, got {strike_width}")
        if profit_target_pct < 0 or profit_target_pct > 1:
            raise ValueError(
                f"profit_target_pct must be between 0 and 1, got {profit_target_pct}"
            )
        if loss_limit_pct < 0 or loss_limit_pct > 1:
            raise ValueError(
                f"loss_limit_pct must be between 0 and 1, got {loss_limit_pct}"
            )

        self.strike_width = strike_width
        self.profit_target_pct = profit_target_pct
        self.loss_limit_pct = loss_limit_pct

    def create_position(
        self,
        symbol: str,
        underlying_price: float,
        expiration_days: int = 45,
        contracts: int = 1,
        volatility: float = 0.30,
        atm_offset: float = 0.0,
    ) -> OptionsPosition:
        """
        Create Bear Put Spread position.

        Args:
            symbol: Underlying stock symbol
            underlying_price: Current price of underlying
            expiration_days: Days until expiration (default 45)
            contracts: Number of contracts (default 1)
            volatility: Implied volatility for premium calculation
            atm_offset: Offset from ATM for long strike (0 = ATM, negative = OTM)

        Returns:
            Complete Bear Put Spread position with 2 legs
        """
        if underlying_price <= 0:
            raise ValueError(
                f"underlying_price must be positive, got {underlying_price}"
            )
        if expiration_days <= 0:
            raise ValueError(f"expiration_days must be positive, got {expiration_days}")
        if contracts <= 0:
            raise ValueError(f"contracts must be positive, got {contracts}")

        # Calculate strikes
        # Long put at or slightly OTM
        long_strike = round(underlying_price + atm_offset, 2)
        short_strike = round(long_strike - self.strike_width, 2)

        # Calculate expiration date
        expiration = datetime.now() + timedelta(days=expiration_days)

        # Calculate premiums
        long_premium = self._estimate_premium(
            underlying_price, long_strike, expiration_days, volatility, "put"
        )
        short_premium = self._estimate_premium(
            underlying_price, short_strike, expiration_days, volatility, "put"
        )

        # Net debit = premium paid - premium received
        net_debit = (long_premium - short_premium) * contracts * 100

        # Create legs
        legs = [
            OptionLeg(
                symbol=symbol,
                strike=long_strike,
                expiration=expiration,
                option_type="put",
                action="buy",
                quantity=contracts,
                premium=long_premium,
            ),
            OptionLeg(
                symbol=symbol,
                strike=short_strike,
                expiration=expiration,
                option_type="put",
                action="sell",
                quantity=contracts,
                premium=short_premium,
            ),
        ]

        # Max profit = (strike width * contracts * 100) - net debit
        max_profit = (self.strike_width * contracts * 100) - net_debit

        # Max loss = net debit
        max_loss = net_debit

        # Breakeven = long strike - (debit / contracts / 100)
        debit_per_share = net_debit / (contracts * 100)
        breakeven = long_strike - debit_per_share

        return OptionsPosition(
            strategy_name="Bear Put Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=net_debit,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=[breakeven],
            profit_target_pct=self.profit_target_pct,
            loss_limit_pct=self.loss_limit_pct,
            metadata={
                "strike_width": self.strike_width,
                "long_strike": long_strike,
                "short_strike": short_strike,
                "underlying_price_at_entry": underlying_price,
            },
        )

    def calculate_pnl(
        self,
        position: OptionsPosition,
        current_price: float,
        days_to_expiration: int,
        volatility: float = 0.30,
    ) -> float:
        """Calculate current P&L for Bear Put Spread."""
        return calculate_pnl(
            position=position,
            current_price=current_price,
            days_to_expiration=days_to_expiration,
            volatility=volatility,
        )

    def should_close(
        self, position: OptionsPosition, current_pnl: float, days_to_expiration: int
    ) -> bool:
        """
        Determine if Bear Put Spread should be closed.

        Close conditions:
        1. Profit target reached
        2. Loss limit hit
        3. Expiration reached
        """
        if days_to_expiration <= 0:
            return True

        if self.profit_target_pct is not None:
            profit_target = position.max_profit * self.profit_target_pct
            if current_pnl >= profit_target:
                return True

        if self.loss_limit_pct is not None:
            loss_limit = -abs(position.max_loss * self.loss_limit_pct)
            if current_pnl <= loss_limit:
                return True

        return False

    def _estimate_premium(
        self,
        underlying_price: float,
        strike: float,
        days_to_expiration: int,
        volatility: float,
        option_type: str,
    ) -> float:
        """Estimate option premium using Black-Scholes."""
        from .greeks import calculate_black_scholes_greeks

        try:
            greeks = calculate_black_scholes_greeks(
                underlying_price=underlying_price,
                strike=strike,
                days_to_expiration=days_to_expiration,
                volatility=volatility,
                option_type=option_type,
            )
            return greeks["price"]
        except Exception:
            # Fallback to intrinsic value
            if option_type == "call":
                return max(underlying_price - strike, 0)
            else:
                return max(strike - underlying_price, 0)
