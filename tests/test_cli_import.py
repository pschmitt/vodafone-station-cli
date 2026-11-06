"""Smoke tests for the installed aiovodafone API surface."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

import cli


class CliImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_uses_detected_mock_device(self) -> None:
        session = Mock()
        api = Mock()
        api.login = AsyncMock()

        with (
            patch.object(cli, "CookieJar") as cookie_jar,
            patch.object(cli, "ClientSession", return_value=session),
            patch.object(
                cli,
                "get_device_type",
                new=AsyncMock(return_value=("mock-device", "http://router")),
            ),
            patch.object(cli, "init_device_class", return_value=api) as init,
        ):
            result = await cli.connect("router", "user", "password", True)

        self.assertIs(result, api)
        cookie_jar.assert_called_once_with(unsafe=True)
        init.assert_called_once_with(
            "http://router",
            "mock-device",
            {"username": "user", "password": "password"},
            session,
        )
        api.login.assert_awaited_once_with(force_logout=True)


if __name__ == "__main__":
    unittest.main()
