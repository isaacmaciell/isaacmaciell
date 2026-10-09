# Integração Artia (MCP)

Servidor MCP que expõe a API GraphQL do [Artia](https://artia.com) como ferramentas para o Claude:
projetos, atividades e apontamentos de horas.

## Status

| Etapa | Situação |
|---|---|
| Autenticação real (`scripts/test_auth.py`) | ✅ Validada |
| Schema real (`schema/`, via `scripts/dump_schema.py`) | ✅ Versionado |
| Operações contra o schema (`scripts/validate_operations.py`) | ✅ 21/21 válidas |
| Leituras no Artia real (projetos, pastas, atividades, participantes, status, tipos, apontamentos) | ✅ Testadas |
| Escritas (criar/atualizar atividade, atualizar pasta, remover participante, excluir atividade) | ✅ Usadas na atualização do projeto de modernização |
| Apontamento de horas (`artia_create_time_entry`, `artia_delete_time_entry`) | ⚠️ Schema válido; esforço em **horas** (conforme o formulário do Artia: `1,5` ou `01:30`). Nenhum lançamento real foi criado ainda pela ferramenta |

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
| `artia_list_folders` | `listingFolders` | leitura |
| `artia_update_folder` | `updateFolder` | escrita |
| `artia_list_activities` | `listingActivities` | leitura |
| `artia_get_activity` | `showActivity` | leitura |
| `artia_create_activity` | `createActivity` | escrita |
| `artia_update_activity` | `updateActivity` | escrita |
| `artia_change_activity_status` | `changeCustomStatusActivity` | escrita |
| `artia_delete_activities` | `destroyActivities` | **escrita irreversível** (exige os títulos esperados) |
| `artia_list_dependencies` | `listingActivityDependencies` | leitura |
| `artia_add_dependencies` | `createActivityDependencies` | escrita |
| `artia_add_participants` | `addActivityParticipants` | escrita |
| `artia_remove_participants` | `removeActivityParticipants` | escrita |
| `artia_list_participants` | `listingAccountParticipants` | leitura |
| `artia_list_custom_status` | `listingCustomStatus` | leitura |
| `artia_list_activity_types` | `listingFolderTypes` | leitura |
| `artia_list_time_entries` | `listingTimeEntries` | leitura |
| `artia_create_time_entry` | `createTimeEntry` | escrita |
| `artia_delete_time_entry` | `destroyTimeEntry` | escrita |

## Particularidades do Artia (aprendidas na prática)

- **IDs:** o `uid` exibido na tela (ex.: A84) não é o `id` interno usado pela API. Liste as atividades da pasta para mapear.
- **Hierarquia:** projeto > pastas > atividades. `artia_list_activities` retorna só as atividades diretas da pasta; pasta com apenas subpastas retorna lista vazia.
- **Responsável:** precisa ser participante **ativo** do grupo de trabalho. Usuário suspenso é recusado ("O responsável deve ser um participante do Grupo de trabalho").
- **Atualização:** o schema exige `title` em todo `updateActivity`; a ferramenta lê e reenvia o título atual quando você não o informa.
- **Campos calculados (somente leitura):** caminho crítico (`isCriticalPath`), % completo e situação de pastas/projetos são calculados pelo Artia a partir das atividades e das dependências.
- **Status e tipos:** use os ids de `artia_list_custom_status` e `artia_list_activity_types`; não há status numérico fixo.
- **Exclusão:** `artia_delete_activities` é definitiva. Exige `expected_titles`: se o título atual de qualquer atividade divergir, nada é excluído.
- **Caminho crítico:** só muda alterando dependências e datas (`artia_add_dependencies`); não há como gravá-lo diretamente.

## Uso no Claude Code

```bash
claude mcp add artia \
  -e ARTIA_CLIENT_ID=... -e ARTIA_CLIENT_SECRET=... -e ARTIA_ORGANIZATION_ID=... -e ARTIA_ACCOUNT_ID=... \
  -- python -m artia_mcp.server
```

## Sincronizar o Artia com uma planilha Gantt

`scripts/sync_gantt.py` compara uma exportação do Gantt (xlsx ou csv) com o Artia e aplica só a diferença.
Instale o extra: `pip install -e ".[sync]"`.

```bash
# 1. Simulação (padrão): mostra o plano, não grava nada
python scripts/sync_gantt.py planilha.xlsx --sheet "Gantt Comparativo"

# 2. Aplicar criações, atualizações e datas de pastas
python scripts/sync_gantt.py planilha.xlsx --sheet "Gantt Comparativo" --apply --fallback-responsible <userId>

# 3. Exclusões exigem confirmação extra
python scripts/sync_gantt.py planilha.xlsx --apply --allow-delete
```

Regras: a atividade `A97` da planilha é o `uid` 97 do Artia (ou, se não existir, a de mesmo título na mesma pasta,
para não duplicar); o primeiro nome de *Recursos* é o responsável e os demais, participantes; uma atividade marcada
`[REMOVIDA]` ou ausente da planilha entra como candidata a exclusão. Atividades novas vão para a última pasta `F...`
anterior na planilha (a pasta inferida aparece no relatório: confira antes de aplicar).
Nunca são gravados os campos que o Artia calcula (% e situação de pastas, caminho crítico, datas reais de pastas); eles
só aparecem como informação. Responsáveis que não são participantes ativos do grupo de trabalho são listados e,
nas atividades novas, substituídos por `--fallback-responsible`.

## Testes

```bash
python -m pytest -q
```
