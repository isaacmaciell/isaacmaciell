"""Cliente HTTP da API GraphQL do Artia.

Responsável por autenticar (mutation ``authenticationByClient``), manter o token
em cache, renovar quando expirar e executar queries/mutations com os cabeçalhos
exigidos pela API (``Authorization`` e ``OrganizationId``).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from graphql import get_introspection_query

from . import operations

DEFAULT_API_URL = "https://app.artia.com/graphql"
# A API não informa a validade do token; renovamos de forma conservadora.
TOKEN_TTL_SECONDS = 50 * 60


class ArtiaError(RuntimeError):
    """Erro retornado pela API do Artia (HTTP ou GraphQL)."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass
class ArtiaConfig:
    client_id: str
    client_secret: str
    organization_id: str
    account_id: int | None = None
    api_url: str = DEFAULT_API_URL
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "ArtiaConfig":
        missing = [
            name
            for name in ("ARTIA_CLIENT_ID", "ARTIA_CLIENT_SECRET", "ARTIA_ORGANIZATION_ID")
            if not os.environ.get(name)
        ]
        if missing:
            raise ArtiaError(f"Variáveis de ambiente ausentes: {', '.join(missing)}")
        account_id = os.environ.get("ARTIA_ACCOUNT_ID")
        return cls(
            client_id=os.environ["ARTIA_CLIENT_ID"],
            client_secret=os.environ["ARTIA_CLIENT_SECRET"],
            organization_id=os.environ["ARTIA_ORGANIZATION_ID"],
            account_id=int(account_id) if account_id else None,
            api_url=os.environ.get("ARTIA_API_URL") or DEFAULT_API_URL,
        )


class ArtiaClient:
    def __init__(self, config: ArtiaConfig, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._http = httpx.Client(timeout=config.timeout, transport=transport)
        self._token: str | None = None
        self._token_expires_at = 0.0

    # ------------------------------------------------------------------ auth
    def authenticate(self, force: bool = False) -> str:
        if not force and self._token and time.monotonic() < self._token_expires_at:
            return self._token
        data = self._post(
            operations.AUTHENTICATE,
            {"clientId": self.config.client_id, "secret": self.config.client_secret},
            auth=False,
        )
        token = (data.get("authenticationByClient") or {}).get("token")
        if not token:
            raise ArtiaError("Autenticação falhou: a API não retornou token.")
        self._token = token
        self._token_expires_at = time.monotonic() + TOKEN_TTL_SECONDS
        return token

    # --------------------------------------------------------------- execute
    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa uma operação autenticada; renova o token uma vez se expirado."""
        self.authenticate()
        try:
            return self._post(query, variables or {}, auth=True)
        except ArtiaError as exc:
            if not _is_auth_error(exc):
                raise
            self.authenticate(force=True)
            return self._post(query, variables or {}, auth=True)

    def introspect(self) -> dict[str, Any]:
        return self.execute(get_introspection_query(descriptions=True))

    def resolve_account_id(self, account_id: int | None) -> int:
        resolved = account_id if account_id is not None else self.config.account_id
        if resolved is None:
            raise ArtiaError(
                "Informe account_id (grupo de trabalho) ou defina ARTIA_ACCOUNT_ID."
            )
        return resolved

    def close(self) -> None:
        self._http.close()

    # -------------------------------------------------------------- internal
    def _post(self, query: str, variables: dict[str, Any], auth: bool) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "OrganizationId": str(self.config.organization_id),
        }
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = self._http.post(
                self.config.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise ArtiaError(f"Falha de rede ao chamar o Artia: {exc}") from exc

        if response.status_code == 401:
            raise ArtiaError("Não autorizado (HTTP 401).", [{"message": "unauthorized"}])
        if response.status_code >= 400:
            raise ArtiaError(f"HTTP {response.status_code}: {response.text[:500]}")

        payload = response.json()
        if payload.get("errors"):
            messages = "; ".join(e.get("message", str(e)) for e in payload["errors"])
            raise ArtiaError(f"Erro GraphQL: {messages}", payload["errors"])
        return payload.get("data") or {}


def _is_auth_error(exc: ArtiaError) -> bool:
    text = " ".join([str(exc)] + [str(e.get("message", "")) for e in exc.errors]).lower()
    return any(k in text for k in ("unauthorized", "401", "token", "autoriz", "expir"))
