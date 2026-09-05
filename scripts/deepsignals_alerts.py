#!/usr/bin/env python3
"""
DeepSignals Alert Engine

Checks collected data for significant signals and sends Telegram
alerts via the HYDRA bot (@hydra_id8_bot).

Alert conditions:
  - Unusual options flow (volume > 10x open interest)
  - Cluster insider buying (3+ insiders on same ticker in 7 days)
  - Extreme dark pool ratios (short volume > 60%)
  - Extreme CBOE put/call ratios (PCR > 1.2 or < 0.5)

Telegram credentials loaded from ~/.hydra/config/telegram.env

Usage:
  python scripts/deepsignals_alerts.py           # Check all conditions
  python scripts/deepsignals_alerts.py --dry-run  # Print alerts without sending
"""

import argparse
import asyncio
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import List

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.data.cboe_client import CBOEClient
from core.data.finra_client import FINRAClient
from core.data.sec_edgar_client import SECEdgarClient

# ── Logging ──────────────────────────────────────────────────────

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(LOG_DIR, "deepsignals_alerts.log"),
            encoding="utf-8",
        ),
    ],
)
# httpx includes full request URLs in INFO logs. Telegram embeds the bot token
# in the URL path, so suppress transport-level request logging.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("deepsignals.alerts")


# ── Telegram ─────────────────────────────────────────────────────


def load_hydra_telegram_env():
    """Load Telegram credentials from HYDRA config."""
    env_path = os.path.expanduser("~/.hydra/config/telegram.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)
        logger.info("Loaded HYDRA Telegram config")
    else:
        logger.warning(f"HYDRA Telegram config not found: {env_path}")


async def send_telegram(message: str, dry_run: bool = False) -> bool:
    """
    Send an HTML-formatted message via the HYDRA Telegram bot.

    Returns True on success.
    """
    if dry_run:
        print(f"\n--- DRY RUN ALERT ---\n{message}\n--- END ---\n")
        return True

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    import httpx

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert sent successfully")
                return True
            else:
                logger.error(
                    f"Telegram API error: {resp.status_code} - {resp.text[:200]}"
                )
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


# ── Alert Checks ─────────────────────────────────────────────────


async def check_extreme_pcr() -> List[str]:
    """Check CBOE put/call ratios for extreme readings."""
    alerts: List[str] = []
    client = CBOEClient()

    try:
        total = await client.get_put_call_ratio("total")
        percentile = await client.get_pcr_percentile("total")
        pcr = total.put_call_ratio

        if pcr > 1.2:
            alerts.append(
                f"<b>CBOE Extreme Fear</b>\n"
                f"Total PCR: <code>{pcr:.3f}</code>\n"
                f"Percentile: <code>{percentile:.0%}</code> (vs 252-day)\n"
                f"<i>Elevated put buying indicates extreme fear</i>"
            )
        elif pcr < 0.5:
            alerts.append(
                f"<b>CBOE Extreme Greed</b>\n"
                f"Total PCR: <code>{pcr:.3f}</code>\n"
                f"Percentile: <code>{percentile:.0%}</code> (vs 252-day)\n"
                f"<i>Low put buying indicates extreme complacency</i>"
            )

        logger.info(
            f"PCR check: total={pcr:.3f}, percentile={percentile:.1%}, "
            f"alerts={len(alerts)}"
        )
    except Exception as e:
        logger.error(f"PCR check failed: {e}")
    finally:
        await client.close()

    return alerts


async def check_dark_pool() -> List[str]:
    """Check for extreme dark pool short ratios (> 60%)."""
    alerts: List[str] = []
    client = FINRAClient()

    try:
        top = await client.get_top_dark_pool_activity(limit=20)
        extreme = [r for r in top if r.short_ratio > 0.60]

        if extreme:
            lines = [
                f"<b>Dark Pool Alert</b> - {len(extreme)} tickers "
                f"with &gt;60% short ratio\n"
            ]
            for r in extreme[:10]:
                lines.append(
                    f"  <code>{r.symbol:6s}</code> "
                    f"{r.short_ratio:.1%} "
                    f"({r.short_volume:>10,} / {r.total_volume:>12,})"
                )
            alerts.append("\n".join(lines))

        logger.info(
            f"Dark pool check: {len(top)} tickers scanned, {len(extreme)} extreme"
        )
    except Exception as e:
        logger.error(f"Dark pool check failed: {e}")
    finally:
        await client.close()

    return alerts


async def check_insider_clusters() -> List[str]:
    """Check for cluster insider buying (3+ insiders on same ticker in 7 days)."""
    alerts: List[str] = []
    client = SECEdgarClient()

    try:
        trades = await client.get_recent_insider_trades(limit=200)

        # Group buys by ticker
        buy_by_ticker: dict[str, list] = defaultdict(list)
        for t in trades:
            if t.transaction_type == "buy":
                buy_by_ticker[t.ticker].append(t)

        for ticker, buys in buy_by_ticker.items():
            if len(buys) >= 3:
                total_value = sum(t.total_value for t in buys if t.total_value)
                filers = [t.filer_name for t in buys[:5]]

                alerts.append(
                    f"<b>Insider Cluster Buy: {ticker}</b>\n"
                    f"<code>{len(buys)}</code> insiders buying\n"
                    f"Total value: <code>${total_value:,.0f}</code>\n"
                    f"Buyers: <i>{', '.join(filers)}</i>"
                )

        logger.info(
            f"Insider check: {len(trades)} trades, {len(alerts)} cluster alerts"
        )
    except Exception as e:
        logger.error(f"Insider check failed: {e}")
    finally:
        await client.close()

    return alerts


# ── Main ─────────────────────────────────────────────────────────


async def run_alerts(dry_run: bool = False):
    """Run all alert checks and send Telegram notifications."""
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"DeepSignals alert check starting (dry_run={dry_run})")

    # Load HYDRA telegram credentials
    load_hydra_telegram_env()

    # Run all checks concurrently
    results = await asyncio.gather(
        check_extreme_pcr(),
        check_dark_pool(),
        check_insider_clusters(),
        return_exceptions=True,
    )

    all_alerts: List[str] = []
    check_names = ["PCR", "Dark Pool", "Insider Clusters"]
    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            logger.error(f"{name} check raised: {result}")
        else:
            all_alerts.extend(result)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Alert checks complete in {elapsed:.1f}s, {len(all_alerts)} alerts")

    if all_alerts:
        header = (
            f"<b>DeepSignals Alert</b> - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{'=' * 30}\n\n"
        )
        message = header + "\n\n".join(all_alerts)

        # Telegram 4096 char limit
        if len(message) > 4000:
            message = message[:3950] + "\n\n<i>...truncated</i>"

        await send_telegram(message, dry_run=dry_run)
    else:
        logger.info("No significant signals detected")
        if dry_run:
            print("No alerts to send.")


def main():
    parser = argparse.ArgumentParser(
        prog="deepsignals_alerts",
        description=(
            "DeepSignals alert engine: checks for significant signals "
            "and sends Telegram alerts"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print alerts to stdout instead of sending to Telegram",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_alerts(dry_run=args.dry_run))
    except KeyboardInterrupt:
        logger.info("Alert check interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
