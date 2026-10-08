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
| `artia_test_connection` | `authenticationByClient` + confirmação de organização/grupo | diagnóstico |
| `artia_graphql` | qualquer (mutations exigem `confirm=true`) | avançado |
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

## Conectando ao Claude

Pré-requisito: `pip install -e .` em um ambiente virtual. Use sempre o **caminho absoluto do Python
desse ambiente** (`<VENV>`), por exemplo `/home/voce/artia/.venv/bin/python` ou
`C:/Users/voce/artia/.venv/Scripts/python.exe`.

### Claude Code

```bash
# Exporte as credenciais no shell (ou carregue do .env) antes de registrar
export ARTIA_CLIENT_ID=... ARTIA_CLIENT_SECRET=... ARTIA_ORGANIZATION_ID=94301 ARTIA_ACCOUNT_ID=6595759

claude mcp add artia --scope user \
  -e ARTIA_CLIENT_ID="$ARTIA_CLIENT_ID" -e ARTIA_CLIENT_SECRET="$ARTIA_CLIENT_SECRET" \
  -e ARTIA_ORGANIZATION_ID="$ARTIA_ORGANIZATION_ID" -e ARTIA_ACCOUNT_ID="$ARTIA_ACCOUNT_ID" \
  -- <VENV> -m artia_mcp.server
```

| Escopo | Onde fica | Quando usar |
|---|---|---|
| `--scope local` (padrão) | só você, só neste diretório | testes |
| `--scope user` | só você, em todos os projetos | uso pessoal do dia a dia (recomendado) |
| `--scope project` | `.mcp.json` versionado no repositório | compartilhar com a equipe |

Para a equipe, versione um `.mcp.json` **sem segredos**; o Claude Code expande `${VAR}` a partir do
ambiente de cada pessoa. Como o caminho do ambiente virtual muda de pessoa para pessoa, o arquivo usa
`python`: abra o Claude Code com o ambiente virtual ativado.

```json
{
  "mcpServers": {
    "artia": {
      "command": "python",
      "args": ["-m", "artia_mcp.server"],
      "env": {
        "ARTIA_CLIENT_ID": "${ARTIA_CLIENT_ID}",
        "ARTIA_CLIENT_SECRET": "${ARTIA_CLIENT_SECRET}",
        "ARTIA_ORGANIZATION_ID": "${ARTIA_ORGANIZATION_ID}",
        "ARTIA_ACCOUNT_ID": "${ARTIA_ACCOUNT_ID}"
      }
    }
  }
}
```

Verificação: `claude mcp list` deve mostrar `artia` conectado; dentro do Claude Code, `/mcp` lista as
ferramentas. Em seguida peça "teste a conexão com o Artia" (`artia_test_connection` deve retornar
`organization.confirmed: true` e o nome do grupo).

### Claude Desktop

Edite o arquivo de configuração (Configurações > Desenvolvedor > Editar configuração):

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "artia": {
      "command": "<VENV>",
      "args": ["-m", "artia_mcp.server"],
      "env": {
        "ARTIA_CLIENT_ID": "...",
        "ARTIA_CLIENT_SECRET": "...",
        "ARTIA_ORGANIZATION_ID": "94301",
        "ARTIA_ACCOUNT_ID": "6595759"
      }
    }
  }
}
```

Reinicie o Claude Desktop por completo (fechar também pela bandeja/menu). O Desktop não lê `.env` nem
expande variáveis: as credenciais ficam nesse arquivo, que é local e não deve ser versionado nem compartilhado.

### Comportamento esperado no Claude

- Ao conectar, o servidor envia instruções com o fluxo recomendado e as particularidades da API
  (duração em horas, situação obrigatória, atividades em subpastas).
- As ferramentas são marcadas por risco: **leitura** (`list`/`get`/`test_connection`), **escrita**
  (`create`/`update`/`change_status`) e **exclusão** (`delete_time_entry`, `artia_graphql`). O cliente
  usa essas marcações para decidir quando pedir sua aprovação.
- `artia_graphql` executa consultas direto; **mutations** só rodam com `confirm=true`. Sem isso a
  ferramenta devolve o que seria executado (destacando `destroy*`) para você confirmar.

### Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `Variáveis de ambiente ausentes` | `env` não configurado no `claude mcp add` ou no JSON do Desktop |
| `organization.confirmed: false` | `ARTIA_ORGANIZATION_ID` diferente da organização da credencial |
| Servidor não aparece / `failed` | caminho do Python errado ou pacote não instalado nesse ambiente |
| "A situação especificada não foi encontrada…" | apontamento sem `status_id` |
| Apontamento com horas a mais | duração enviada já em horas em vez de minutos (`"15"` = 15 min) |

## Testes

```bash
python -m pytest -q
```
