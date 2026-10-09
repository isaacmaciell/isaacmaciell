from artia_mcp import sync

HEADER = "ID;Atividade;Início Estimado;Término Estimado;Início real;Término real;% Completo;Situação;Recursos;Tipo de Atividade;Status da Alteração"


def write_csv(tmp_path, lines):
    path = tmp_path / "gantt.csv"
    path.write_text("﻿" + HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_state():
    state = sync.ArtiaState()
    state.folders = {10: {"id": "10", "estimatedStart": "2026-01-01", "estimatedEnd": "2026-02-01", "completedPercent": 0.0}}
    state.active_users = {"Ana": 1}
    state.users = {"Ana": 1, "Bia": 2}
    state.status_ids = {"Encerrado": 9, "Em Andamento": 8, "Não Iniciada": 7}
    state.type_ids = {"desenvolvimento": 5, "teste": 6}
    state.activities = {
        1: {"id": "101", "uid": 1, "title": "Antiga ", "_folder_id": 10, "estimatedStart": "2026-01-01",
            "estimatedEnd": "2026-01-10", "actualStart": None, "actualEnd": None, "completedPercent": 10.0,
            "customStatus": {"statusName": "Em Andamento"}, "responsible": {"name": "Ana"}, "participants": []},
        2: {"id": "102", "uid": 2, "title": "Sobra", "_folder_id": 10, "estimatedStart": None, "estimatedEnd": None,
            "actualStart": None, "actualEnd": None, "completedPercent": 0.0, "customStatus": None,
            "responsible": {"name": "Ana"}, "participants": []},
    }
    return state


def test_load_sheet_parses_dates_percent_and_folder(tmp_path):
    path = write_csv(tmp_path, [
        "F10;Pasta;01/01/2026;01/02/2026;;;0%;Pendente;;;",
        "A1;Antiga;01/01/2026;15/01/2026;;;50,5%;Em Andamento;Ana;Desenvolvimento;",
    ])
    rows = sync.load_sheet(path)
    assert [r.kind for r in rows] == ["folder", "activity"]
    act = rows[1]
    assert (act.est_end, act.pct, act.folder_id, act.number) == ("2026-01-15", 50.5, 10, 1)


def test_plan_creates_updates_deletes_and_ignores_trailing_space(tmp_path):
    path = write_csv(tmp_path, [
        "F10;Pasta;01/01/2026;28/02/2026;;;0%;Pendente;;;",
        "A1;Antiga;01/01/2026;15/01/2026;;;50%;Encerrado;Ana;Desenvolvimento;",
        "A2;Sobra;;;;;0%;Não Iniciada;Ana;Desenvolvimento;[REMOVIDA]",
        "A3;Nova;01/03/2026;05/03/2026;;;0%;Não Iniciada;Cris;Teste;[NOVA]",
    ])
    plan = sync.build_plan(sync.load_sheet(path), make_state(), fallback_responsible=1)
    by_kind = {}
    for a in plan:
        by_kind.setdefault(a.kind, []).append(a)
    assert by_kind["FOLDER"][0].changes == {"estimatedEnd": ("2026-02-01", "2026-02-28")}
    update = by_kind["UPDATE"][0]
    assert "title" not in update.changes  # só diferia por espaço no fim
    assert update.changes["estimatedEnd"] == ("2026-01-10", "2026-01-15")
    assert update.changes["status"] == ("Em Andamento", "Encerrado")
    assert [d.ref for d in by_kind["DELETE"]] == ["A2"]
    create = by_kind["CREATE"][0]
    assert create.payload["activity_type_id"] == 6
    assert create.payload["custom_status_id"] == 7
    assert create.payload["responsible_id"] == 1  # provisório
    assert any("Cris" in i.title for i in by_kind["INFO"])


def test_plan_is_empty_when_already_in_sync(tmp_path):
    path = write_csv(tmp_path, [
        "F10;Pasta;01/01/2026;01/02/2026;;;0%;Pendente;;;",
        "A1;Antiga;01/01/2026;10/01/2026;;;10%;Em Andamento;Ana;Desenvolvimento;",
        "A2;Sobra;;;;;0%;;Ana;Desenvolvimento;",
    ])
    assert sync.build_plan(sync.load_sheet(path), make_state()) == []


class FakeTools:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return {"uid": 99}

        return call


def test_apply_skips_delete_without_flag():
    plan = [sync.Action("DELETE", "A2", "Sobra", payload={"activity_id": 102, "folder_id": 10})]
    tools = FakeTools()
    log = sync.apply_plan(tools, make_state(), plan)
    assert tools.calls == []
    assert "NÃO EXECUTADA" in log[0]


def test_apply_delete_passes_expected_title():
    plan = [sync.Action("DELETE", "A2", "Sobra", payload={"activity_id": 102, "folder_id": 10})]
    tools = FakeTools()
    sync.apply_plan(tools, make_state(), plan, allow_delete=True)
    assert tools.calls == [("artia_delete_activities", (10, [102], ["Sobra"]), {})]


def test_apply_update_only_sends_changed_fields():
    act = sync.Action("UPDATE", "A1", "Antiga", {"estimatedEnd": ("a", "2026-01-15"), "status": ("x", "Encerrado")},
                      {"activity_id": 101, "folder_id": 10})
    tools = FakeTools()
    sync.apply_plan(tools, make_state(), [act])
    assert tools.calls[0] == ("artia_update_activity", ("101", 10), {"estimated_end": "2026-01-15"})
    assert tools.calls[1] == ("artia_change_activity_status", ("101", 10, 9), {})
