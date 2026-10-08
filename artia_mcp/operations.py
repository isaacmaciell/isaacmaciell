"""Catálogo das operações GraphQL do Artia usadas pelas ferramentas.

Cada operação é descrita por uma ``OperationSpec`` (nome do campo raiz, tipos
dos argumentos e campos retornados). O documento GraphQL é montado em tempo de
execução apenas com os argumentos informados, para não enviar ``null`` em
campos opcionais (o que em mutations de atualização poderia apagar dados).

IMPORTANTE: nomes de operações, argumentos e campos seguem a documentação
pública do Artia, mas ainda NÃO foram conferidos contra o schema real. Depois de
rodar ``scripts/dump_schema.py``, execute ``scripts/validate_operations.py``:
ele aponta qualquer divergência e basta ajustar este arquivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AUTHENTICATE = """
mutation Authenticate($clientId: String!, $secret: String!) {
  authenticationByClient(clientId: $clientId, secret: $secret) {
    token
  }
}
"""

PROJECT_FIELDS = """
id
number
name
status
lastInformations
estimatedStart
estimatedEnd
actualStart
actualEnd
estimatedEffort
"""

ACTIVITY_FIELDS = """
id
uid
title
description
status
completedPercent
estimatedStart
estimatedEnd
actualStart
actualEnd
estimatedEffort
actualEffort
"""

TIME_ENTRY_FIELDS = """
id
dateAt
duration
startTime
endTime
observation
activityId
"""


@dataclass(frozen=True)
class OperationSpec:
    kind: str  # "query" | "mutation"
    root_field: str
    arg_types: dict[str, str]
    selection: str
    required: tuple[str, ...] = field(default=())

    def build(self, provided: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Monta (documento, variáveis) só com os argumentos não nulos."""
        missing = [name for name in self.required if provided.get(name) is None]
        if missing:
            raise ValueError(f"{self.root_field}: argumentos obrigatórios ausentes: {missing}")
        unknown = set(provided) - set(self.arg_types)
        if unknown:
            raise ValueError(f"{self.root_field}: argumentos desconhecidos: {sorted(unknown)}")
        variables = {k: v for k, v in provided.items() if v is not None}
        return self.document(variables.keys()), variables

    def document(self, arg_names) -> str:
        names = [n for n in self.arg_types if n in set(arg_names)]
        var_defs = ", ".join(f"${n}: {self.arg_types[n]}" for n in names)
        call_args = ", ".join(f"{n}: ${n}" for n in names)
        op_name = self.root_field[0].upper() + self.root_field[1:]
        header = f"{self.kind} {op_name}" + (f"({var_defs})" if var_defs else "")
        call = self.root_field + (f"({call_args})" if call_args else "")
        return f"{header} {{\n  {call} {{{self.selection}}}\n}}"


# ------------------------------------------------------------------ projetos
LIST_PROJECTS = OperationSpec(
    "query",
    "listingProjects",
    {"accountId": "Int!", "page": "Int", "status": "String"},
    PROJECT_FIELDS,
    required=("accountId",),
)

SHOW_PROJECT = OperationSpec(
    "query",
    "showProject",
    {"id": "String!", "accountId": "Int!"},
    PROJECT_FIELDS,
    required=("id", "accountId"),
)

# ---------------------------------------------------------------- atividades
LIST_ACTIVITIES = OperationSpec(
    "query",
    "listingActivities",
    {"accountId": "Int!", "folderId": "Int!", "page": "Int", "status": "String"},
    ACTIVITY_FIELDS,
    required=("accountId", "folderId"),
)

SHOW_ACTIVITY = OperationSpec(
    "query",
    "showActivity",
    {"id": "String!", "accountId": "Int!", "folderId": "Int!"},
    ACTIVITY_FIELDS,
    required=("id", "accountId", "folderId"),
)

_ACTIVITY_INPUT = {
    "title": "String",
    "description": "String",
    "estimatedStart": "String",
    "estimatedEnd": "String",
    "estimatedEffort": "Float",
    "responsibleId": "Int",
    "categoryText": "String",
    "priority": "Int",
}

CREATE_ACTIVITY = OperationSpec(
    "mutation",
    "createActivity",
    {"accountId": "Int!", "folderId": "Int!", **_ACTIVITY_INPUT, "title": "String!"},
    ACTIVITY_FIELDS,
    required=("accountId", "folderId", "title"),
)

UPDATE_ACTIVITY = OperationSpec(
    "mutation",
    "updateActivity",
    {"id": "String!", "accountId": "Int!", "folderId": "Int!", **_ACTIVITY_INPUT},
    ACTIVITY_FIELDS,
    required=("id", "accountId", "folderId"),
)

CHANGE_ACTIVITY_STATUS = OperationSpec(
    "mutation",
    "changeStatusActivity",
    {"id": "String!", "accountId": "Int!", "folderId": "Int!", "status": "Int!"},
    ACTIVITY_FIELDS,
    required=("id", "accountId", "folderId", "status"),
)

# --------------------------------------------------- apontamentos (time entries)
LIST_TIME_ENTRIES = OperationSpec(
    "query",
    "listingTimeEntries",
    {
        "accountId": "Int!",
        "activityId": "Int",
        "userId": "Int",
        "startDate": "String",
        "endDate": "String",
        "page": "Int",
    },
    TIME_ENTRY_FIELDS,
    required=("accountId",),
)

CREATE_TIME_ENTRY = OperationSpec(
    "mutation",
    "createTimeEntry",
    {
        "accountId": "Int!",
        "activityId": "Int!",
        "dateAt": "String!",
        "duration": "Int!",
        "startTime": "String",
        "endTime": "String",
        "observation": "String",
    },
    TIME_ENTRY_FIELDS,
    required=("accountId", "activityId", "dateAt", "duration"),
)

DELETE_TIME_ENTRY = OperationSpec(
    "mutation",
    "destroyTimeEntry",
    {"id": "String!", "accountId": "Int!"},
    "\nid\n",
    required=("id", "accountId"),
)

ALL_OPERATIONS: dict[str, OperationSpec] = {
    "LIST_PROJECTS": LIST_PROJECTS,
    "SHOW_PROJECT": SHOW_PROJECT,
    "LIST_ACTIVITIES": LIST_ACTIVITIES,
    "SHOW_ACTIVITY": SHOW_ACTIVITY,
    "CREATE_ACTIVITY": CREATE_ACTIVITY,
    "UPDATE_ACTIVITY": UPDATE_ACTIVITY,
    "CHANGE_ACTIVITY_STATUS": CHANGE_ACTIVITY_STATUS,
    "LIST_TIME_ENTRIES": LIST_TIME_ENTRIES,
    "CREATE_TIME_ENTRY": CREATE_TIME_ENTRY,
    "DELETE_TIME_ENTRY": DELETE_TIME_ENTRY,
}
