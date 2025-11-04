"""
P&L scenario modeling for options positions.

Provides tools to model profit/loss at different underlying prices,
helping visualize risk/reward profiles.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

from .base import OptionsPosition
from .greeks import calculate_black_scholes_greeks


def model_pnl_scenarios(
    position: OptionsPosition,
    price_range: Optional[List[float]] = None,
    days_to_expiration: Optional[int] = None,
    volatility: float = 0.30,
    risk_free_rate: float = 0.05,
    num_points: int = 50,
) -> Dict[float, float]:
    """
    Model P&L at different underlying prices.

    This helps visualize the payoff diagram for an options strategy,
    showing profit/loss across a range of stock prices.

    Args:
        position: The options position
        price_range: List of prices to evaluate (auto-generated if None)
        days_to_expiration: Days until expiration (uses current if None)
        volatility: Implied volatility (default 30%)
        risk_free_rate: Risk-free rate (default 5%)
        num_points: Number of price points to generate if range not provided

    Returns:
        Dictionary mapping stock price -> P&L
        {100.0: 50.0, 101.0: 45.0, ...}
    """
    # Use position's DTE if not specified
    if days_to_expiration is None:
        days_to_expiration = position.days_to_expiration()

    # Auto-generate price range if not provided
    if price_range is None:
        price_range = _generate_price_range(position, num_points)

    scenarios = {}

    for price in price_range:
        pnl = calculate_pnl(
            position=position,
            current_price=price,
            days_to_expiration=days_to_expiration,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )
        scenarios[price] = pnl

    return scenarios


def calculate_pnl(
    position: OptionsPosition,
    current_price: float,
    days_to_expiration: int,
    volatility: float = 0.30,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate current P&L for a position.

    P&L = Current Value - Entry Cost
    - For credit spreads: current value should be lower (profit)
    - For debit spreads: current value should be higher (profit)

    Args:
        position: The options position
        current_price: Current underlying price
        days_to_expiration: Days until expiration
        volatility: Implied volatility
        risk_free_rate: Risk-free rate

    Returns:
        Current P&L (positive = profit, negative = loss)
    """
    current_value = 0.0

    for leg in position.legs:
        # Calculate current option value
        greeks = calculate_black_scholes_greeks(
            underlying_price=current_price,
            strike=leg.strike,
            days_to_expiration=days_to_expiration,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=leg.option_type,
        )

        leg_value = greeks["price"] * leg.quantity * leg.contract_multiplier()

        # For bought options: we own them (add value)
        # For sold options: we're short them (subtract value)
        if leg.action == "buy":
            current_value += leg_value
        else:  # sell
            current_value -= leg_value

    # P&L = Current Value - Entry Cost
    # Entry cost is negative for credit spreads (we received money)
    pnl = current_value - position.entry_cost

    return pnl


def calculate_pnl_at_expiration(
    position: OptionsPosition,
    price_range: Optional[List[float]] = None,
    num_points: int = 50,
) -> Dict[float, float]:
    """
    Calculate P&L at expiration (intrinsic value only).

    At expiration, options are worth only their intrinsic value:
    - Calls: max(S - K, 0)
    - Puts: max(K - S, 0)

    Args:
        position: The options position
        price_range: List of prices to evaluate (auto-generated if None)
        num_points: Number of price points if range not provided

    Returns:
        Dictionary mapping stock price -> expiration P&L
    """
    if price_range is None:
        price_range = _generate_price_range(position, num_points)

    scenarios = {}

    for price in price_range:
        # Calculate intrinsic value at expiration
        total_value = 0.0

        for leg in position.legs:
            if leg.option_type == "call":
                intrinsic = max(price - leg.strike, 0)
            else:  # put
                intrinsic = max(leg.strike - price, 0)

            leg_value = intrinsic * leg.quantity * leg.contract_multiplier()

            if leg.action == "buy":
                total_value += leg_value
            else:  # sell
                total_value -= leg_value

        # P&L at expiration
        pnl = total_value - position.entry_cost
        scenarios[price] = pnl

    return scenarios


