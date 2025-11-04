"""
Strategy Agent - Analyzes opportunities using deep value + squeeze detection

Evaluates stocks based on fundamental value criteria and short squeeze potential.
Generates trade theses and recommendations for the DeepStack trading system.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from .base_agent import AgentResponse, BaseAgent, Tool

logger = logging.getLogger(__name__)


@dataclass
class StockAnalysis:
    """Analysis result for a stock."""

    symbol: str
    deep_value_score: float
    squeeze_score: float
    overall_score: float
    recommendation: str
    thesis: str
    catalysts: List[str]
    risks: List[str]
    target_price: float
    stop_price: float
    position_size_pct: float
    confidence: float


@dataclass
class SqueezeData:
    """Short squeeze data for a stock."""

    short_interest_pct: float
    days_to_cover: float
    cost_to_borrow: float
    float_available_pct: float
    squeeze_score: float


class StrategyAgent(BaseAgent):
    """
    Strategy Agent for DeepStack trading system.

    Analyzes stocks using:
    - Deep value fundamentals (P/E, P/B, ROE, etc.)
    - Short squeeze potential (short interest, borrow costs)
    - Catalyst identification
    - Risk/reward assessment

    Generates structured trade theses and recommendations.
    """

    def __init__(self):
        super().__init__(
            name="StrategyAgent",
            description="Expert in deep value investing and short squeeze detection, analyzing stocks for asymmetric opportunities with clear catalysts and risk management.",
        )

        # Register tools
        self._register_tools()

        # Strategy parameters from config
        self.deep_value_config = self.config.strategies.deep_value
        self.squeeze_config = self.config.strategies.squeeze_hunter

        logger.info("StrategyAgent initialized with deep value and squeeze detection")

    def _register_tools(self):
        """Register strategy analysis tools."""

        # Market data tools
        self.register_tool(
            Tool(
                name="get_stock_quote",
                description="Get current quote and basic metrics for a stock symbol",
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol (e.g., AAPL)",
                        }
                    },
                    "required": ["symbol"],
                },
            ),
            self._handle_get_stock_quote,
        )

        self.register_tool(
            Tool(
                name="get_fundamentals",
                description="Get fundamental data for a stock (P/E, P/B, ROE, etc.)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"}
                    },
                    "required": ["symbol"],
                },
            ),
            self._handle_get_fundamentals,
        )

        self.register_tool(
            Tool(
                name="get_short_interest",
                description="Get short interest and squeeze metrics for a stock",
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"}
                    },
                    "required": ["symbol"],
                },
            ),
            self._handle_get_short_interest,
        )

        self.register_tool(
            Tool(
                name="analyze_sector",
                description="Analyze sector positioning and peer comparisons",
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol"},
                        "sector": {"type": "string", "description": "Sector name"},
                    },
                    "required": ["symbol"],
                },
            ),
            self._handle_analyze_sector,
        )

        self.register_tool(
            Tool(
                name="scan_value_stocks",
                description="Scan for undervalued stocks using deep value criteria",
                input_schema={
                    "type": "object",
                    "properties": {
                        "min_market_cap": {
                            "type": "number",
                            "description": "Minimum market cap in millions",
                        },
                        "max_pe": {
                            "type": "number",
                            "description": "Maximum P/E ratio",
                        },
                        "max_pb": {
                            "type": "number",
                            "description": "Maximum P/B ratio",
                        },
                        "min_roe": {
                            "type": "number",
                            "description": "Minimum ROE percentage",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                        },
                    },
                },
            ),
            self._handle_scan_value_stocks,
        )

    async def _handle_get_stock_quote(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get stock quote data."""
        symbol = args["symbol"]

        # In real implementation, this would call IBKR or other data source
        # For now, return mock data
        return {
            "symbol": symbol,
            "price": 150.0 + (hash(symbol) % 100),  # Mock price
            "volume": 1000000,
            "market_cap": 50000000000,
            "sector": "Technology",
        }

    async def _handle_get_fundamentals(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get fundamental data."""
        symbol = args["symbol"]

        # Mock fundamental data based on symbol
        base_data = {
            "symbol": symbol,
            "pe_ratio": 12.5 + (hash(symbol) % 20),
            "pb_ratio": 0.8 + (hash(symbol) % 0.8),
            "roe": 0.12 + (hash(symbol) % 0.10),
            "debt_equity": 0.3 + (hash(symbol) % 0.4),
            "current_ratio": 1.2 + (hash(symbol) % 0.8),
            "fcf_yield": 0.05 + (hash(symbol) % 0.05),
            "dividend_yield": 0.02 + (hash(symbol) % 0.02),
        }

        return base_data

    async def _handle_get_short_interest(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get short interest and squeeze data."""
        symbol = args["symbol"]

        # Mock squeeze data
        short_interest = 0.15 + (hash(symbol) % 0.25)  # 15-40%
        days_to_cover = 3 + (hash(symbol) % 8)  # 3-11 days
        borrow_cost = 0.02 + (hash(symbol) % 0.15)  # 2-17%
        float_available = 0.10 + (hash(symbol) % 0.20)  # 10-30%

        squeeze_score = self._calculate_squeeze_score(
            short_interest, days_to_cover, borrow_cost, float_available
        )

        return {
            "symbol": symbol,
            "short_interest_pct": short_interest,
            "days_to_cover": days_to_cover,
            "cost_to_borrow": borrow_cost,
            "float_available_pct": float_available,
            "squeeze_score": squeeze_score,
        }

    async def _handle_analyze_sector(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sector positioning."""
        symbol = args["symbol"]

        # Mock sector analysis
        return {
            "symbol": symbol,
            "sector": "Technology",
            "sector_performance": 0.12,  # 12% sector return
            "relative_strength": 0.85,  # 85th percentile
            "peer_comparison": {"avg_pe": 18.5, "avg_pb": 2.1, "avg_roe": 0.15},
        }

    async def _handle_scan_value_stocks(
        self, args: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Scan for undervalued stocks."""
        # Mock scan results
        mock_stocks = [
            {"symbol": "AAPL", "pe": 12.3, "pb": 0.8, "roe": 0.18, "fcf_yield": 0.08},
            {"symbol": "MSFT", "pe": 15.7, "pb": 1.2, "roe": 0.22, "fcf_yield": 0.06},
            {"symbol": "GOOGL", "pe": 11.2, "pb": 0.7, "roe": 0.16, "fcf_yield": 0.09},
            {"symbol": "TSLA", "pe": 45.8, "pb": 3.2, "roe": 0.08, "fcf_yield": 0.02},
            {"symbol": "NVDA", "pe": 22.1, "pb": 2.8, "roe": 0.25, "fcf_yield": 0.04},
        ]

        # Filter based on criteria
        filtered = []
        for stock in mock_stocks:
            if (
                stock["pe"] <= args.get("max_pe", 20)
                and stock["pb"] <= args.get("max_pb", 2.0)
                and stock["roe"] >= args.get("min_roe", 0.10)
            ):
                filtered.append(stock)

        return filtered[: args.get("limit", 10)]

    def _calculate_squeeze_score(
        self,
        short_interest: float,
        days_to_cover: float,
        borrow_cost: float,
        float_available: float,
    ) -> float:
        """
        Calculate squeeze score (0-100).

        Args:
            short_interest: Short interest as percentage
            days_to_cover: Days to cover
            borrow_cost: Cost to borrow as percentage
            float_available: Available float percentage

        Returns:
            Squeeze score from 0-100
        """
        # Normalize each factor
        short_score = min(short_interest / 0.7, 1.0) * 40  # Max 40 points
        days_score = min(days_to_cover / 10, 1.0) * 30  # Max 30 points
        borrow_score = min(borrow_cost / 0.20, 1.0) * 20  # Max 20 points
        availability_score = (1 - float_available) * 10  # Max 10 points

        total_score = short_score + days_score + borrow_score + availability_score

        # Categorize
        if total_score >= 80:
            category = "Extreme"
        elif total_score >= 60:
            category = "High"
        elif total_score >= 40:
            category = "Moderate"
        else:
            category = "Low"

        return min(total_score, 100.0)

    async def analyze_stock(self, symbol: str) -> StockAnalysis:
        """
        Comprehensive analysis of a stock for trading opportunities.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            Complete stock analysis
        """
        # Gather data using tools
        quote_data = await self._handle_get_stock_quote({"symbol": symbol})
        fundamentals = await self._handle_get_fundamentals({"symbol": symbol})
        squeeze_data = await self._handle_get_short_interest({"symbol": symbol})

        # Calculate deep value score
        deep_value_score = self._calculate_deep_value_score(fundamentals)

        # Use squeeze data
        squeeze_score = squeeze_data["squeeze_score"]

        # Calculate overall score (weighted average)
        overall_score = (deep_value_score * 0.6) + (squeeze_score * 0.4)

        # Generate thesis and recommendations
        thesis = self._generate_thesis(symbol, quote_data, fundamentals, squeeze_data)
        catalysts = self._identify_catalysts(symbol, fundamentals, squeeze_data)
        risks = self._identify_risks(symbol, fundamentals, squeeze_data)

        # Calculate position sizing
        position_size_pct = self._calculate_position_size(overall_score, squeeze_score)

        # Set target and stop prices
        current_price = quote_data["price"]
        target_price = current_price * (
            1 + (overall_score / 100) * 0.5
        )  # 50% of score as upside
        stop_price = current_price * (1 - 0.08)  # 8% stop loss

        # Determine recommendation
        if overall_score >= 70 and squeeze_score >= 60:
            recommendation = "STRONG_BUY"
        elif overall_score >= 60:
            recommendation = "BUY"
        elif overall_score >= 40:
            recommendation = "WATCH"
        else:
            recommendation = "AVOID"

        confidence = min(overall_score / 100, 0.9)  # Cap at 90%

        return StockAnalysis(
            symbol=symbol,
            deep_value_score=deep_value_score,
            squeeze_score=squeeze_score,
            overall_score=overall_score,
            recommendation=recommendation,
            thesis=thesis,
            catalysts=catalysts,
            risks=risks,
            target_price=target_price,
            stop_price=stop_price,
            position_size_pct=position_size_pct,
            confidence=confidence,
        )

    def _calculate_deep_value_score(self, fundamentals: Dict[str, Any]) -> float:
        """
        Calculate deep value score (0-100) based on fundamentals.

        Args:
            fundamentals: Fundamental data dictionary

        Returns:
            Deep value score
        """
        score = 0.0

        # P/E ratio (lower is better)
        pe = fundamentals.get("pe_ratio", 20)
        if pe <= 10:
            score += 25
        elif pe <= 15:
            score += 20
        elif pe <= 20:
            score += 15
        else:
            score += 10

        # P/B ratio (lower is better)
        pb = fundamentals.get("pb_ratio", 2.0)
        if pb <= 1.0:
            score += 20
        elif pb <= 1.5:
            score += 15
        elif pb <= 2.0:
            score += 10
        else:
            score += 5

        # ROE (higher is better)
        roe = fundamentals.get("roe", 0.10)
        if roe >= 0.20:
            score += 20
        elif roe >= 0.15:
            score += 15
        elif roe >= 0.10:
            score += 10
        else:
            score += 5

        # FCF Yield (higher is better)
        fcf_yield = fundamentals.get("fcf_yield", 0.03)
        if fcf_yield >= 0.08:
            score += 15
        elif fcf_yield >= 0.06:
            score += 12
        elif fcf_yield >= 0.04:
            score += 8
        else:
            score += 4

        # Debt/Equity (lower is better)
        debt_equity = fundamentals.get("debt_equity", 0.5)
        if debt_equity <= 0.3:
            score += 10
        elif debt_equity <= 0.5:
            score += 7
        elif debt_equity <= 1.0:
            score += 4
        else:
            score += 1

        # Current Ratio (higher is better)
        current_ratio = fundamentals.get("current_ratio", 1.0)
        if current_ratio >= 2.0:
            score += 10
        elif current_ratio >= 1.5:
            score += 7
        elif current_ratio >= 1.0:
            score += 4
        else:
            score += 1

        return min(score, 100.0)

    def _generate_thesis(
        self,
        symbol: str,
        quote: Dict[str, Any],
        fundamentals: Dict[str, Any],
        squeeze: Dict[str, Any],
    ) -> str:
        """
        Generate investment thesis for the stock.

        Args:
            symbol: Stock symbol
            quote: Quote data
            fundamentals: Fundamental data
            squeeze: Squeeze data

        Returns:
            Investment thesis string
        """
        current_price = quote["price"]
        pe = fundamentals.get("pe_ratio", 0)
        pb = fundamentals.get("pb_ratio", 0)
        roe = fundamentals.get("roe", 0) * 100
        short_interest = squeeze.get("short_interest_pct", 0) * 100
        days_to_cover = squeeze.get("days_to_cover", 0)

        thesis_parts = []

        # Deep value thesis
        if pe < 15 and pb < 1.5:
            thesis_parts.append(
                f"Deep value opportunity with attractive fundamentals: P/E {pe:.1f}x, P/B {pb:.2f}x, "
                f"ROE {roe:.1f}%. Trading significantly below intrinsic value."
            )

        # Squeeze potential
        if short_interest > 20 and days_to_cover > 5:
            thesis_parts.append(
                f"Strong short squeeze potential with {short_interest:.1f}% short interest "
                f"and {days_to_cover:.1f} days to cover. Borrow costs elevated, "
                "indicating short sellers are under pressure."
            )

        # Growth potential
        if roe > 15:
            thesis_parts.append(
                f"Strong growth potential with {roe:.1f}% ROE indicating efficient capital allocation "
                "and competitive advantages."
            )

        # Risk/reward summary
        upside_potential = (
            squeeze.get("squeeze_score", 0) + fundamentals.get("fcf_yield", 0) * 1000
        ) / 100
        downside_risk = 0.08  # 8% stop loss

        thesis_parts.append(
            f"Asymmetric risk/reward: Potential {upside_potential:.0%} upside vs "
            f"{downside_risk:.0%} downside risk."
        )

        return (
            " ".join(thesis_parts) if thesis_parts else f"{symbol} analysis completed."
        )

    def _identify_catalysts(
        self, symbol: str, fundamentals: Dict[str, Any], squeeze: Dict[str, Any]
    ) -> List[str]:
        """
        Identify potential catalysts for the stock.

        Args:
            symbol: Stock symbol
            fundamentals: Fundamental data
            squeeze: Squeeze data

        Returns:
            List of potential catalysts
        """
        catalysts = []

        # Earnings catalyst
        catalysts.append("Next earnings report could be catalyst")

        # Squeeze catalysts
        if squeeze.get("short_interest_pct", 0) > 0.25:
            catalysts.append("Short squeeze potential if positive news emerges")

        # Value catalysts
        if fundamentals.get("pe_ratio", 20) < 12:
            catalysts.append("Market may revalue stock as fundamentals improve")

        # Sector catalysts
        catalysts.append("Sector rotation or market sentiment shift")

        return catalysts

    def _identify_risks(
        self, symbol: str, fundamentals: Dict[str, Any], squeeze: Dict[str, Any]
    ) -> List[str]:
        """
        Identify key risks for the stock.

        Args:
            symbol: Stock symbol
            fundamentals: Fundamental data
            squeeze: Squeeze data

        Returns:
            List of key risks
        """
        risks = []

        # High valuation risk
        if fundamentals.get("pe_ratio", 0) > 25:
            risks.append("Elevated P/E ratio suggests limited margin of safety")

        # Debt risk
        if fundamentals.get("debt_equity", 0) > 1.0:
            risks.append("High debt levels increase financial risk")

        # Squeeze risks
        if squeeze.get("short_interest_pct", 0) > 0.40:
            risks.append("Very high short interest could lead to volatility")

        # Market risk
        risks.append("Market downturn could pressure stock price")

        # Liquidity risk
        if fundamentals.get("current_ratio", 1.0) < 1.0:
            risks.append("Low current ratio indicates liquidity concerns")

        return risks

    def _calculate_position_size(
        self, overall_score: float, squeeze_score: float
    ) -> float:
        """
        Calculate recommended position size as percentage.

        Args:
            overall_score: Overall analysis score (0-100)
            squeeze_score: Squeeze score (0-100)

        Returns:
            Position size percentage
        """
        # Base position size from overall score
        base_size = overall_score / 100 * 0.05  # Max 5%

        # Adjust for squeeze potential
        squeeze_multiplier = 1 + (squeeze_score / 100) * 0.5  # Up to 50% more

        # Apply Kelly-like adjustment
        kelly_adjustment = 0.25  # Use 25% of "Kelly" sizing

        position_size = base_size * squeeze_multiplier * kelly_adjustment

        # Hard limits
        return min(position_size, 0.05)  # Max 5%

    async def analyze_opportunity(self, symbol: str) -> AgentResponse:
        """
        Analyze a trading opportunity and provide recommendation.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            Agent response with analysis
        """
        try:
            analysis = await self.analyze_stock(symbol)

            response_content = f"""
# Analysis for {analysis.symbol}

**Overall Score:** {analysis.overall_score:.0f}/100 (Confidence: {analysis.confidence:.0%})
**Deep Value Score:** {analysis.deep_value_score:.0f}/100
**Squeeze Score:** {analysis.squeeze_score:.0f}/100

## Recommendation: {analysis.recommendation}

### Investment Thesis
{analysis.thesis}

### Catalysts
{chr(10).join(f"• {catalyst}" for catalyst in analysis.catalysts)}

### Key Risks
{chr(10).join(f"• {risk}" for risk in analysis.risks)}

### Position Sizing
- **Recommended Size:** {analysis.position_size_pct:.1%}
- **Target Price:** ${analysis.target_price:.2f}
- **Stop Loss:** ${analysis.stop_price:.2f}
- **Risk/Reward Ratio:** {((analysis.target_price - 150) / (150 - analysis.stop_price)):.1f}:1

### Risk Management
- Maximum position: 5% of portfolio
- Total portfolio heat: ≤15%
- Monitor for thesis breaks
- Exit if stop loss hit
"""

            return AgentResponse(
                content=response_content,
                metadata={
                    "symbol": symbol,
                    "analysis": analysis.__dict__,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return AgentResponse(
                content=f"I apologize, but I encountered an error analyzing {symbol}: {str(e)}",
                metadata={"error": str(e)},
            )

    async def scan_opportunities(self, strategy: str = "both") -> AgentResponse:
        """
        Scan for trading opportunities.

        Args:
            strategy: Strategy to scan ('deep_value', 'squeeze', 'both')

        Returns:
            Agent response with opportunities
        """
        try:
            opportunities = []

            if strategy in ["deep_value", "both"]:
                # Scan for value stocks
                value_stocks = await self._handle_scan_value_stocks(
                    {
                        "max_pe": self.deep_value_config.criteria.get("p_e_max", 15),
                        "max_pb": self.deep_value_config.criteria.get("p_b_max", 1.0),
                        "min_roe": self.deep_value_config.criteria.get("roe_min", 0.15),
                        "limit": 10,
                    }
                )

                for stock in value_stocks:
                    analysis = await self.analyze_stock(stock["symbol"])
                    if analysis.overall_score >= 60:  # Only high-quality opportunities
                        opportunities.append(analysis)

            if strategy in ["squeeze", "both"]:
                # Scan for squeeze candidates (mock for now)
                squeeze_candidates = ["GME", "AMC", "BB", "EXPR"]  # Would be real scan

                for symbol in squeeze_candidates:
                    try:
                        analysis = await self.analyze_stock(symbol)
                        if analysis.squeeze_score >= 60:  # High squeeze potential
                            opportunities.append(analysis)
                    except Exception:
                        continue  # Skip if analysis fails

            # Sort by overall score
            opportunities.sort(key=lambda x: x.overall_score, reverse=True)

            # Format response
            if not opportunities:
                content = "No high-quality opportunities found at this time."
            else:
                content = f"""# Top Trading Opportunities ({len(opportunities)} found)

"""
                for i, opp in enumerate(opportunities[:5], 1):  # Top 5
                    content += f"""{i}. **{opp.symbol}** - Score: {opp.overall_score:.0f}/100
   - Deep Value: {opp.deep_value_score:.0f}/100 | Squeeze: {opp.squeeze_score:.0f}/100
   - Recommendation: {opp.recommendation}
   - Thesis: {opp.thesis[:100]}{'...' if len(opp.thesis) > 100 else ''}
   - Position Size: {opp.position_size_pct:.1%} | Target: ${opp.target_price:.0f}

"""

            return AgentResponse(
                content=content,
                metadata={
                    "strategy": strategy,
                    "opportunities_count": len(opportunities),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")
            return AgentResponse(
                content=f"I apologize, but I encountered an error scanning for opportunities: {str(e)}",
                metadata={"error": str(e)},
            )
