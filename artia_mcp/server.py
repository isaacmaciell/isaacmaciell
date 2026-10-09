"""Servidor MCP do Artia: ferramentas de projetos, atividades e apontamentos."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import operations as ops
from .client import ArtiaClient, ArtiaConfig, ArtiaError

MAX_PAGES = 100
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
def artia_list_projects(account_id: int | None = None) -> Any:
    """Lista os projetos de um grupo de trabalho (accountId)."""
    return _run(ops.LIST_PROJECTS, accountId=_account(account_id))


@mcp.tool()
def artia_get_project(project_id: str, account_id: int | None = None) -> Any:
    """Retorna os detalhes de um projeto."""
    return _run(ops.SHOW_PROJECT, id=str(project_id), accountId=_account(account_id))


# ----------------------------------------------------------------------- pastas
@mcp.tool()
def artia_list_folders(account_id: int | None = None, page: int | None = None) -> Any:
    """Lista as pastas do grupo de trabalho, com a pasta/projeto pai (`parent`).

    Sem `page`, percorre todas as páginas e devolve a lista completa.
    """
    account = _account(account_id)
    if page is not None:
        return _run(ops.LIST_FOLDERS, accountId=account, page=page)
    folders: list[Any] = []
    for number in range(1, MAX_PAGES + 1):
        batch = _run(ops.LIST_FOLDERS, accountId=account, page=number)
        if not batch:
            break
        folders.extend(batch)
    return folders


@mcp.tool()
def artia_update_folder(
    folder_id: str,
    name: str | None = None,
    estimated_start: str | None = None,
    estimated_end: str | None = None,
    actual_start: str | None = None,
    actual_end: str | None = None,
    estimated_effort_hours: float | None = None,
) -> Any:
    """Atualiza uma pasta. Só os campos informados são enviados (datas AAAA-MM-DD).

    O % completo e a situação da pasta são calculados pelo Artia a partir das
    atividades; a API não permite gravá-los de forma confiável.
    """
    return _run(
        ops.UPDATE_FOLDER,
        id=str(folder_id),
        name=name,
        estimatedStart=estimated_start,
        estimatedEnd=estimated_end,
        actualStart=actual_start,
        actualEnd=actual_end,
        estimatedEffort=estimated_effort_hours,
    )


# ------------------------------------------------------------------- atividades
@mcp.tool()
def artia_list_activities(folder_id: int, account_id: int | None = None) -> Any:
    """Lista as atividades que estão diretamente em uma pasta/projeto (folderId).

    Uma pasta sem atividades próprias (só subpastas) retorna lista vazia.
    """
    try:
        return _run(ops.LIST_ACTIVITIES, accountId=_account(account_id), folderId=folder_id)
    except ArtiaError as exc:
        if "não possui atividades" in str(exc):
            return []
        raise


@mcp.tool()
def artia_get_activity(
    activity_id: str, folder_id: int | None = None, account_id: int | None = None
) -> Any:
    """Retorna os detalhes de uma atividade (id interno, não o `uid` exibido na tela)."""
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
    actual_start: str | None = None,
    actual_end: str | None = None,
    estimated_effort_hours: float | None = None,
    completed_percent: float | None = None,
    responsible_id: int | None = None,
    activity_type_id: int | None = None,
    custom_status_id: int | None = None,
    category: str | None = None,
    priority: int | None = None,
) -> Any:
    """Cria uma atividade em uma pasta/projeto. Datas no formato AAAA-MM-DD.

    O responsável precisa ser um participante ATIVO do grupo de trabalho
    (veja artia_list_participants). activity_type_id e custom_status_id vêm de
    artia_list_activity_types e artia_list_custom_status.
    """
    return _run(
        ops.CREATE_ACTIVITY,
        accountId=_account(account_id),
        folderId=folder_id,
        title=title,
        description=description,
        estimatedStart=estimated_start,
        estimatedEnd=estimated_end,
        actualStart=actual_start,
        actualEnd=actual_end,
        estimatedEffort=estimated_effort_hours,
        completedPercent=completed_percent,
        responsibleId=responsible_id,
        folderTypeId=activity_type_id,
        customStatusId=custom_status_id,
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
    actual_start: str | None = None,
    actual_end: str | None = None,
    estimated_effort_hours: float | None = None,
    completed_percent: float | None = None,
    responsible_id: int | None = None,
    activity_type_id: int | None = None,
    category: str | None = None,
    priority: int | None = None,
) -> Any:
    """Atualiza campos de uma atividade. Só os campos informados são enviados.

    O Artia exige o título em toda atualização; se `title` não for informado,
    o título atual é lido e reenviado.
    """
    account = _account(account_id)
    if title is None:
        current = _run(ops.SHOW_ACTIVITY, id=str(activity_id), accountId=account, folderId=folder_id)
        title = current["title"]
    return _run(
        ops.UPDATE_ACTIVITY,
        id=str(activity_id),
        accountId=account,
        folderId=folder_id,
        title=title,
        description=description,
        estimatedStart=estimated_start,
        estimatedEnd=estimated_end,
        actualStart=actual_start,
        actualEnd=actual_end,
        estimatedEffort=estimated_effort_hours,
        completedPercent=completed_percent,
        responsibleId=responsible_id,
        folderTypeId=activity_type_id,
        categoryText=category,
        priority=priority,
    )


@mcp.tool()
def artia_change_activity_status(
    activity_id: str, folder_id: int, custom_status_id: int, account_id: int | None = None
) -> Any:
    """Altera o status de uma atividade (id de artia_list_custom_status)."""
    return _run(
        ops.CHANGE_ACTIVITY_STATUS,
        id=str(activity_id),
        accountId=_account(account_id),
        folderId=folder_id,
        customStatusId=custom_status_id,
    )


@mcp.tool()
def artia_delete_activities(
    folder_id: int,
    activity_ids: list[int],
    expected_titles: list[str],
    account_id: int | None = None,
) -> Any:
    """EXCLUI atividades de forma DEFINITIVA. Confirme com o usuário antes de chamar.

    Trava de segurança: `expected_titles` (um por id, na mesma ordem) precisa
    bater exatamente com o título atual de cada atividade; se algum divergir,
    nada é excluído.
    """
    if len(activity_ids) != len(expected_titles):
        raise ValueError("activity_ids e expected_titles precisam ter o mesmo tamanho.")
    account = _account(account_id)
    for activity_id, expected in zip(activity_ids, expected_titles):
        current = _run(ops.SHOW_ACTIVITY, id=str(activity_id), accountId=account, folderId=folder_id)
        if current["title"] != expected:
            raise ValueError(
                f"Atividade {activity_id} tem o título {current['title']!r}, "
                f"e não {expected!r}. Nada foi excluído."
            )
    return _run(ops.DESTROY_ACTIVITIES, ids=activity_ids, accountId=account)


@mcp.tool()
def artia_list_dependencies(folder_id: int, activity_id: int) -> Any:
    """Lista as dependências (predecessoras/sucessoras) de uma atividade (id interno).

    O schema marca activityId como opcional, mas o Artia responde "Activity not
    found" sem ele; por isso é obrigatório aqui. O caminho crítico do Artia é
    calculado a partir destas dependências e das datas.
    """
    return _run(ops.LIST_DEPENDENCIES, folderId=folder_id, activityId=activity_id)


@mcp.tool()
def artia_add_dependencies(
    folder_id: int,
    activity_id: int,
    predecessor_ids: list[int] | None = None,
    successor_ids: list[int] | None = None,
) -> Any:
    """Cria dependências para uma atividade (ids internos), no padrão fim-início do Artia."""
    return _run(
        ops.CREATE_DEPENDENCIES,
        folderId=folder_id,
        activityId=activity_id,
        predecessors=[{"activityId": i} for i in predecessor_ids] if predecessor_ids else None,
        successors=[{"activityId": i} for i in successor_ids] if successor_ids else None,
    )


def _participants(user_ids: list[int], role: str) -> list[dict[str, Any]]:
    if role not in ("PARTICIPANT", "INFORMED"):
        raise ValueError('role deve ser "PARTICIPANT" ou "INFORMED".')
    return [{"userId": uid, "role": role} for uid in user_ids]


@mcp.tool()
def artia_add_participants(activity_id: int, user_ids: list[int], role: str = "PARTICIPANT") -> Any:
    """Adiciona participantes (ou informados) a uma atividade. user_ids vêm de artia_list_participants."""
    return _run(ops.ADD_PARTICIPANTS, activityId=activity_id, participants=_participants(user_ids, role))


@mcp.tool()
def artia_remove_participants(
    activity_id: int, user_ids: list[int], role: str = "PARTICIPANT"
) -> Any:
    """Remove participantes de uma atividade (o responsável não é afetado)."""
    return _run(ops.REMOVE_PARTICIPANTS, activityId=activity_id, participants=_participants(user_ids, role))


# ------------------------------------------------------------------- consultas
@mcp.tool()
def artia_list_participants(account_id: int | None = None) -> Any:
    """Lista os participantes ativos do grupo de trabalho (candidatos a responsável)."""
    return _run(ops.LIST_PARTICIPANTS, accountId=_account(account_id))


@mcp.tool()
def artia_list_custom_status(
    object_type: str | None = None, account_id: int | None = None
) -> Any:
    """Lista os status personalizados. object_type: "Activity" ou "Project"."""
    return _run(
        ops.LIST_CUSTOM_STATUS, accounts=[_account(account_id)], statusObject=object_type
    )


@mcp.tool()
def artia_list_activity_types(object_type: str = "Activity") -> Any:
    """Lista tipos cadastrados. object_type: "Activity", "Project", "Folder" ou "Milestone"."""
    return _run(ops.LIST_FOLDER_TYPES, fetchAll=True, folderObject=object_type)


# ---------------------------------------------------------------- apontamentos
def parse_duration(value: str | int | float) -> float:
    """Converte o esforço em HORAS (como no formulário do Artia: "1,5" ou "01:30").

    Aceita 1.5, "1,5", "1:30", "01:30", "1h30", "2h" e "45min". Número simples
    é sempre interpretado como horas.
    """
    if isinstance(value, (int, float)):
        hours = float(value)
    else:
        text = value.strip().lower().replace(",", ".")
        if text.endswith("min"):
            hours = float(text[:-3]) / 60
        elif ":" in text or "h" in text:
            h, _, m = text.replace("h", ":").partition(":")
            hours = float(h or 0) + float(m or 0) / 60
        else:
            hours = float(text)
    if hours <= 0:
        raise ValueError("O esforço do apontamento deve ser maior que zero.")
    return round(hours, 4)


@mcp.tool()
def artia_list_time_entries(
    account_id: int | None = None,
    folder_id: int | None = None,
    activity_id: int | None = None,
    only_mine: bool | None = None,
) -> Any:
    """Lista apontamentos de horas, com filtros opcionais."""
    return _run(
        ops.LIST_TIME_ENTRIES,
        accountId=_account(account_id),
        folderId=folder_id,
        activityId=activity_id,
        onlyMine=only_mine,
    )


@mcp.tool()
def artia_create_time_entry(
    activity_id: int,
    duration: str,
    start_time: str,
    date_at: str | None = None,
    account_id: int | None = None,
    observation: str | None = None,
) -> Any:
    """Registra um apontamento de horas em uma atividade.

    duration: esforço em horas, como no formulário do Artia ("1,5", "01:30",
    "1h30", "45min"; número simples = horas). start_time: HH:MM (a API exige,
    embora a tela do Artia o trate como opcional). date_at: AAAA-MM-DD (padrão: hoje).
    ATENÇÃO: nenhum apontamento foi criado de verdade por esta ferramenta ainda;
    confira o primeiro lançamento na tela do Artia.
    """
    return _run(
        ops.CREATE_TIME_ENTRY,
        accountId=_account(account_id),
        activityId=activity_id,
        dateAt=date_at or date.today().isoformat(),
        startTime=start_time,
        duration=parse_duration(duration),
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
