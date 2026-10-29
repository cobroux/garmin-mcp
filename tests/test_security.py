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


def test_rest_refuses_mcp_user_id(monkeypatch):
    from types import SimpleNamespace

    from garmin_mcp import server

    monkeypatch.setenv("GARMIN_API_TOKEN", "t")
    req = lambda uid: SimpleNamespace(headers={"x-internal-token": "t"}, path_params={"user_id": uid})
    assert server._require_api_token(req("default")).status_code == 404
    assert server._require_api_token(req("other")) is None


def test_expired_pending_and_codes_purged():
    p = SingleUserOAuthProvider()
    c = _client("https://claude.ai/cb")
    p._pending["old"] = type("P", (), {"expires_at": 0})()
    p._auth_codes["old"] = type("A", (), {"expires_at": 0})()
    params = AuthorizationParams(
        state="s", scopes=[], code_challenge="x", redirect_uri=c.redirect_uris[0],
        redirect_uri_provided_explicitly=True,
    )
    asyncio.run(p.authorize(c, params))
    assert "old" not in p._pending and "old" not in p._auth_codes


def test_non_numeric_activity_id_rejected():
    from garmin_mcp import server

    with pytest.raises(ValueError):
        server.get_activity_details("1/../x")