def find_breakeven_points(
    position: OptionsPosition,
    volatility: float = 0.30,
    price_range: Optional[Tuple[float, float]] = None,
    tolerance: float = 0.01,
) -> List[float]:
    """
    Find breakeven points where P&L = 0 at expiration.

    Uses binary search to find prices where the position breaks even.

    Args:
        position: The options position
        volatility: Implied volatility (for initial range estimation)
        price_range: (min_price, max_price) to search (auto if None)
        tolerance: How close to zero for breakeven (default $0.01)

    Returns:
        List of breakeven prices, sorted ascending
    """
    # Get expiration P&L across price range
    if price_range is None:
        price_range = _get_search_range(position)

    # Generate fine-grained price points
    prices = np.linspace(price_range[0], price_range[1], 1000)
    pnl_values = []

    for price in prices:
        # Calculate intrinsic value at expiration
        total_value = 0.0
        for leg in position.legs:
            if leg.option_type == "call":
                intrinsic = max(price - leg.strike, 0)
            else:
                intrinsic = max(leg.strike - price, 0)

            leg_value = intrinsic * leg.quantity * leg.contract_multiplier()

            if leg.action == "buy":
                total_value += leg_value
            else:
                total_value -= leg_value

        pnl = total_value - position.entry_cost
        pnl_values.append(pnl)

    # Find sign changes (crossings of zero)
    breakevens = []
    pnl_array = np.array(pnl_values)

    for i in range(len(pnl_array) - 1):
        # Check if sign changes
        if pnl_array[i] * pnl_array[i + 1] < 0:
            # Linear interpolation to find exact breakeven
            p1, p2 = prices[i], prices[i + 1]
            pnl1, pnl2 = pnl_array[i], pnl_array[i + 1]

            # Solve: pnl1 + (pnl2 - pnl1) * t = 0
            t = -pnl1 / (pnl2 - pnl1)
            breakeven = p1 + t * (p2 - p1)
            breakevens.append(breakeven)

    return sorted(breakevens)


def _generate_price_range(
    position: OptionsPosition, num_points: int = 50
) -> List[float]:
    """
    Generate a reasonable price range for P&L modeling.

    Range spans from lowest strike - 20% to highest strike + 20%.

    Args:
        position: The options position
        num_points: Number of price points to generate

    Returns:
        List of prices evenly spaced across the range
    """
    strikes = [leg.strike for leg in position.legs]
    min_strike = min(strikes)
    max_strike = max(strikes)

    # Add 20% buffer on each side
    range_width = max_strike - min_strike
    buffer = max(range_width * 0.2, 5.0)  # At least $5 buffer

    min_price = min_strike - buffer
    max_price = max_strike + buffer

    return list(np.linspace(min_price, max_price, num_points))


def _get_search_range(position: OptionsPosition) -> Tuple[float, float]:
    """
    Get price range for breakeven search.

    Args:
        position: The options position

    Returns:
        (min_price, max_price) tuple
    """
    strikes = [leg.strike for leg in position.legs]
    min_strike = min(strikes)
    max_strike = max(strikes)

    # Search from 50% below min strike to 50% above max strike
    min_price = min_strike * 0.5
    max_price = max_strike * 1.5

    return (min_price, max_price)


def calculate_roi(position: OptionsPosition, current_pnl: float) -> float:
    """
    Calculate return on investment (ROI) percentage.

    For credit spreads, ROI is based on max risk (capital at risk).
    For debit spreads, ROI is based on debit paid.

    Args:
        position: The options position
        current_pnl: Current profit/loss

    Returns:
        ROI as percentage (e.g., 0.50 = 50% return)
    """
    if position.is_credit_spread():
        # ROI based on max risk
        max_risk = position.max_loss
        if max_risk == 0:
            return 0.0
        return current_pnl / max_risk
    else:
        # ROI based on debit paid
        debit = position.net_debit_paid()
        if debit == 0:
            return 0.0
        return current_pnl / debit


def get_risk_reward_ratio(position: OptionsPosition) -> float:
    """
    Calculate risk/reward ratio.

    Risk/Reward = Max Profit / Max Loss

    Higher is better - indicates more reward per dollar of risk.

    Args:
        position: The options position

    Returns:
        Risk/reward ratio
    """
    if position.max_loss == 0:
        return float("inf")

    return position.max_profit / position.max_loss
