"""
Greeks calculation using Black-Scholes model.

Provides functions to calculate option Greeks (Delta, Gamma, Theta, Vega)
for individual options and complete positions.
"""

import math
from typing import Dict

from scipy.stats import norm

from .base import Greeks, OptionLeg, OptionsPosition


def calculate_black_scholes_greeks(
    underlying_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float = 0.05,
    option_type: str = "call",
) -> Dict[str, float]:
    """
    Calculate Black-Scholes option price and Greeks.

    The Black-Scholes model is the standard for pricing European-style options.
    While American options can be exercised early, this model provides accurate
    estimates for most options trading scenarios.

    Args:
        underlying_price: Current price of underlying stock
        strike: Strike price of the option
        days_to_expiration: Days until expiration
        volatility: Implied volatility (e.g., 0.30 for 30%)
        risk_free_rate: Risk-free interest rate (default 5%)
        option_type: "call" or "put"

    Returns:
        Dictionary containing:
        - price: Theoretical option price
        - delta: Price change per $1 move in underlying
        - gamma: Delta change per $1 move in underlying
        - theta: Price change per day (time decay)
        - vega: Price change per 1% volatility change

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate inputs
    if underlying_price <= 0:
        raise ValueError(f"underlying_price must be positive, got {underlying_price}")
    if strike <= 0:
        raise ValueError(f"strike must be positive, got {strike}")
    if days_to_expiration < 0:
        raise ValueError(
            f"days_to_expiration cannot be negative, got {days_to_expiration}"
        )
    if volatility <= 0:
        raise ValueError(f"volatility must be positive, got {volatility}")
    if option_type not in ["call", "put"]:
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type}")

    # Handle expiration day (0 DTE)
    if days_to_expiration == 0:
        return _calculate_expiration_greeks(underlying_price, strike, option_type)

    # Convert days to years
    T = days_to_expiration / 365.0
    S = underlying_price
    K = strike
    sigma = volatility
    r = risk_free_rate

    # Calculate d1 and d2 from Black-Scholes formula
    # d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
    # d2 = d1 - σ√T
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    # Calculate price and Greeks
    if option_type == "call":
        # Call option formulas
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
        theta_annual = -S * norm.pdf(d1) * sigma / (2 * sqrt_T) - r * K * math.exp(
            -r * T
        ) * norm.cdf(d2)
    else:  # put
        # Put option formulas
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
        theta_annual = -S * norm.pdf(d1) * sigma / (2 * sqrt_T) + r * K * math.exp(
            -r * T
        ) * norm.cdf(-d2)

    # Gamma is the same for calls and puts
    gamma = norm.pdf(d1) / (S * sigma * sqrt_T)

    # Vega is the same for calls and puts
    # Vega per 1% volatility change
    vega = S * norm.pdf(d1) * sqrt_T / 100

    # Convert theta from annual to per-day
    theta = theta_annual / 365

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
    }


def _calculate_expiration_greeks(
    underlying_price: float, strike: float, option_type: str
) -> Dict[str, float]:
    """
    Calculate option value and Greeks at expiration (0 DTE).

    At expiration, options have only intrinsic value:
    - Calls: max(S - K, 0)
    - Puts: max(K - S, 0)

    All Greeks are zero except delta (0 or 1 for calls, 0 or -1 for puts).

    Args:
        underlying_price: Current price of underlying
        strike: Strike price
        option_type: "call" or "put"

    Returns:
        Greeks dictionary with intrinsic value and zero Greeks
    """
    if option_type == "call":
        intrinsic_value = max(underlying_price - strike, 0)
        # Delta is 1 if ITM, 0 if OTM
        delta = 1.0 if underlying_price > strike else 0.0
    else:  # put
        intrinsic_value = max(strike - underlying_price, 0)
        # Delta is -1 if ITM, 0 if OTM
        delta = -1.0 if underlying_price < strike else 0.0

    return {
        "price": intrinsic_value,
        "delta": delta,
        "gamma": 0.0,
        "theta": 0.0,
        "vega": 0.0,
    }


def calculate_position_greeks(
    position: OptionsPosition,
    underlying_price: float,
    days_to_expiration: int,
    volatility: float = 0.30,
    risk_free_rate: float = 0.05,
) -> Greeks:
    """
    Calculate total Greeks for a multi-leg options position.

    Greeks are additive - we sum the Greeks of each leg, accounting for
    buy/sell direction and quantity.

    Args:
        position: The options position
        underlying_price: Current price of underlying
        days_to_expiration: Days until expiration
        volatility: Implied volatility (default 30%)
        risk_free_rate: Risk-free rate (default 5%)

    Returns:
        Greeks object with total position Greeks
    """
    total_delta = 0.0
    total_gamma = 0.0
    total_theta = 0.0
    total_vega = 0.0

    for leg in position.legs:
        # Calculate Greeks for this leg
        leg_greeks = calculate_black_scholes_greeks(
            underlying_price=underlying_price,
            strike=leg.strike,
            days_to_expiration=days_to_expiration,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=leg.option_type,
        )

        # Determine sign based on buy/sell
        # Buying options = positive Greeks
        # Selling options = negative Greeks
        sign = 1.0 if leg.action == "buy" else -1.0

        # Add to totals (multiply by quantity and sign)
        total_delta += leg_greeks["delta"] * sign * leg.quantity
        total_gamma += leg_greeks["gamma"] * sign * leg.quantity
        total_theta += leg_greeks["theta"] * sign * leg.quantity
        total_vega += leg_greeks["vega"] * sign * leg.quantity

    return Greeks(
        delta=total_delta, gamma=total_gamma, theta=total_theta, vega=total_vega
    )


def calculate_leg_value(
    leg: OptionLeg,
    underlying_price: float,
    days_to_expiration: int,
    volatility: float = 0.30,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate current value of a single option leg.

    Args:
        leg: The option leg
        underlying_price: Current price of underlying
        days_to_expiration: Days until expiration
        volatility: Implied volatility
        risk_free_rate: Risk-free rate

    Returns:
        Current value of the leg (total premium)
    """
    greeks = calculate_black_scholes_greeks(
        underlying_price=underlying_price,
        strike=leg.strike,
        days_to_expiration=days_to_expiration,
        volatility=volatility,
        risk_free_rate=risk_free_rate,
        option_type=leg.option_type,
    )

    # Current option price
    current_premium = greeks["price"]

    # Total value (premium * quantity * multiplier)
    return current_premium * leg.quantity * leg.contract_multiplier()


def calculate_position_value(
    position: OptionsPosition,
    underlying_price: float,
    days_to_expiration: int,
    volatility: float = 0.30,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate current total value of a multi-leg position.

    Args:
        position: The options position
        underlying_price: Current price of underlying
        days_to_expiration: Days until expiration
        volatility: Implied volatility
        risk_free_rate: Risk-free rate

    Returns:
        Current total value of the position
    """
    total_value = 0.0

    for leg in position.legs:
        leg_value = calculate_leg_value(
            leg, underlying_price, days_to_expiration, volatility, risk_free_rate
        )

        # Add or subtract based on buy/sell
        if leg.action == "buy":
            total_value += leg_value
        else:  # sell
            total_value -= leg_value

    return total_value
