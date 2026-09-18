from unittest.mock import MagicMock, patch
from integrations.brokers.kite import (
    exchange_request_token,
    fetch_holdings,
    get_login_url,
)


def test_get_login_url_delegates_to_kiteconnect():
    with patch("integrations.brokers.kite.KiteConnect") as MockKite:
        mock_instance = MagicMock()
        mock_instance.login_url.return_value = "https://kite.zerodha.com/connect/login?v=3&api_key=test_key"
        MockKite.return_value = mock_instance

        url = get_login_url()
        assert url == "https://kite.zerodha.com/connect/login?v=3&api_key=test_key"
        MockKite.assert_called_once()
        mock_instance.login_url.assert_called_once()


def test_exchange_request_token_returns_access_token():
    with patch("integrations.brokers.kite.KiteConnect") as MockKite:
        mock_instance = MagicMock()
        mock_instance.generate_session.return_value = {"access_token": "mock_access_token_xyz"}
        MockKite.return_value = mock_instance

        token = exchange_request_token("mock_request_token_123")
        assert token == "mock_access_token_xyz"
        mock_instance.generate_session.assert_called_once()


def test_fetch_holdings_returns_raw_kite_response():
    with patch("integrations.brokers.kite.KiteConnect") as MockKite:
        mock_instance = MagicMock()
        raw_holdings = [
            {
                "tradingsymbol": "INFY",
                "quantity": 10,
                "average_price": 1500.0,
                "last_price": 1600.0,
            }
        ]
        mock_instance.holdings.return_value = raw_holdings
        MockKite.return_value = mock_instance

        result = fetch_holdings("mock_token")
        assert result == raw_holdings
        mock_instance.set_access_token.assert_called_once_with("mock_token")
        mock_instance.holdings.assert_called_once()
