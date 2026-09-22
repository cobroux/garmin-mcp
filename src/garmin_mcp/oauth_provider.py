"""Minimal single-user OAuth 2.1 authorization server for the hosted deployment.

This is not a general-purpose auth server: there is exactly one accepted
subject ("owner"), gated by a shared secret (MCP_APP_PASSWORD) entered once
per client in the /login page served alongside the MCP endpoint. Dynamic
client registration is enabled so any MCP client (claude.ai included) can
register itself. All state lives in memory, so a server restart requires
reconnecting the client.
"""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    OAuthToken,
    RefreshToken,
    construct_redirect_uri,
)

ACCESS_TOKEN_TTL_SECONDS = 3600
PENDING_LOGIN_TTL_SECONDS = 300
AUTH_CODE_TTL_SECONDS = 300
OWNER_SUBJECT = "owner"


@dataclass
class _PendingAuthorization:
    client_id: str
    params: AuthorizationParams
    expires_at: float


class SingleUserOAuthProvider(OAuthAuthorizationServerProvider):
    """OAuth provider for a server with exactly one user: whoever knows MCP_APP_PASSWORD."""

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending: dict[str, _PendingAuthorization] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}

    # -- dynamic client registration --

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    # -- authorization: hand off to our own /login page instead of a 3rd party --

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        pending_id = secrets.token_urlsafe(24)
        self._pending[pending_id] = _PendingAuthorization(
            client_id=client.client_id,
            params=params,
            expires_at=time.time() + PENDING_LOGIN_TTL_SECONDS,
        )
        return f"/login?pending={pending_id}"

    def complete_login(self, pending_id: str, password: str) -> str | None:
        """Called by the /login route after the password form is submitted.

        Returns the URL to redirect the browser to on success, or None if the
        pending request is unknown/expired or the password is wrong.
        """
        pending = self._pending.get(pending_id)
        if pending is None or pending.expires_at < time.time():
            self._pending.pop(pending_id, None)
            return None
        expected = os.environ.get("MCP_APP_PASSWORD", "")
        if not expected or not secrets.compare_digest(password, expected):
            return None
        del self._pending[pending_id]

        params = pending.params
        code = secrets.token_urlsafe(32)
        self._auth_codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + AUTH_CODE_TTL_SECONDS,
            client_id=pending.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
            subject=OWNER_SUBJECT,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._auth_codes.get(authorization_code)
        if code is None or code.client_id != client.client_id or code.expires_at < time.time():
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._auth_codes.pop(authorization_code.code, None)
        return self._issue_tokens(client.client_id, authorization_code.scopes, authorization_code.resource)

    # -- refresh tokens --

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        token = self._refresh_tokens.get(refresh_token)
        if token is None or token.client_id != client.client_id:
            return None
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._refresh_tokens.pop(refresh_token.token, None)
        return self._issue_tokens(client.client_id, scopes or refresh_token.scopes, refresh_token.resource)

    # -- access tokens --

    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self._access_tokens.get(token)
        if access is None:
            return None
        if access.expires_at is not None and access.expires_at < time.time():
            del self._access_tokens[token]
            return None
        return access

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._access_tokens.pop(token.token, None)
        else:
            self._refresh_tokens.pop(token.token, None)

    def _issue_tokens(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + ACCESS_TOKEN_TTL_SECONDS
        self._access_tokens[access_token] = AccessToken(
            token=access_token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=resource,
            subject=OWNER_SUBJECT,
        )
        self._refresh_tokens[refresh_token] = RefreshToken(
            token=refresh_token,
            client_id=client_id,
            scopes=scopes,
            resource=resource,
            subject=OWNER_SUBJECT,
        )
        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(scopes) if scopes else None,
        )
