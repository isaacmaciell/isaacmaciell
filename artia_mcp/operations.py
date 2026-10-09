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
accountId
name
description
folderTypeName
status
customStatus { id statusName }
estimatedStart
estimatedEnd
actualStart
actualEnd
estimatedEffort
completedPercent
"""

FOLDER_FIELDS = """
id
accountId
name
parent { id name }
status
estimatedStart
estimatedEnd
actualStart
actualEnd
estimatedEffort
completedPercent
"""

ACTIVITY_FIELDS = """
id
uid
title
description
folderId
folderTypeName
status
customStatus { id statusName }
completedPercent
estimatedStart
estimatedEnd
actualStart
actualEnd
estimatedEffort
actualEffort
isCriticalPath
responsible { id name }
participants { id name role }
"""

TIME_ENTRY_FIELDS = """
id
folderId
activityId
userId
dateAt
startTime
endTime
duration
observation
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
    "query", "listingProjects", {"accountId": "Int!"}, PROJECT_FIELDS, required=("accountId",)
)

SHOW_PROJECT = OperationSpec(
    "query",
    "showProject",
    {"id": "ID!", "accountId": "Int"},
    PROJECT_FIELDS,
    required=("id",),
)

# -------------------------------------------------------------------- pastas
LIST_FOLDERS = OperationSpec(
    "query",
    "listingFolders",
    {"accountId": "Int!", "page": "Int"},
    FOLDER_FIELDS,
    required=("accountId",),
)

UPDATE_FOLDER = OperationSpec(
    "mutation",
    "updateFolder",
    {
        "id": "ID!",
        "name": "String",
        "estimatedStart": "DateTime",
        "estimatedEnd": "DateTime",
        "actualStart": "DateTime",
        "actualEnd": "DateTime",
        "estimatedEffort": "Float",
        "completedPercent": "Float",
    },
    FOLDER_FIELDS,
    required=("id",),
)

# ---------------------------------------------------------------- atividades
LIST_ACTIVITIES = OperationSpec(
    "query",
    "listingActivities",
    {"accountId": "Int", "folderId": "Int!"},
    ACTIVITY_FIELDS,
    required=("folderId",),
)

SHOW_ACTIVITY = OperationSpec(
    "query",
    "showActivity",
    {"id": "ID!", "accountId": "Int", "folderId": "Int"},
    ACTIVITY_FIELDS,
    required=("id",),
)

_ACTIVITY_INPUT = {
    "description": "String",
    "estimatedStart": "DateTime",
    "estimatedEnd": "DateTime",
    "actualStart": "DateTime",
    "actualEnd": "DateTime",
    "estimatedEffort": "Float",
    "completedPercent": "Float",
    "responsibleId": "Int",
    "categoryText": "String",
    "priority": "Int",
    "folderTypeId": "Int",
    "customStatusId": "Int",
}

CREATE_ACTIVITY = OperationSpec(
    "mutation",
    "createActivity",
    {"accountId": "Int", "folderId": "Int!", "title": "String!", **_ACTIVITY_INPUT},
    ACTIVITY_FIELDS,
    required=("folderId", "title"),
)

# O schema exige "title" também na atualização.
UPDATE_ACTIVITY = OperationSpec(
    "mutation",
    "updateActivity",
    {"id": "ID!", "title": "String!", "accountId": "Int", "folderId": "Int", **_ACTIVITY_INPUT},
    ACTIVITY_FIELDS,
    required=("id", "title"),
)

CHANGE_ACTIVITY_STATUS = OperationSpec(
    "mutation",
    "changeCustomStatusActivity",
    {"id": "ID!", "accountId": "Int", "folderId": "Int!", "customStatusId": "Int", "status": "Boolean"},
    ACTIVITY_FIELDS,
    required=("id", "folderId"),
)

DESTROY_ACTIVITIES = OperationSpec(
    "mutation",
    "destroyActivities",
    {"ids": "[Int!]!", "accountId": "Int"},
    "message",
    required=("ids",),
)

LIST_DEPENDENCIES = OperationSpec(
    "query",
    "listingActivityDependencies",
    {"folderId": "Int!", "activityId": "Int"},
    "id\npredecessorId\nsuccessorId\nlinkType\nvariation",
    required=("folderId",),
)

