"""Servidor MCP do Artia: ferramentas de projetos, atividades e apontamentos."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import operations as ops
from .client import ArtiaClient, ArtiaConfig, ArtiaError

mcp = MCPServer("artia")
_client: ArtiaClient | None = None


def get_client() -> ArtiaClient:
    global _client
    if _client is None:
        _client = ArtiaClient(ArtiaConfig.from_env())
    return _client


def _run(spec: ops.OperationSpec, **args: Any) -> Any:
    document, variables = spec.build(args)
    data = get_client().execute(document, variables)
    return data.get(spec.root_field)


def _account(account_id: int | None) -> int:
    return get_client().resolve_account_id(account_id)


# ------------------------------------------------------------------ diagnóstico
@mcp.tool()
def artia_test_connection() -> dict[str, Any]:
    """Testa a autenticação no Artia e retorna o status da conexão."""
    try:
        get_client().authenticate(force=True)
        return {"ok": True, "message": "Autenticado com sucesso no Artia."}
    except ArtiaError as exc:
        return {"ok": False, "message": str(exc)}


@mcp.tool()
def artia_graphql(query: str, variables: dict[str, Any] | None = None) -> Any:
    """Executa uma query/mutation GraphQL arbitrária no Artia (uso avançado)."""
    return get_client().execute(query, variables or {})


# --------------------------------------------------------------------- projetos
@mcp.tool()
def artia_list_projects(
    account_id: int | None = None, page: int | None = None, status: str | None = None
) -> Any:
    """Lista os projetos de um grupo de trabalho (accountId)."""
    return _run(ops.LIST_PROJECTS, accountId=_account(account_id), page=page, status=status)


@mcp.tool()
def artia_get_project(project_id: str, account_id: int | None = None) -> Any:
    """Retorna os detalhes de um projeto."""
    return _run(ops.SHOW_PROJECT, id=str(project_id), accountId=_account(account_id))


# ------------------------------------------------------------------- atividades
@mcp.tool()
def artia_list_activities(
    folder_id: int,
    account_id: int | None = None,
    page: int | None = None,
    status: str | None = None,
) -> Any:
    """Lista as atividades de uma pasta/projeto (folderId) do Artia."""
    return _run(
        ops.LIST_ACTIVITIES,
        accountId=_account(account_id),
        folderId=folder_id,
        page=page,
        status=status,
    )


@mcp.tool()
def artia_get_activity(activity_id: str, folder_id: int, account_id: int | None = None) -> Any:
    """Retorna os detalhes de uma atividade."""
    return _run(
        ops.SHOW_ACTIVITY, id=str(activity_id), accountId=_account(account_id), folderId=folder_id
    )


@mcp.tool()
def artia_create_activity(
    folder_id: int,
    title: str,
    account_id: int | None = None,
    description: str | None = None,
    estimated_start: str | None = None,
    estimated_end: str | None = None,
    estimated_effort_hours: float | None = None,
    responsible_id: int | None = None,
    category: str | None = None,
    priority: int | None = None,
) -> Any:
    """Cria uma atividade em uma pasta/projeto. Datas no formato AAAA-MM-DD."""
    return _run(
        ops.CREATE_ACTIVITY,
        accountId=_account(account_id),
        folderId=folder_id,
        title=title,
        description=description,
        estimatedStart=estimated_start,
        estimatedEnd=estimated_end,
        estimatedEffort=estimated_effort_hours,
        responsibleId=responsible_id,
        categoryText=category,
        priority=priority,
    )


@mcp.tool()
def artia_update_activity(
    activity_id: str,
    folder_id: int,
    account_id: int | None = None,
    title: str | None = None,
    description: str | None = None,
    estimated_start: str | None = None,
    estimated_end: str | None = None,
    estimated_effort_hours: float | None = None,
    responsible_id: int | None = None,
    category: str | None = None,
    priority: int | None = None,
) -> Any:
    """Atualiza campos de uma atividade. Só os campos informados são enviados."""
    return _run(
        ops.UPDATE_ACTIVITY,
        id=str(activity_id),
        accountId=_account(account_id),
        folderId=folder_id,
        title=title,
        description=description,
        estimatedStart=estimated_start,
        estimatedEnd=estimated_end,
        estimatedEffort=estimated_effort_hours,
        responsibleId=responsible_id,
        categoryText=category,
        priority=priority,
    )


@mcp.tool()
def artia_change_activity_status(
    activity_id: str, folder_id: int, status: int, account_id: int | None = None
) -> Any:
    """Altera o status de uma atividade (código numérico de status do Artia)."""
    return _run(
        ops.CHANGE_ACTIVITY_STATUS,
        id=str(activity_id),
        accountId=_account(account_id),
        folderId=folder_id,
        status=status,
    )


# ---------------------------------------------------------------- apontamentos
def parse_duration(value: str | int) -> int:
    """Converte duração em minutos. Aceita 90, "90", "1:30" ou "1h30"."""
    if isinstance(value, int):
        minutes = value
    else:
        text = value.strip().lower().replace("min", "").replace("m", "")
        if ":" in text or "h" in text:
            hours, _, mins = text.replace("h", ":").partition(":")
            minutes = int(hours or 0) * 60 + int(mins or 0)
        else:
            minutes = int(text)
    if minutes <= 0:
        raise ValueError("A duração do apontamento deve ser maior que zero.")
    return minutes


@mcp.tool()
def artia_list_time_entries(
    account_id: int | None = None,
    activity_id: int | None = None,
    user_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int | None = None,
) -> Any:
    """Lista apontamentos de horas, com filtros opcionais (datas AAAA-MM-DD)."""
    return _run(
        ops.LIST_TIME_ENTRIES,
        accountId=_account(account_id),
        activityId=activity_id,
        userId=user_id,
        startDate=start_date,
        endDate=end_date,
        page=page,
    )


@mcp.tool()
def artia_create_time_entry(
    activity_id: int,
    duration: str,
    date_at: str | None = None,
    account_id: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    observation: str | None = None,
) -> Any:
    """Registra um apontamento de horas em uma atividade.

    duration: minutos ("90") ou horas ("1:30", "1h30"). date_at: AAAA-MM-DD
    (padrão: hoje). start_time/end_time: HH:MM, opcionais.
    """
    return _run(
        ops.CREATE_TIME_ENTRY,
        accountId=_account(account_id),
        activityId=activity_id,
        dateAt=date_at or date.today().isoformat(),
        duration=parse_duration(duration),
        startTime=start_time,
        endTime=end_time,
        observation=observation,
    )


@mcp.tool()
def artia_delete_time_entry(time_entry_id: str, account_id: int | None = None) -> Any:
    """Exclui um apontamento de horas."""
    return _run(ops.DELETE_TIME_ENTRY, id=str(time_entry_id), accountId=_account(account_id))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
