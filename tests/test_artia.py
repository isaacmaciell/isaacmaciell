import json

import httpx
import pytest
from graphql import parse

from artia_mcp import operations as ops
from artia_mcp import server
from artia_mcp.client import ArtiaClient, ArtiaConfig, ArtiaError


def make_client(handler):
    config = ArtiaConfig("cid", "secret", "org-1", account_id=42, api_url="https://artia.test/graphql")
    return ArtiaClient(config, transport=httpx.MockTransport(handler))


def auth_response(token="tok-1"):
    return httpx.Response(200, json={"data": {"authenticationByClient": {"token": token}}})


def test_authenticate_sends_credentials_and_org_header():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["headers"] = request.headers
        return auth_response()

    client = make_client(handler)
    assert client.authenticate() == "tok-1"
    assert seen["body"]["variables"] == {"clientId": "cid", "secret": "secret"}
    assert seen["headers"]["OrganizationId"] == "org-1"
    assert "Authorization" not in seen["headers"]


def test_execute_uses_bearer_token_and_caches_it():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append((body["query"], request.headers.get("Authorization")))
        if "authenticationByClient" in body["query"]:
            return auth_response()
        return httpx.Response(200, json={"data": {"listingProjects": []}})

    client = make_client(handler)
    client.execute("query { listingProjects(accountId: 1) { id } }")
    client.execute("query { listingProjects(accountId: 1) { id } }")
    assert sum("authenticationByClient" in q for q, _ in calls) == 1
    assert calls[-1][1] == "Bearer tok-1"


def test_execute_reauthenticates_on_expired_token():
    tokens = iter(["old", "new"])
    state = {"rejected": False}

    def handler(request):
        body = json.loads(request.content)
        if "authenticationByClient" in body["query"]:
            return auth_response(next(tokens))
        if request.headers["Authorization"] == "Bearer old" and not state["rejected"]:
            state["rejected"] = True
            return httpx.Response(401, text="Unauthorized")
        return httpx.Response(200, json={"data": {"ok": True}})

    assert make_client(handler).execute("query { ok }") == {"ok": True}


def test_graphql_errors_raise():
    def handler(request):
        body = json.loads(request.content)
        if "authenticationByClient" in body["query"]:
            return auth_response()
        return httpx.Response(200, json={"errors": [{"message": "Field 'x' doesn't exist"}]})

    with pytest.raises(ArtiaError, match="doesn't exist"):
        make_client(handler).execute("query { x }")


def test_failed_authentication_raises():
    client = make_client(lambda r: httpx.Response(200, json={"data": {"authenticationByClient": None}}))
    with pytest.raises(ArtiaError, match="token"):
        client.authenticate()


def test_config_from_env_reports_missing(monkeypatch):
    for name in ("ARTIA_CLIENT_ID", "ARTIA_CLIENT_SECRET", "ARTIA_ORGANIZATION_ID"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ArtiaError, match="ARTIA_CLIENT_ID"):
        ArtiaConfig.from_env()


@pytest.mark.parametrize("name,spec", ops.ALL_OPERATIONS.items())
def test_every_operation_is_valid_graphql(name, spec):
    parse(spec.document(spec.arg_types))


def test_build_omits_null_arguments():
    document, variables = ops.UPDATE_ACTIVITY.build(
        {"id": "7", "accountId": 1, "folderId": 2, "title": "Novo", "description": None}
    )
    assert variables == {"id": "7", "accountId": 1, "folderId": 2, "title": "Novo"}
    assert "$description" not in document
    parse(document)


def test_build_requires_mandatory_arguments():
    with pytest.raises(ValueError, match="title"):
        ops.CREATE_ACTIVITY.build({"accountId": 1, "folderId": 2})


@pytest.mark.parametrize("value,expected", [(90, 90), ("90", 90), ("1:30", 90), ("1h30", 90), ("2h", 120), ("45min", 45)])
def test_parse_duration(value, expected):
    assert server.parse_duration(value) == expected


def test_parse_duration_rejects_zero():
    with pytest.raises(ValueError):
        server.parse_duration("0")


def test_create_time_entry_tool(monkeypatch):
    sent = {}

    def handler(request):
        body = json.loads(request.content)
        if "authenticationByClient" in body["query"]:
            return auth_response()
        sent.update(body)
        return httpx.Response(200, json={"data": {"createTimeEntry": {"id": "99"}}})

    monkeypatch.setattr(server, "_client", make_client(handler))
    result = server.artia_create_time_entry(
        activity_id=10, duration="1:15", start_time="09:00", date_at="2026-10-08", observation="Reunião"
    )
    assert result == {"id": "99"}
    assert sent["variables"] == {
        "accountId": 42, "activityId": 10, "dateAt": "2026-10-08", "startTime": "09:00",
        "duration": 75.0, "observation": "Reunião",
    }
    assert "createTimeEntry(" in sent["query"]


def test_list_projects_requires_account(monkeypatch):
    client = make_client(lambda r: auth_response())
    client.config.account_id = None
    monkeypatch.setattr(server, "_client", client)
    with pytest.raises(ArtiaError, match="account_id"):
        server.artia_list_projects()


def _tool_client(monkeypatch, responder):
    def handler(request):
        body = json.loads(request.content)
        if "authenticationByClient" in body["query"]:
            return auth_response()
        return httpx.Response(200, json=responder(body))

    monkeypatch.setattr(server, "_client", make_client(handler))


def test_update_activity_reuses_current_title(monkeypatch):
    sent = []

    def responder(body):
        sent.append(body)
        if "showActivity" in body["query"]:
            return {"data": {"showActivity": {"title": "Título atual"}}}
        return {"data": {"updateActivity": {"id": "1"}}}

    _tool_client(monkeypatch, responder)
    server.artia_update_activity("1", folder_id=5, completed_percent=50.0)
    assert sent[-1]["variables"]["title"] == "Título atual"
    assert sent[-1]["variables"]["completedPercent"] == 50.0


def test_list_activities_returns_empty_for_folder_without_activities(monkeypatch):
    _tool_client(
        monkeypatch,
        lambda body: {"errors": [{"message": "Esse grupo de trabalho não possui atividades"}]},
    )
    assert server.artia_list_activities(folder_id=1) == []


def test_other_graphql_errors_still_raise(monkeypatch):
    _tool_client(monkeypatch, lambda body: {"errors": [{"message": "Sem permissão"}]})
    with pytest.raises(ArtiaError, match="Sem permissão"):
        server.artia_list_activities(folder_id=1)


def test_operations_match_real_schema():
    import pathlib

    from graphql import build_client_schema, validate

    path = pathlib.Path(__file__).resolve().parents[1] / "schema" / "artia_schema.json"
    schema = build_client_schema(json.loads(path.read_text()))
    for name, spec in ops.ALL_OPERATIONS.items():
        errors = validate(schema, parse(spec.document(spec.arg_types)))
        assert not errors, f"{name}: {[e.message for e in errors]}"
