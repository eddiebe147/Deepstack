"""
Iron Condor options strategy implementation.

Iron Condor is a neutral strategy that profits from low volatility.
It combines a bull put spread and a bear call spread.

Strategy Structure:
- Sell OTM put (collect premium)
- Buy further OTM put (limit risk)
- Sell OTM call (collect premium)
- Buy further OTM call (limit risk)

Max Profit: Net premium collected
Max Loss: Width of spread - net premium
Best Case: Stock stays between short strikes until expiration
"""

from datetime import datetime, timedelta

from .base import OptionLeg, OptionsPosition, OptionsStrategy
from .pnl_modeling import calculate_pnl


class IronCondorStrategy(OptionsStrategy):
    """
    Iron Condor - Neutral options strategy.

    Profits from range-bound markets with low volatility. The stock
    should ideally stay between the two short strikes until expiration.

    Example with stock at $100:
    - Sell 95 put, buy 90 put (put spread, width $5, collect ~$2)
    - Sell 105 call, buy 110 call (call spread, width $5, collect ~$2)
    - Net credit: ~$4 per share ($400 total)
    - Max profit: $400 (if stock stays 95-105)
    - Max loss: $100 ($5 width - $4 credit)

    Parameters:
        wing_width: Distance between long/short strikes (default: 5.0)
        range_width_pct: Distance from current price to short strikes (default: 5%)
        profit_target_pct: Close at X% of max profit (default: 50%)
        loss_limit_pct: Close at X% of max loss (default: 50%)
    """

    def __init__(
        self,
        wing_width: float = 5.0,
        range_width_pct: float = 0.05,
        profit_target_pct: float = 0.50,
        loss_limit_pct: float = 0.50,
    ):
        """
        Initialize Iron Condor strategy.

        Args:
            wing_width: Distance between long/short strikes
            range_width_pct: Distance from price to short strikes (as %)
            profit_target_pct: Close at this % of max profit (0.5 = 50%)
            loss_limit_pct: Close at this % of max loss (0.5 = 50%)
        """
        if wing_width <= 0:
            raise ValueError(f"wing_width must be positive, got {wing_width}")
        if range_width_pct <= 0 or range_width_pct >= 1:
            raise ValueError(
                f"range_width_pct must be between 0 and 1, got {range_width_pct}"
            )
        if profit_target_pct < 0 or profit_target_pct > 1:
            raise ValueError(
                f"profit_target_pct must be between 0 and 1, got {profit_target_pct}"
            )
        if loss_limit_pct < 0 or loss_limit_pct > 1:
            raise ValueError(
                f"loss_limit_pct must be between 0 and 1, got {loss_limit_pct}"
            )

        self.wing_width = wing_width
        self.range_width_pct = range_width_pct
        self.profit_target_pct = profit_target_pct
        self.loss_limit_pct = loss_limit_pct

    def create_position(
        self,
        symbol: str,
        underlying_price: float,
        expiration_days: int = 45,
        contracts: int = 1,
        volatility: float = 0.30,
    ) -> OptionsPosition:
        """
        Create Iron Condor position.

        Args:
            symbol: Underlying stock symbol
            underlying_price: Current price of underlying
            expiration_days: Days until expiration (default 45)
            contracts: Number of contracts (default 1)
            volatility: Implied volatility for premium calculation

        Returns:
            Complete Iron Condor position with 4 legs
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
        range_offset = underlying_price * self.range_width_pct

        # Put spread (lower side)
        short_put_strike = round(underlying_price - range_offset, 2)
        long_put_strike = round(short_put_strike - self.wing_width, 2)

        # Call spread (upper side)
        short_call_strike = round(underlying_price + range_offset, 2)
        long_call_strike = round(short_call_strike + self.wing_width, 2)

        # Calculate expiration date
        expiration = datetime.now() + timedelta(days=expiration_days)

        # Calculate premiums using simplified model
        # In production, would use real market data
        short_put_premium = self._estimate_premium(
            underlying_price, short_put_strike, expiration_days, volatility, "put"
        )
        long_put_premium = self._estimate_premium(
            underlying_price, long_put_strike, expiration_days, volatility, "put"
        )
        short_call_premium = self._estimate_premium(
            underlying_price, short_call_strike, expiration_days, volatility, "call"
        )
        long_call_premium = self._estimate_premium(
            underlying_price, long_call_strike, expiration_days, volatility, "call"
        )

        # Net credit = premiums collected - premiums paid
        put_spread_credit = (short_put_premium - long_put_premium) * contracts * 100
        call_spread_credit = (short_call_premium - long_call_premium) * contracts * 100
        net_credit = put_spread_credit + call_spread_credit

        # Create legs (order: short put, long put, short call, long call)
        legs = [
            OptionLeg(
                symbol=symbol,
                strike=short_put_strike,
                expiration=expiration,
                option_type="put",
                action="sell",
                quantity=contracts,
                premium=short_put_premium,
            ),
            OptionLeg(
                symbol=symbol,
                strike=long_put_strike,
                expiration=expiration,
                option_type="put",
                action="buy",
                quantity=contracts,
                premium=long_put_premium,
            ),
            OptionLeg(
                symbol=symbol,
                strike=short_call_strike,
                expiration=expiration,
                option_type="call",
                action="sell",
                quantity=contracts,
                premium=short_call_premium,
            ),
            OptionLeg(
                symbol=symbol,
                strike=long_call_strike,
                expiration=expiration,
                option_type="call",
                action="buy",
                quantity=contracts,
                premium=long_call_premium,
            ),
        ]

        # Max profit = net credit (keep all premium if stock stays in range)
        max_profit = net_credit

        # Max loss = (wing width * contracts * 100) - net credit
        # Occurs if stock moves beyond either long strike
        max_loss = (self.wing_width * contracts * 100) - net_credit

        # Breakeven points (where P&L = 0 at expiration)
        # Lower breakeven = short put - (credit / contracts / 100)
        # Upper breakeven = short call + (credit / contracts / 100)
        credit_per_share = net_credit / (contracts * 100)
        breakeven_lower = short_put_strike - credit_per_share
        breakeven_upper = short_call_strike + credit_per_share

        return OptionsPosition(
            strategy_name="Iron Condor",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=-net_credit,  # Negative because we received credit
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=[breakeven_lower, breakeven_upper],
            profit_target_pct=self.profit_target_pct,
            loss_limit_pct=self.loss_limit_pct,
            metadata={
                "wing_width": self.wing_width,
                "range_width_pct": self.range_width_pct,
                "short_put_strike": short_put_strike,
                "long_put_strike": long_put_strike,
                "short_call_strike": short_call_strike,
                "long_call_strike": long_call_strike,
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
        """
        Calculate current P&L for Iron Condor position.

        Args:
            position: The Iron Condor position
            current_price: Current underlying price
            days_to_expiration: Days until expiration
            volatility: Current implied volatility

        Returns:
            Current P&L (positive = profit, negative = loss)
        """
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
        Determine if Iron Condor should be closed.

        Close conditions:
        1. Profit target reached (e.g., 50% of max profit)
        2. Loss limit hit (e.g., 50% of max loss)
        3. Expiration reached

        Args:
            position: The Iron Condor position
            current_pnl: Current profit/loss
            days_to_expiration: Days until expiration

        Returns:
            True if position should be closed
        """
        # Close at expiration
        if days_to_expiration <= 0:
            return True

        # Check profit target
        if self.profit_target_pct is not None:
            profit_target = position.max_profit * self.profit_target_pct
            if current_pnl >= profit_target:
                return True

        # Check loss limit
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
        """
        Estimate option premium using simplified Black-Scholes.

        This is a simplified model. In production, use real market data.

        Args:
            underlying_price: Current stock price
            strike: Option strike price
            days_to_expiration: Days until expiration
            volatility: Implied volatility
            option_type: "call" or "put"

        Returns:
            Estimated premium per share
        """
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
            # Fallback to intrinsic value if calculation fails
            if option_type == "call":
                return max(underlying_price - strike, 0)
            else:
                return max(strike - underlying_price, 0)
