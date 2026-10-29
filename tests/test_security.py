import asyncio

import pytest
from mcp.server.auth.provider import AuthorizationParams, RegistrationError
from mcp.shared.auth import OAuthClientInformationFull

from garmin_mcp.garmin_client import GarminAuthError, _tokenstore_path
from garmin_mcp.oauth_provider import SingleUserOAuthProvider


@pytest.mark.parametrize("uid", ["..", ".", "a/b", "", "x" * 65])
def test_user_id_rejected(uid):
    with pytest.raises(GarminAuthError):
        _tokenstore_path(uid)


@pytest.mark.parametrize("uid", ["default", "user_42"])
def test_user_id_accepted(uid):
    assert _tokenstore_path(uid).name == uid


def _client(uri):
    return OAuthClientInformationFull(client_id="c", redirect_uris=[uri])


def test_redirect_uri_allowlist():
    p = SingleUserOAuthProvider()
    asyncio.run(p.register_client(_client("https://claude.ai/api/mcp/auth_callback")))
    with pytest.raises(RegistrationError):
        asyncio.run(p.register_client(_client("https://evil.example/cb")))


def test_pending_deleted_after_wrong_password(monkeypatch):
    monkeypatch.setenv("MCP_APP_PASSWORD", "right")
    p = SingleUserOAuthProvider()
    c = _client("https://claude.ai/cb")
    params = AuthorizationParams(
        state="s", scopes=[], code_challenge="x", redirect_uri=c.redirect_uris[0],
        redirect_uri_provided_explicitly=True,
    )
    url = asyncio.run(p.authorize(c, params))
    pid = url.split("=", 1)[1]
    assert p.complete_login(pid, "wrong") is None
    assert p.complete_login(pid, "right") is None
