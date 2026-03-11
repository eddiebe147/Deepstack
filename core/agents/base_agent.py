"""
Base Agent - Foundation for all DeepStack AI agents

Provides common functionality for Claude AI integration, tool calling,
context management, and prompt templating. All trading agents inherit from this.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel

from ..config import get_config
from ..consciousness import DaeConsciousness

logger = logging.getLogger(__name__)

# Singleton consciousness loader — loaded once, shared across agents
_dae_consciousness: Optional[DaeConsciousness] = None


def get_consciousness() -> DaeConsciousness:
    """Get or initialize the Dae consciousness loader."""
    global _dae_consciousness
    if _dae_consciousness is None:
        _dae_consciousness = DaeConsciousness()
        _dae_consciousness.load()
    return _dae_consciousness


class Tool(BaseModel):
    """Represents a tool that agents can call."""

    name: str
    description: str
    input_schema: Dict[str, Any]

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        super().__init__(name=name, description=description, input_schema=input_schema)


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""

    tool_name: str
    arguments: Dict[str, Any]


class AgentResponse(BaseModel):
    """Response from an agent."""

    content: str
    tool_calls: List[ToolCall] = []
    metadata: Dict[str, Any] = {}


class BaseAgent:
    """
    Base class for all DeepStack AI agents.

    Provides:
    - Claude client integration
    - Tool calling framework
    - Context management
    - Prompt templating
    - Error handling
    """

    def __init__(self, name: str, description: str, config: Optional[Any] = None):
        """
        Initialize base agent.

        Args:
            name: Agent name for logging
            description: Agent description
            config: DeepStack configuration (uses global if None)
        """
        self.name = name
        self.description = description
        self.config = config or get_config()

        # Claude client
        self.anthropic = Anthropic(api_key=self.config.anthropic_api_key)

        # OpenAI-compatible clients
        self.perplexity = None
        if self.config.perplexity_api_key:
            self.perplexity = OpenAI(
                api_key=self.config.perplexity_api_key,
                base_url="https://api.perplexity.ai",
            )

        self.deepseek = None
        if self.config.deepseek_api_key:
            self.deepseek = OpenAI(
                api_key=self.config.deepseek_api_key,
                base_url="https://api.deepseek.com",
            )

        self.xai = None
        if self.config.xai_api_key:
            self.xai = OpenAI(
                api_key=self.config.xai_api_key, base_url="https://api.x.ai/v1"
            )

        # Default model
        self.model = self.config.llm_model or "claude-3-5-sonnet-20241022"

        # Context management
        self.context: List[Dict[str, str]] = []
        self.max_context_length = 10

        # Tools registry
        self.tools: Dict[str, Tool] = {}
        self.tool_handlers: Dict[str, Callable] = {}

        # Knowledge base integration
        self.knowledge_base_path = Path("knowledge-base")

        logger.info(f"BaseAgent '{name}' initialized")

    def register_tool(self, tool: Tool, handler: Callable):
        """
        Register a tool with the agent.

        Args:
            tool: Tool definition
            handler: Function to handle tool calls
        """
        self.tools[tool.name] = tool
        self.tool_handlers[tool.name] = handler
        logger.debug(f"Registered tool: {tool.name}")

    def get_tools_for_claude(self) -> List[Dict[str, Any]]:
        """
        Get tools in format expected by Claude API.

        Returns:
            List of tool definitions for Claude
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self.tools.values()
        ]

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 1024,
    ) -> Any:
        """
        Call LLM API (Claude, Perplexity, DeepSeek, or Grok).

        Args:
            messages: List of message dictionaries
            tools: Optional tools to make available
            max_tokens: Maximum tokens in response

        Returns:
            API response object (normalized)
        """
        try:
            # Add system context
            system_message = self._build_system_message()

            # Provider dispatch
            if "claude" in self.model:
                return await self._call_claude(
                    messages, system_message, tools, max_tokens
                )
            elif "sonar" in self.model:
                return await self._call_openai_compatible(
                    self.perplexity, messages, system_message, tools, max_tokens
                )
            elif "deepseek" in self.model:
                return await self._call_openai_compatible(
                    self.deepseek, messages, system_message, tools, max_tokens
                )
            elif "grok" in self.model:
                return await self._call_openai_compatible(
                    self.xai, messages, system_message, tools, max_tokens
                )
            else:
                # Default to Claude if unknown
                logger.warning(f"Unknown model {self.model}, defaulting to Claude")
                return await self._call_claude(
                    messages, system_message, tools, max_tokens
                )

        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            raise

    async def _call_claude(self, messages, system_message, tools, max_tokens):
        """Internal method to call Claude."""
        messages_with_system = [system_message] + messages

        request_params = {
            "model": self.model,
            "messages": messages_with_system,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        return await asyncio.get_event_loop().run_in_executor(
            None, self.anthropic.messages.create, **request_params
        )

    async def _call_openai_compatible(
        self, client, messages, system_message, tools, max_tokens
    ):
        """Internal method to call OpenAI-compatible APIs."""
        if not client:
            raise ValueError(
                f"Client for model {self.model} is not initialized (missing API key?)"
            )

        # Convert system message to OpenAI format (separate role)
        formatted_messages = [
            {"role": "system", "content": system_message["content"]}
        ] + messages

        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
        }

        # Note: Tool calling format might differ slightly, but basic chat works.
        # For now, we'll skip tools for non-Claude models to ensure basic chat works,
        # or we'd need to adapt tool schemas.
        # DeepSeek/Grok tool support varies.

        response = await asyncio.get_event_loop().run_in_executor(
            None, client.chat.completions.create, **request_params
        )

        # Normalize response to look like Claude's for easy consumption
        # Create a mock object or simple structure
        class MockResponse:
            def __init__(self, content_text):
                self.content = [type("obj", (object,), {"text": content_text})]
                self.tool_calls = []
                self.usage = type("obj", (object,), {"input_tokens": 0})

        return MockResponse(response.choices[0].message.content)

    def _build_system_message(self) -> Dict[str, str]:
        """
        Build system message from Dae consciousness files.

        Composes the system prompt from the CaF consciousness layers:
        - Brainstem: identity, values, purpose (always loaded)
        - Limbic: fears, goals, tilt detection (always loaded)
        - Cortical: economic reasoning (always loaded)
        - Memory: working/semantic (optional, heavier)

        Falls back to legacy hardcoded prompt if consciousness files
        are not available.

        Returns:
            System message dictionary
        """
        consciousness = get_consciousness()

        if consciousness._loaded and consciousness._cache:
            # Compose from consciousness files
            consciousness_prompt = consciousness.compose_system_prompt(
                include_memory=False
            )

            # Load trader philosophies as supplemental knowledge
            philosophies = self._load_trader_philosophies()

            system_prompt = f"""You are Dae — DeepStack Autonomous Engine.

{consciousness_prompt}

---

## Master Trader Wisdom (Supplemental)
{philosophies}

## Risk Management Rules
- Maximum 5% per position (hard limit)
- Maximum 15% portfolio heat (total risk)
- 2% risk per trade (never more)
- Kelly Criterion with 0.2x-0.3x fractional sizing
- Never move stop losses down (only up)
- Thesis break = immediate exit

## Response Format
When using tools, respond with JSON tool calls.
When providing analysis, be comprehensive but concise.
Always explain your reasoning step by step.
"""
            logger.info("System prompt composed from Dae consciousness files")

        else:
            # Fallback: legacy hardcoded prompt
            philosophies = self._load_trader_philosophies()

            system_prompt = f"""
You are {self.name}, an AI trading agent in the DeepStack autonomous trading system.

{self.description}

## Core Trading Philosophy
- Find deep value opportunities (downside protection)
- Identify short squeeze potential (explosive upside)
- Asymmetric risk/reward: Risk $1 to make $10+
- Systematic discipline that protects from emotions

## Master Trader Wisdom
{philosophies}

## Risk Management Rules
- Maximum 5% per position (hard limit)
- Maximum 15% portfolio heat (total risk)
- 2% risk per trade (never more)
- Kelly Criterion with 0.2x-0.3x fractional sizing
- Never move stop losses down (only up)
- Thesis break = immediate exit

## Your Role
You must:
1. Always provide reasoned analysis
2. Quantify risks and rewards
3. Document your thesis clearly
4. Follow risk management rules strictly
5. Use available tools to gather data
6. Admit when you don't know something

## Response Format
When using tools, respond with JSON tool calls.
When providing analysis, be comprehensive but concise.
Always explain your reasoning step by step.
"""
            logger.warning(
                "Consciousness files not loaded — using legacy system prompt"
            )

        return {"role": "system", "content": system_prompt}

    def _load_trader_philosophies(self) -> str:
        """
        Load trader philosophies from knowledge base.

        Returns:
            Formatted trader wisdom string
        """
        try:
            philosophy_file = self.knowledge_base_path / "trader_philosophies.yaml"
            if not philosophy_file.exists():
                return "Using default trading principles."

            import yaml

            with open(philosophy_file, "r") as f:
                data = yaml.safe_load(f)

            philosophies = []
            for trader, info in data.get("traders", {}).items():
                philosophies.append(
                    f"**{info['name']}**: {info['philosophy']}\n"
                    f"Key principles: {'; '.join(info['key_principles'][:3])}"
                )

            return "\n\n".join(philosophies)

        except Exception as e:
            logger.error(f"Error loading trader philosophies: {e}")
            return "Using default trading principles."

    def add_context(self, role: str, content: str):
        """
        Add message to context.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        self.context.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        # Keep context manageable
        if len(self.context) > self.max_context_length:
            self.context = self.context[-self.max_context_length :]

    def get_recent_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get recent context messages.

        Args:
            limit: Number of messages to return

        Returns:
            List of recent messages
        """
        return self.context[-limit:]

    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """
        Execute a tool call.

        Args:
            tool_call: Tool call to execute

        Returns:
            Tool execution result
        """
        tool_name = tool_call.tool_name
        arguments = tool_call.arguments

        if tool_name not in self.tool_handlers:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self.tool_handlers[tool_name]

        try:
            logger.debug(f"Executing tool: {tool_name} with args: {arguments}")
            result = await handler(arguments)
            logger.debug(f"Tool {tool_name} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise

    async def process_message(self, user_message: str) -> AgentResponse:
        """
        Process a user message and return agent response.

        Args:
            user_message: User input message

        Returns:
            Agent response with content and tool calls
        """
        # Add user message to context
        self.add_context("user", user_message)

        # Get recent context for this conversation
        context_messages = self.get_recent_context()

        # Build messages for Claude
        messages = []
        for msg in context_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        try:
            # Call LLM with tools
            response = await self.call_llm(
                messages, tools=self.get_tools_for_claude(), max_tokens=2048
            )

            # Parse response
            assistant_content = response.content[0].text if response.content else ""

            # Check for tool calls
            tool_calls = []
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_calls.append(
                        ToolCall(
                            tool_name=tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                        )
                    )

            # Add assistant response to context
            self.add_context("assistant", assistant_content)

            return AgentResponse(
                content=assistant_content,
                tool_calls=tool_calls,
                metadata={
                    "model": self.model,
                    "timestamp": datetime.now().isoformat(),
                    "tokens_used": (
                        response.usage.input_tokens if hasattr(response, "usage") else 0
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return AgentResponse(
                content=("Error processing your request: " f"{str(e)}"),
                metadata={"error": str(e)},
            )

    async def run_with_tools(self, user_message: str) -> AgentResponse:
        """
        Run agent with tool calling until no more tools are needed.

        Args:
            user_message: Initial user message

        Returns:
            Final agent response
        """
        current_response = await self.process_message(user_message)

        # Execute tool calls if present
        while current_response.tool_calls:
            for tool_call in current_response.tool_calls:
                try:
                    tool_result = await self.execute_tool_call(tool_call)

                    # Add tool result to context
                    tool_message = (
                        f"Tool {tool_call.tool_name} result: {json.dumps(tool_result)}"
                    )
                    self.add_context("system", tool_message)

                except Exception as e:
                    error_message = f"Tool {tool_call.tool_name} failed: {str(e)}"
                    self.add_context("system", error_message)

            # Get next response after tool execution
            context_messages = self.get_recent_context()
            messages = []
            for msg in context_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})

            try:
                response = await self.call_llm(
                    messages, tools=self.get_tools_for_claude(), max_tokens=2048
                )

                assistant_content = response.content[0].text if response.content else ""
                self.add_context("assistant", assistant_content)

                current_response = AgentResponse(
                    content=assistant_content,
                    tool_calls=[
                        ToolCall(
                            tool_name=tc.function.name,
                            arguments=json.loads(tc.function.arguments),
                        )
                        for tc in (response.tool_calls or [])
                    ],
                    metadata={
                        "model": self.model,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            except Exception as e:
                logger.error(f"Error in tool response processing: {e}")
                current_response = AgentResponse(
                    content=("Error processing tool results."),
                    metadata={"error": str(e)},
                )
                break

        return current_response

    # Common utility methods for agents

    def format_portfolio_data(self, positions: List[Dict[str, Any]]) -> str:
        """Format portfolio positions for display."""
        if not positions:
            return "No open positions."

        lines = ["**Current Positions:**"]
        for pos in positions:
            pnl_color = "🟢" if pos.get("unrealized_pnl", 0) >= 0 else "🔴"
            sym = pos["symbol"]
            shares = pos["position"]
            cost = pos["avg_cost"]
            pnl = pos.get("unrealized_pnl", 0)
            lines.append(
                f"{pnl_color} {sym}: {shares} shares "
                f"@ ${cost:.2f} (P&L: ${pnl:+.2f})"
            )

        return "\n".join(lines)

    def format_risk_metrics(self, portfolio_heat: float, daily_pnl: float) -> str:
        """Format risk metrics for display."""
        heat_status = "✅" if portfolio_heat <= 0.15 else "⚠️"
        pnl_status = "🟢" if daily_pnl >= 0 else "🔴"

        return (
            f"**Risk Metrics:**\n"
            f"{heat_status} Portfolio Heat: {portfolio_heat:.1%} (max: 15%)\n"
            f"{pnl_status} Daily P&L: ${daily_pnl:+.2f}"
        )

    def format_market_data(self, quotes: Dict[str, Dict[str, Any]]) -> str:
        """Format market data for display."""
        lines = ["**Market Data:**"]
        for symbol, quote in quotes.items():
            price = quote.get("last", "N/A")
            change = quote.get("change", "N/A")
            lines.append(f"{symbol}: ${price} ({change})")

        return "\n".join(lines)

    def calculate_position_size(
        self, entry_price: float, stop_price: float, risk_pct: float = 0.02
    ) -> int:
        """
        Calculate position size based on risk management.

        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            risk_pct: Risk percentage (default 2%)

        Returns:
            Position size in shares
        """
        portfolio_value = 100000  # Would get from portfolio manager
        risk_amount = portfolio_value * risk_pct
        risk_per_share = abs(entry_price - stop_price)

        if risk_per_share == 0:
            return 0

        shares = int(risk_amount / risk_per_share)

        # Apply maximum position limits
        max_position_value = portfolio_value * 0.05  # 5% max
        max_shares_by_value = int(max_position_value / entry_price)

        return min(shares, max_shares_by_value)
