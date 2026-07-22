"""Unit tests for FakeDataSourceAdapter."""
import pytest

from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def adapter():
    return FakeDataSourceAdapter()


def test_fetch_interday_returns_dataframe(adapter):
    df = adapter.fetch_interday("AI.PA", period="max")
    assert not df.empty
    assert set(["date", "open", "high", "low", "close", "volume"]).issubset(df.columns)


def test_fetch_interday_row_count(adapter):
    df = adapter.fetch_interday("AI.PA")
    assert len(df) >= 5


def test_fetch_intraday_returns_dataframe(adapter):
    df = adapter.fetch_intraday("AI.PA", interval="15m", period="30d")
    assert not df.empty
    assert set(["datetime", "open", "high", "low", "close", "volume"]).issubset(df.columns)


def test_fetch_dividends_returns_dataframe(adapter):
    df = adapter.fetch_dividends("AI.PA")
    assert not df.empty
    assert set(["ex_date", "payment_date", "amount", "currency"]).issubset(df.columns)


def test_fetch_dividends_min_rows(adapter):
    df = adapter.fetch_dividends("AI.PA")
    assert len(df) >= 2


def test_no_network_access(adapter, monkeypatch):
    """FakeDataSourceAdapter must not make network calls."""
    import socket
    original_connect = socket.socket.connect
    called = []

    def mock_connect(self, address):
        called.append(address)
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", mock_connect)
    adapter.fetch_interday("AI.PA")
    adapter.fetch_intraday("AI.PA")
    adapter.fetch_dividends("AI.PA")
    assert len(called) == 0
