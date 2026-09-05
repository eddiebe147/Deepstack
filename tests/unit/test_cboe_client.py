from datetime import datetime, timedelta

import pytest

from core.data.cboe_client import CBOEClient, PutCallData


def _row(date: str) -> PutCallData:
    return PutCallData(
        date=date,
        call_volume=100,
        put_volume=50,
        total_volume=150,
        put_call_ratio=0.5,
    )


@pytest.mark.asyncio
async def test_get_put_call_ratio_accepts_fresh_data(monkeypatch):
    client = CBOEClient()
    today = datetime.now().strftime("%Y-%m-%d")

    async def fetch(_ratio_type):
        return [_row(today)]

    monkeypatch.setattr(client, "_fetch_csv", fetch)
    assert (await client.get_put_call_ratio("total")).date == today


@pytest.mark.asyncio
async def test_get_put_call_ratio_rejects_stale_data(monkeypatch):
    client = CBOEClient()
    stale = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d")

    async def fetch(_ratio_type):
        return [_row(stale)]

    monkeypatch.setattr(client, "_fetch_csv", fetch)
    with pytest.raises(ValueError, match="Stale CBOE total data"):
        await client.get_put_call_ratio("total")
