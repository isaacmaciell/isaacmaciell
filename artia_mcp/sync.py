"""Sincroniza o cronograma de uma planilha Gantt (exportação do Artia) com o Artia.

Fluxo: ler a planilha (``load_sheet``) -> ler o estado atual do Artia
(``fetch_state``) -> calcular o plano (``build_plan``) -> aplicar (``apply_plan``).
O plano é só dados; nada é gravado até ``apply_plan`` ser chamado.

Regras de correspondência
- Atividade da planilha ``A97`` corresponde ao ``uid`` 97 do Artia; se o uid não
  existir, usa-se atividade de mesmo título na mesma pasta (evita duplicar).
- Pasta ``F6663644`` da planilha corresponde ao id interno 6663644.
- Atividade pertence à pasta da última linha ``F...`` anterior na planilha.
- ``Recursos``: o primeiro nome é o responsável, os demais são participantes.

Campos calculados pelo Artia (% e situação de pastas, caminho crítico) são
apenas informados, nunca gravados.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Situação da planilha -> nome do status personalizado de atividade no Artia.
STATUS_BY_SITUACAO = {"Encerrado": "Encerrado", "Em Andamento": "Em Andamento", "Não Iniciada": "Não Iniciada"}
TYPE_ALIASES = {"testes": "teste"}


# ----------------------------------------------------------------- planilha
@dataclass
class SheetRow:
    id: str
    title: str
    kind: str  # "folder" | "activity"
    est_start: str | None
    est_end: str | None
    act_start: str | None
    act_end: str | None
    pct: float | None
    situacao: str
    resources: list[str]
    tipo: str
    change: str
    folder_id: int | None = None  # só atividades: pasta pai
    critical: str = ""

    @property
    def number(self) -> int:
        return int(self.id[1:])


def _date(text: Any) -> str | None:
    if text in (None, ""):
        return None
    if isinstance(text, datetime):
        return text.strftime("%Y-%m-%d")
    return datetime.strptime(str(text).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")


def _pct(text: Any) -> float | None:
    if text in (None, ""):
        return None
    return float(str(text).replace("%", "").replace(",", ".").strip())


def _read_rows(path: Path, sheet: str | None) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))
    import openpyxl  # extra opcional: pip install -e ".[sync]"

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c or "").replace("﻿", "").strip() for c in rows[0]]
    return [dict(zip(header, r)) for r in rows[1:]]


def load_sheet(path: str | Path, sheet: str | None = None) -> list[SheetRow]:
    result: list[SheetRow] = []
    current_folder: int | None = None
    for raw in _read_rows(Path(path), sheet):
        row = {str(k).replace("﻿", "").strip(): v for k, v in raw.items()}
        rid = str(row.get("ID") or "").strip()
        if not rid:
            continue
        kind = "folder" if rid.startswith("F") else "activity"
        if kind == "folder":
            current_folder = int(rid[1:])
        resources = [r.strip() for r in str(row.get("Recursos") or "").split(";") if r.strip()]
        result.append(
            SheetRow(
                id=rid,
                title=str(row.get("Atividade") or "").strip(),
                kind=kind,
                est_start=_date(row.get("Início Estimado")),
                est_end=_date(row.get("Término Estimado")),
                act_start=_date(row.get("Início real")),
                act_end=_date(row.get("Término real")),
                pct=_pct(row.get("% Completo")),
                situacao=str(row.get("Situação") or "").strip(),
                resources=resources,
                tipo=str(row.get("Tipo de Atividade") or "").strip(),
                change=str(row.get("Status da Alteração") or "").strip(),
                folder_id=current_folder if kind == "activity" else None,
                critical=str(row.get("Caminho Crítico") or "").strip(),
            )
        )
    return result


# ------------------------------------------------------------- estado do Artia
@dataclass
class ArtiaState:
    folders: dict[int, dict[str, Any]] = field(default_factory=dict)
    activities: dict[int, dict[str, Any]] = field(default_factory=dict)  # por uid
    users: dict[str, int] = field(default_factory=dict)  # nome -> userId (qualquer usuário visto)
    active_users: dict[str, int] = field(default_factory=dict)  # só participantes ativos do grupo
    status_ids: dict[str, int] = field(default_factory=dict)  # nome -> id
    type_ids: dict[str, int] = field(default_factory=dict)  # nome (minúsculo) -> id
    projects: set[int] = field(default_factory=set)


def fetch_state(tools: Any, folder_ids: set[int]) -> ArtiaState:
    """Lê do Artia pastas, atividades, usuários, status e tipos.

    ``tools`` é o módulo ``artia_mcp.server`` (ou um objeto com as mesmas funções).
    """
    state = ArtiaState()
    state.projects = {int(p["id"]) for p in tools.artia_list_projects()}
    for project in tools.artia_list_projects():
        state.folders[int(project["id"])] = project
    for folder in tools.artia_list_folders():
        state.folders[int(folder["id"])] = folder
    for p in tools.artia_list_participants():
        state.users[p["name"]] = int(p["userId"])
        state.active_users[p["name"]] = int(p["userId"])
    for st in tools.artia_list_custom_status("Activity"):
        state.status_ids[st["statusName"]] = int(st["id"])
    for tp in tools.artia_list_activity_types("Activity"):
        if not tp["inactive"]:
            state.type_ids[tp["name"].strip().lower()] = int(tp["id"])
    for fid in sorted(folder_ids):
        for act in tools.artia_list_activities(fid):
            act["_folder_id"] = fid
            state.activities[int(act["uid"])] = act
            for person in [act.get("responsible"), *(act.get("participants") or [])]:
                if person and person.get("name") and person.get("id"):
                    state.users.setdefault(person["name"], int(person["id"]))
    return state


# --------------------------------------------------------------------- plano
@dataclass
class Action:
    kind: str  # CREATE | UPDATE | FOLDER | DELETE | INFO
    ref: str
    title: str
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)  # campo -> (atual, novo)
    payload: dict[str, Any] = field(default_factory=dict)
    note: str = ""


def _close(a: float | None, b: float | None) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 0.01)


def build_plan(
    rows: list[SheetRow], state: ArtiaState, fallback_responsible: int | None = None
) -> list[Action]:
    plan: list[Action] = []
    seen_uids: set[int] = set()
    sheet_folders = {int(r.id[1:]) for r in rows if r.kind == "folder"}
    missing_users: dict[str, list[str]] = {}
    pct_diffs: list[str] = []
    folder_names = {r.id[1:]: r.title for r in rows if r.kind == "folder"}

    for row in rows:
        if row.kind == "folder":
            folder = state.folders.get(int(row.id[1:]))
            if not folder:
                plan.append(Action("INFO", row.id, row.title, note="pasta não existe no Artia (criação de pastas não suportada)"))
                continue
            changes = {}
            for name, key, new in (
                ("estimatedStart", "estimatedStart", row.est_start),
                ("estimatedEnd", "estimatedEnd", row.est_end),
            ):
                # datas reais de pastas são calculadas pelo Artia: não sincronizar
                if new is not None and folder.get(key) != new:
                    changes[name] = (folder.get(key), new)
            if changes:
                plan.append(Action("FOLDER", row.id, row.title, changes, {"folder_id": row.id[1:], **{k: v[1] for k, v in changes.items()}}))
            if row.pct is not None and not _close(folder.get("completedPercent"), row.pct):
                pct_diffs.append(f"{row.id} {folder.get('completedPercent')} (planilha {row.pct})")
            continue

        uid = row.number
        existing = state.activities.get(uid)
        if existing is None:  # tenta casar por título na mesma pasta
            existing = next(
                (a for a in state.activities.values() if a["_folder_id"] == row.folder_id and a["title"] == row.title and a["uid"] not in seen_uids),
                None,
            )
        removed = "REMOVIDA" in row.change.upper()

        if existing is None:
            if removed:
                continue
            payload: dict[str, Any] = {
                "folder_id": row.folder_id,
                "title": row.title,
                "estimated_start": row.est_start,
                "estimated_end": row.est_end,
                "actual_start": row.act_start,
                "actual_end": row.act_end,
                "completed_percent": row.pct,
                "activity_type_id": state.type_ids.get(TYPE_ALIASES.get(row.tipo.lower(), row.tipo.lower())),
                "custom_status_id": state.status_ids.get(STATUS_BY_SITUACAO.get(row.situacao, "")),
            }
            note = ""
            if row.resources:
                uid_resp = state.active_users.get(row.resources[0])
                if uid_resp is None:
                    uid_resp = fallback_responsible
                    missing_users.setdefault(row.resources[0], []).append(row.id)
                    note = "responsável provisório" if fallback_responsible else "sem responsável"
                payload["responsible_id"] = uid_resp
            folder_label = folder_names.get(str(row.folder_id), row.folder_id)
            note = "; ".join(x for x in (f"pasta inferida pela posição na planilha: {folder_label}", note) if x)
            plan.append(Action("CREATE", row.id, row.title, payload=payload, note=note))
            continue

        seen_uids.add(int(existing["uid"]))
        if removed:
            plan.append(Action("DELETE", row.id, existing["title"], payload={"activity_id": int(existing["id"]), "folder_id": existing["_folder_id"]}, note="marcada como removida na planilha"))
            continue

        changes: dict[str, tuple[Any, Any]] = {}
        note_parts: list[str] = []
        for label, cur, new in (
            ("title", existing["title"].strip(), row.title.strip()),
            ("estimatedStart", existing.get("estimatedStart"), row.est_start),
            ("estimatedEnd", existing.get("estimatedEnd"), row.est_end),
            ("actualStart", existing.get("actualStart"), row.act_start),
            ("actualEnd", existing.get("actualEnd"), row.act_end),
        ):
            if new is not None and cur != new:
                changes[label] = (cur, new)
        if row.pct is not None and not _close(existing.get("completedPercent"), row.pct):
            changes["completedPercent"] = (existing.get("completedPercent"), row.pct)
        wanted_status = STATUS_BY_SITUACAO.get(row.situacao)
        cur_status = (existing.get("customStatus") or {}).get("statusName")
        if wanted_status and cur_status != wanted_status:
            changes["status"] = (cur_status, wanted_status)

        if row.resources:
            cur_resp = (existing.get("responsible") or {}).get("name")
            if row.resources[0] != cur_resp:
                if row.resources[0] in state.active_users:
                    changes["responsible"] = (cur_resp, row.resources[0])
                else:
                    missing_users.setdefault(row.resources[0], []).append(row.id)
            cur_part = {p["name"] for p in existing.get("participants") or []}
            want_part = set(row.resources[1:])
            if cur_part != want_part:
                for n in sorted(want_part - cur_part):
                    if n not in state.active_users:
                        missing_users.setdefault(n, []).append(row.id)
                want_ok = {n for n in want_part if n in state.active_users or n in cur_part}
                if cur_part != want_ok:
                    changes["participants"] = (sorted(cur_part), sorted(want_ok))
        if changes or note_parts:
            plan.append(
                Action(
                    "UPDATE" if changes else "INFO",
                    row.id,
                    existing["title"],
                    changes,
                    {"activity_id": int(existing["id"]), "folder_id": existing["_folder_id"], "row": row},
                    "; ".join(note_parts),
                )
            )

    for name, refs in missing_users.items():
        plan.append(Action("INFO", "usuários", name, note=f"'{name}' não é participante ativo do Artia; afeta {len(refs)} atividade(s): {', '.join(refs[:6])}{'...' if len(refs) > 6 else ''}"))
    if pct_diffs:
        plan.append(Action("INFO", "pastas", "% calculado pelo Artia", note="; ".join(pct_diffs)))
    # no Artia, dentro das pastas da planilha, mas ausente nela
    for uid, act in state.activities.items():
        if uid not in seen_uids and act["_folder_id"] in sheet_folders and not any(
            r.kind == "activity" and r.number == uid for r in rows
        ):
            plan.append(Action("DELETE", f"A{uid}", act["title"], payload={"activity_id": int(act["id"]), "folder_id": act["_folder_id"]}, note="não consta na planilha"))
    return plan


# ------------------------------------------------------------------- aplicação
def apply_plan(tools: Any, state: ArtiaState, plan: list[Action], allow_delete: bool = False) -> list[str]:
    """Executa o plano. Exclusões só com ``allow_delete`` e conferindo o título."""
    log: list[str] = []
    for act in plan:
        if act.kind == "FOLDER":
            p = act.payload
            tools.artia_update_folder(
                p["folder_id"],
                estimated_start=p.get("estimatedStart"),
                estimated_end=p.get("estimatedEnd"),
                actual_start=p.get("actualStart"),
                actual_end=p.get("actualEnd"),
            )
            log.append(f"pasta {act.ref} atualizada")
        elif act.kind == "CREATE":
            created = tools.artia_create_activity(**act.payload)
            log.append(f"criada {act.ref} -> uid {created.get('uid')}")
        elif act.kind == "UPDATE":
            _apply_update(tools, state, act)
            log.append(f"atualizada {act.ref}")
        elif act.kind == "DELETE":
            if not allow_delete:
                log.append(f"EXCLUSÃO NÃO EXECUTADA (use --allow-delete): {act.ref} {act.title}")
                continue
            tools.artia_delete_activities(
                act.payload["folder_id"], [act.payload["activity_id"]], [act.title]
            )
            log.append(f"excluída {act.ref}")
    return log


def _apply_update(tools: Any, state: ArtiaState, act: Action) -> None:
    ch, p = act.changes, act.payload
    fields = {
        "title": "title",
        "estimatedStart": "estimated_start",
        "estimatedEnd": "estimated_end",
        "actualStart": "actual_start",
        "actualEnd": "actual_end",
        "completedPercent": "completed_percent",
    }
    kwargs = {arg: ch[key][1] for key, arg in fields.items() if key in ch}
    if "responsible" in ch:
        kwargs["responsible_id"] = state.active_users[ch["responsible"][1]]
    if kwargs:
        tools.artia_update_activity(str(p["activity_id"]), p["folder_id"], **kwargs)
    if "status" in ch and ch["status"][1] in state.status_ids:
        tools.artia_change_activity_status(str(p["activity_id"]), p["folder_id"], state.status_ids[ch["status"][1]])
    if "participants" in ch:
        cur, want = set(ch["participants"][0]), set(ch["participants"][1])
        add = [state.active_users[n] for n in want - cur if n in state.active_users]
        rem = [state.users[n] for n in cur - want if n in state.users]
        if add:
            tools.artia_add_participants(p["activity_id"], add)
        if rem:
            tools.artia_remove_participants(p["activity_id"], rem)


# ------------------------------------------------------------------- relatório
def format_plan(plan: list[Action]) -> str:
    if not plan:
        return "Nada a fazer: o Artia já está igual à planilha."
    order = ["CREATE", "UPDATE", "FOLDER", "DELETE", "INFO"]
    lines = []
    for kind in order:
        items = [a for a in plan if a.kind == kind]
        if not items:
            continue
        lines.append(f"\n## {kind} ({len(items)})")
        for a in items:
            lines.append(f"- {a.ref} {a.title[:70]}")
            for k, (old, new) in a.changes.items():
                lines.append(f"    {k}: {old!r} -> {new!r}")
            if a.note:
                lines.append(f"    obs: {a.note}")
    return "\n".join(lines)
