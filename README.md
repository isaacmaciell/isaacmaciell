# Integração Artia (MCP)

Servidor MCP que expõe a API GraphQL do [Artia](https://artia.com) como ferramentas para o Claude:
projetos, atividades e apontamentos de horas.

## Status

| Etapa | Situação |
|---|---|
| Cliente GraphQL (auth, cache e renovação de token) | ✅ Pronto e testado com mocks |
| Ferramentas de projetos, atividades e apontamentos | ✅ Prontas e testadas com mocks |
| Teste de autenticação real (`scripts/test_auth.py`) | ✅ OK (organização 94301, grupo 6595759) |
| Download do schema (`scripts/dump_schema.py`) | ✅ Feito (introspecção não exige token); salvo em `schema/` |
| Conferência das operações com o schema real (`scripts/validate_operations.py`) | ✅ 11/11 operações válidas |

As operações em `artia_mcp/operations.py` foram conferidas contra o schema real e o teste
`test_every_operation_matches_artia_schema` repete essa conferência a cada execução da suíte.
Projetos, atividades e apontamentos (criar e excluir) já foram exercitados com dados reais.

### Comportamentos confirmados na API real

- **`duration` é em horas decimais**: `0.25` = 15 min (08:00 → 08:15). A ferramenta converte a entrada para horas.
- **Formatos**: `dateAt` = `AAAA-MM-DD`; `startTime`/`endTime` = `HH:MM` (24 h).
- **`timeEntryStatusId` é obrigatório na prática**: sem ele o Artia responde "A situação especificada não foi
  encontrada no grupo de trabalho indicado". Use um ID de status de atividade
  (`listingCustomStatus`, `statusObject: "Activity"`).
- **Atividades ficam em subpastas**: `listingActivities` no ID do projeto pode responder "Esse grupo de trabalho
  não possui atividades"; informe o `folderId` da pasta da atividade (`listingActivitiesV2` traz o `folderId`).
- `listingOrganizations` responde "Autorização não encontrada" com token de integração; a organização pode ser
  conferida pelo `organizationId` de `listingFolderTypes`.

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
| `artia_change_activity_status` | `changeCustomStatusActivity` | escrita |
| `artia_list_time_entries` | `listingTimeEntries` | leitura |
| `artia_create_time_entry` | `createTimeEntry` | escrita |
| `artia_delete_time_entry` | `destroyTimeEntry` | escrita |

`artia_create_time_entry` aceita a duração em minutos (`90`) ou horas (`1:30`, `1h30`) e a envia ao Artia em
horas decimais; exige `start_time` (HH:MM) e `status_id` (situação da atividade) e usa a data de hoje quando
`date_at` não é informado. `artia_update_activity`
exige `title`, pois o Artia o pede em toda atualização. As ferramentas de atualização enviam apenas os campos informados.

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
