# Integração Artia (MCP)

Servidor MCP que expõe a API GraphQL do [Artia](https://artia.com) como ferramentas para o Claude:
projetos, atividades e apontamentos de horas.

## Status

| Etapa | Situação |
|---|---|
| Cliente GraphQL (auth, cache e renovação de token) | ✅ Pronto e testado com mocks |
| Ferramentas de projetos, atividades e apontamentos | ✅ Prontas e testadas com mocks |
| Teste de autenticação real (`scripts/test_auth.py`) | ⏳ Pendente: credenciais e acesso de rede |
| Download do schema (`scripts/dump_schema.py`) | ⏳ Pendente: credenciais e acesso de rede |
| Conferência das operações com o schema real (`scripts/validate_operations.py`) | ⏳ Pendente: depende do schema |

Os nomes de operações e campos em `artia_mcp/operations.py` seguem a documentação pública do Artia,
mas **ainda não foram conferidos contra o schema real**. O passo 3 abaixo aponta exatamente o que ajustar.

## Configuração

```bash
pip install -e ".[dev]"
cp .env.example .env   # preencha e exporte as variáveis
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ARTIA_CLIENT_ID` | sim | Client ID da integração (Artia > Configurações > Integrações > API) |
| `ARTIA_CLIENT_SECRET` | sim | Secret da integração |
| `ARTIA_ORGANIZATION_ID` | sim | ID da organização (cabeçalho `OrganizationId`) |
| `ARTIA_ACCOUNT_ID` | não | Grupo de trabalho padrão (`accountId`) das ferramentas |
| `ARTIA_API_URL` | não | Padrão `https://app.artia.com/graphql` |

## Validação em 3 passos

```bash
python scripts/test_auth.py            # 1. autentica e confirma o token
python scripts/dump_schema.py          # 2. salva schema/ e lista queries e mutations
python scripts/validate_operations.py  # 3. confere cada operação contra o schema
```

Se o passo 3 apontar erro, ajuste o `OperationSpec` correspondente em `artia_mcp/operations.py`
(nome do campo raiz, tipos dos argumentos ou campos retornados) e rode de novo.

## Ferramentas

| Ferramenta | Operação GraphQL | Tipo |
|---|---|---|
| `artia_test_connection` | `authenticationByClient` | diagnóstico |
| `artia_graphql` | qualquer (query livre) | avançado |
| `artia_list_projects` | `listingProjects` | leitura |
| `artia_get_project` | `showProject` | leitura |
| `artia_list_activities` | `listingActivities` | leitura |
| `artia_get_activity` | `showActivity` | leitura |
| `artia_create_activity` | `createActivity` | escrita |
| `artia_update_activity` | `updateActivity` | escrita |
| `artia_change_activity_status` | `changeStatusActivity` | escrita |
| `artia_list_time_entries` | `listingTimeEntries` | leitura |
| `artia_create_time_entry` | `createTimeEntry` | escrita |
| `artia_delete_time_entry` | `destroyTimeEntry` | escrita |

`artia_create_time_entry` aceita a duração em minutos (`90`) ou horas (`1:30`, `1h30`) e usa a data de hoje
quando `date_at` não é informado. As ferramentas de atualização enviam apenas os campos informados.

## Uso no Claude Code

```bash
claude mcp add artia \
  -e ARTIA_CLIENT_ID=... -e ARTIA_CLIENT_SECRET=... -e ARTIA_ORGANIZATION_ID=... -e ARTIA_ACCOUNT_ID=... \
  -- python -m artia_mcp.server
```

## Testes

```bash
python -m pytest -q
```