CREATE_DEPENDENCIES = OperationSpec(
    "mutation",
    "createActivityDependencies",
    {
        "folderId": "Int!",
        "activityId": "Int!",
        "predecessors": "[ActivityDependencyRelationInput!]",
        "successors": "[ActivityDependencyRelationInput!]",
    },
    "__typename",
    required=("folderId", "activityId"),
)

ADD_PARTICIPANTS = OperationSpec(
    "mutation",
    "addActivityParticipants",
    {"activityId": "Int!", "participants": "[ActivityParticipantInput!]!"},
    "id\nparticipants { id name role }",
    required=("activityId", "participants"),
)

REMOVE_PARTICIPANTS = OperationSpec(
    "mutation",
    "removeActivityParticipants",
    {"activityId": "Int!", "participants": "[ActivityParticipantInput!]!"},
    "id\nparticipants { id name role }",
    required=("activityId", "participants"),
)

# ----------------------------------------------------------------- consultas
LIST_PARTICIPANTS = OperationSpec(
    "query",
    "listingAccountParticipants",
    {"accountId": "Int!"},
    "id\nuserId\nname\nemail\nstate",
    required=("accountId",),
)

LIST_CUSTOM_STATUS = OperationSpec(
    "query",
    "listingCustomStatus",
    {"accounts": "[Int!]", "inactive": "Boolean", "statusObject": "String"},
    "id\nstatusName\nstatusObject\ninactive",
)

LIST_FOLDER_TYPES = OperationSpec(
    "query",
    "listingFolderTypes",
    {"fetchAll": "Boolean", "folderObject": "String", "inactive": "Boolean", "name": "String"},
    "id\nname\nfolderObject\ninactive",
)

# --------------------------------------------------- apontamentos (time entries)
LIST_TIME_ENTRIES = OperationSpec(
    "query",
    "listingTimeEntries",
    {"accountId": "Int!", "folderId": "Int", "activityId": "Int", "onlyMine": "Boolean"},
    TIME_ENTRY_FIELDS,
    required=("accountId",),
)

CREATE_TIME_ENTRY = OperationSpec(
    "mutation",
    "createTimeEntry",
    {
        "accountId": "Int!",
        "activityId": "Int!",
        "dateAt": "DateTime!",
        "startTime": "HoursTime!",
        "duration": "Float!",
        "observation": "String",
    },
    TIME_ENTRY_FIELDS,
    required=("accountId", "activityId", "dateAt", "startTime", "duration"),
)

DELETE_TIME_ENTRY = OperationSpec(
    "mutation",
    "destroyTimeEntry",
    {"id": "ID!", "accountId": "Int!"},
    "\nid\n",
    required=("id", "accountId"),
)

ALL_OPERATIONS: dict[str, OperationSpec] = {
    "LIST_PROJECTS": LIST_PROJECTS,
    "SHOW_PROJECT": SHOW_PROJECT,
    "LIST_FOLDERS": LIST_FOLDERS,
    "UPDATE_FOLDER": UPDATE_FOLDER,
    "LIST_ACTIVITIES": LIST_ACTIVITIES,
    "SHOW_ACTIVITY": SHOW_ACTIVITY,
    "CREATE_ACTIVITY": CREATE_ACTIVITY,
    "UPDATE_ACTIVITY": UPDATE_ACTIVITY,
    "CHANGE_ACTIVITY_STATUS": CHANGE_ACTIVITY_STATUS,
    "DESTROY_ACTIVITIES": DESTROY_ACTIVITIES,
    "LIST_DEPENDENCIES": LIST_DEPENDENCIES,
    "CREATE_DEPENDENCIES": CREATE_DEPENDENCIES,
    "ADD_PARTICIPANTS": ADD_PARTICIPANTS,
    "REMOVE_PARTICIPANTS": REMOVE_PARTICIPANTS,
    "LIST_PARTICIPANTS": LIST_PARTICIPANTS,
    "LIST_CUSTOM_STATUS": LIST_CUSTOM_STATUS,
    "LIST_FOLDER_TYPES": LIST_FOLDER_TYPES,
    "LIST_TIME_ENTRIES": LIST_TIME_ENTRIES,
    "CREATE_TIME_ENTRY": CREATE_TIME_ENTRY,
    "DELETE_TIME_ENTRY": DELETE_TIME_ENTRY,
}
