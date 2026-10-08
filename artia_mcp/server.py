"""Servidor MCP do Artia: ferramentas de projetos, atividades e apontamentos."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from graphql import GraphQLError, OperationDefinitionNode, parse
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import operations as ops
from .client import ArtiaClient, ArtiaConfig, ArtiaError

INSTRUCTIONS = """\
Servidor do Artia (projetos, atividades e apontamentos de horas).

Fluxo recomendado:
1. artia_test_connection para confirmar organização e grupo de trabalho.
2. artia_list_projects para achar o projeto; as atividades ficam em subpastas,
   então use o folderId da pasta da atividade (artia_list_activities no ID do
   projeto pode responder "Esse grupo de trabalho não possui atividades").
3. Antes de criar, alterar ou excluir, confirme com o usuário o que será gravado.

Particularidades confirmadas na API real:
- Apontamento: duration é enviada em horas decimais (0.25 = 15 min); a ferramenta
  aceita minutos ou "1:30" e converte. dateAt = AAAA-MM-DD; startTime = HH:MM.
- Apontamento exige status_id (situação da atividade); obtenha os IDs com
  artia_list_activity_statuses. Sem ele o Artia recusa o registro.
- artia_graphql executa leituras direto; mutations só rodam com confirm=true.
"""

READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)
DELETE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)

mcp = MCPServer("artia", instructions=INSTRUCTIONS)
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
@mcp.tool(annotations=READ)
def artia_test_connection() -> dict[str, Any]:
    """Testa a autenticação e confirma a organização e o grupo de trabalho configurados."""
    client = get_client()
    try:
        client.authenticate(force=True)
    except ArtiaError as exc:
        return {"ok": False, "message": str(exc)}
    result: dict[str, Any] = {"ok": True, "message": "Autenticado com sucesso no Artia."}
    try:
        # listingOrganizations é recusada para token de integração; o organizationId
        # dos tipos de pasta confirma a organização do token.
        types = client.execute("{ listingFolderTypes(fetchAll: true) { organizationId } }")
        org_ids = {t.get("organizationId") for t in types.get("listingFolderTypes") or []}
        configured = str(client.config.organization_id)
        result["organization"] = {
            "configured": configured,
            "confirmed": org_ids == {int(configured)} if configured.isdigit() else False,
        }
        if client.config.account_id is not None:
            folder = client.execute(
                "query($id: ID!) { showFolder(id: $id) { id name } }",
                {"id": str(client.config.account_id)},
            )
            result["account"] = folder.get("showFolder")
    except ArtiaError as exc:
        result["warning"] = f"Autenticado, mas não foi possível confirmar organização/grupo: {exc}"
    return result


def _mutation_fields(query: str) -> list[str]:
    """Campos raiz das mutations do documento (vazio se só houver queries)."""
    try:
        document = parse(query)
    except GraphQLError as exc:
        raise ValueError(f"GraphQL inválido: {exc.message}") from exc
    return [
        selection.name.value
        for definition in document.definitions
        if isinstance(definition, OperationDefinitionNode) and definition.operation.value == "mutation"
        for selection in definition.selection_set.selections
        if hasattr(selection, "name")
    ]


@mcp.tool(annotations=DELETE)
def artia_graphql(
    query: str, variables: dict[str, Any] | None = None, confirm: bool = False
) -> Any:
    """Executa uma query/mutation GraphQL arbitrária no Artia (uso avançado).

    Queries rodam direto. Mutations só rodam com confirm=true; sem isso a
    ferramenta devolve as operações que seriam executadas, para confirmar com
    o usuário antes (atenção a destroy*, que apaga dados em definitivo).
    """
    mutations = _mutation_fields(query)
    if mutations and not confirm:
        return {
            "executed": False,
            "requires_confirmation": True,
            "mutations": mutations,
            "destructive": [m for m in mutations if m.startswith("destroy")],
            "variables": variables or {},
            "message": "Confirme com o usuário e chame de novo com confirm=true.",
        }
    return get_client().execute(query, variables or {})


# --------------------------------------------------------------------- projetos
@mcp.tool(annotations=READ)
def artia_list_projects(account_id: int | None = None) -> Any:
    """Lista os projetos de um grupo de trabalho (accountId)."""
    return _run(ops.LIST_PROJECTS, accountId=_account(account_id))


@mcp.tool(annotations=READ)
def artia_get_project(project_id: str, account_id: int | None = None) -> Any:
    """Retorna os detalhes de um projeto."""
    return _run(ops.SHOW_PROJECT, id=str(project_id), accountId=_account(account_id))


# ------------------------------------------------------------------- atividades
@mcp.tool(annotations=READ)
def artia_list_activities(folder_id: int, account_id: int | None = None) -> Any:
    """Lista as atividades de uma pasta/projeto (folderId) do Artia."""
    return _run(ops.LIST_ACTIVITIES, accountId=_account(account_id), folderId=folder_id)


@mcp.tool(annotations=READ)
def artia_get_activity(activity_id: str, folder_id: int, account_id: int | None = None) -> Any:
    """Retorna os detalhes de uma atividade."""
    return _run(
        ops.SHOW_ACTIVITY, id=str(activity_id), accountId=_account(account_id), folderId=folder_id
    )


@mcp.tool(annotations=WRITE)
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


@mcp.tool(annotations=WRITE)
def artia_update_activity(
    activity_id: str,
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
    """Atualiza campos de uma atividade. Só os campos informados são enviados.

    O Artia exige o título em toda atualização (repita o atual se não mudar).
    """
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


@mcp.tool(annotations=WRITE)
def artia_change_activity_status(
    activity_id: str,
    folder_id: int,
    custom_status_id: int | None = None,
    status: bool | None = None,
    account_id: int | None = None,
) -> Any:
    """Altera o status de uma atividade.

    custom_status_id: ID do status personalizado da organização.
    status: status booleano da atividade (campo ``status`` do Artia).
    """
    if custom_status_id is None and status is None:
        raise ValueError("Informe custom_status_id e/ou status.")
    return _run(
        ops.CHANGE_ACTIVITY_STATUS,
        id=str(activity_id),
        accountId=_account(account_id),
        folderId=folder_id,
        customStatusId=custom_status_id,
        status=status,
    )


@mcp.tool(annotations=READ)
def artia_list_activity_statuses(
    account_id: int | None = None, include_inactive: bool = False
) -> Any:
    """Lista as situações de atividade do grupo de trabalho, em ordem de exibição.

    Use o ``id`` como ``status_id`` em artia_create_time_entry ou como
    ``custom_status_id`` em artia_change_activity_status.
    """
    statuses = _run(
        ops.LIST_CUSTOM_STATUSES,
        accounts=[_account(account_id)],
        statusObject="Activity",
        inactive=None if include_inactive else False,
    ) or []
    return sorted(statuses, key=lambda s: s.get("position") or 0)


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


@mcp.tool(annotations=READ)
def artia_list_time_entries(
    account_id: int | None = None,
    folder_id: int | None = None,
    activity_id: int | None = None,
    only_mine: bool | None = None,
) -> Any:
    """Lista apontamentos de horas, com filtros opcionais por pasta, atividade ou só os meus."""
    return _run(
        ops.LIST_TIME_ENTRIES,
        accountId=_account(account_id),
        folderId=folder_id,
        activityId=activity_id,
        onlyMine=only_mine,
    )


@mcp.tool(annotations=WRITE)
def artia_create_time_entry(
    activity_id: int,
    duration: str,
    start_time: str,
    status_id: int,
    date_at: str | None = None,
    account_id: int | None = None,
    observation: str | None = None,
) -> Any:
    """Registra um apontamento de horas em uma atividade.

    duration: minutos ("90") ou horas ("1:30", "1h30"); é enviada ao Artia em
    horas decimais. start_time: HH:MM (obrigatório no Artia). date_at: AAAA-MM-DD
    (padrão: hoje). status_id: situação da atividade registrada no apontamento
    (ID de status com statusObject "Activity", ex.: "Não Iniciada", "Em Andamento");
    o Artia recusa o apontamento sem ela.
    """
    return _run(
        ops.CREATE_TIME_ENTRY,
        accountId=_account(account_id),
        activityId=activity_id,
        dateAt=date_at or date.today().isoformat(),
        duration=round(parse_duration(duration) / 60, 4),
        startTime=start_time,
        timeEntryStatusId=status_id,
        observation=observation,
    )


@mcp.tool(annotations=DELETE)
def artia_delete_time_entry(time_entry_id: str, account_id: int | None = None) -> Any:
    """Exclui um apontamento de horas."""
    return _run(ops.DELETE_TIME_ENTRY, id=str(time_entry_id), accountId=_account(account_id))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
