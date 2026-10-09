# Artia MCP

Servidor baseado no **Model Context Protocol (MCP)** que dá a agentes de IA (Claude, Codex, Copilot, Cursor) acesso ao **Artia** da S4E: projetos, pastas, atividades, participantes, dependências e apontamentos de horas.

Construído sobre a API GraphQL oficial do Artia, com **operações validadas contra o schema real**, **trava de segurança nas exclusões** e um script de **sincronização planilha Gantt → Artia** com modo de simulação.

> Diferente do S4E Knowledge MCP (somente leitura), este servidor **também escreve** no Artia. Leia a seção [Segurança e escrita](#-segurança-e-escrita) e o [AGENTS.md](AGENTS.md) antes de usar com um agente.

---

## 🏛️ Arquitetura

```
Agente (Claude / Codex / Copilot / Cursor)
         │  MCP (JSON-RPC 2.0 via stdio)
         ▼
┌────────────────────────────────────────────────────────┐
│                      ARTIA MCP                         │
│                                                        │
│  [server.py]      22 ferramentas MCP (leitura/escrita) │
│         │                                              │
│  [operations.py]  20 operações GraphQL tipadas        │
│         │         (validadas contra schema/)           │
│  [client.py]      Autenticação, cache e renovação de   │
│         │         token; tratamento de erros GraphQL   │
│  [sync.py]        Plano de diferenças planilha ↔ Artia │
└────────────────────────────────────────────────────────┘
         │  HTTPS (GraphQL)
         ▼
   https://app.artia.com/graphql
```

Detalhes técnicos em [docs/artia-mcp.md](docs/artia-mcp.md).

---

## ✅ Status

| Etapa | Situação |
|---|---|
| Autenticação real (`scripts/test_auth.py`) | ✅ Validada |
| Schema real versionado (`schema/`) | ✅ |
| Operações contra o schema (`scripts/validate_operations.py`) | ✅ 21/21 válidas |
| Leituras no Artia real (projetos, pastas, atividades, participantes, status, tipos, dependências) | ✅ Testadas |
| Escritas (criar/atualizar atividade, atualizar pasta, participantes, excluir atividade) | ✅ Usadas na atualização do projeto de modernização |
| Apontamento de horas (`create`/`delete_time_entry`) | ⚠️ Schema válido, **nenhum lançamento real criado ainda** |
| Sincronização planilha → Artia | ✅ Simulação testada no Artia real; `--apply` coberto por testes com mocks |

---

## 🔒 Segurança e escrita

* **Credenciais só em variáveis de ambiente.** Nunca em código, README, chat ou commit. O `.env` está no `.gitignore`.
* **Menor privilégio:** use as credenciais de uma integração dedicada, com acesso apenas ao grupo de trabalho necessário. *(Recomendação: não confirmamos se o Artia permite credenciais somente leitura.)*
* **Exclusão protegida:** `artia_delete_activities` exige o título esperado de cada atividade; se algum divergir, **nada** é excluído. A exclusão no Artia é definitiva.
* **Sincronização em duas etapas:** `scripts/sync_gantt.py` **simula por padrão**; gravar exige `--apply`, e excluir exige ainda `--allow-delete`.
* **Campos calculados nunca são gravados:** % e situação de pastas/projetos, caminho crítico e datas reais de pastas são calculados pelo Artia.

---

## 🛠️ Ferramentas MCP

| Ferramenta | Operação GraphQL | Tipo |
| :--- | :--- | :--- |
| `artia_test_connection` | `authenticationByClient` | diagnóstico |
| `artia_graphql` | qualquer (query livre) | avançado |
| `artia_list_projects` / `artia_get_project` | `listingProjects` / `showProject` | leitura |
| `artia_list_folders` | `listingFolders` (todas as páginas) | leitura |
| `artia_update_folder` | `updateFolder` | escrita |
| `artia_list_activities` / `artia_get_activity` | `listingActivities` / `showActivity` | leitura |
| `artia_create_activity` | `createActivity` | escrita |
| `artia_update_activity` | `updateActivity` | escrita |
| `artia_change_activity_status` | `changeCustomStatusActivity` | escrita |
| `artia_delete_activities` | `destroyActivities` | **escrita irreversível** |
| `artia_list_dependencies` / `artia_add_dependencies` | `listingActivityDependencies` / `createActivityDependencies` | leitura / escrita |
| `artia_add_participants` / `artia_remove_participants` | `addActivityParticipants` / `removeActivityParticipants` | escrita |
| `artia_list_participants` | `listingAccountParticipants` | leitura |
| `artia_list_custom_status` / `artia_list_activity_types` | `listingCustomStatus` / `listingFolderTypes` | leitura |
| `artia_list_time_entries` | `listingTimeEntries` | leitura |
| `artia_create_time_entry` / `artia_delete_time_entry` | `createTimeEntry` / `destroyTimeEntry` | escrita |

---

## 🚀 Instalação

### Pré-requisitos
* Python 3.10 ou superior
* Credenciais de integração do Artia (Configurações → Integrações → API)

### 1. Instalar
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # inclui pytest e openpyxl (sincronização com .xlsx)
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env             # preencha e exporte as variáveis
```

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ARTIA_CLIENT_ID` | sim | Client ID da integração |
| `ARTIA_CLIENT_SECRET` | sim | Secret da integração |
| `ARTIA_ORGANIZATION_ID` | sim | ID da organização (cabeçalho `OrganizationId`) |
| `ARTIA_ACCOUNT_ID` | não | Grupo de trabalho (`accountId`) padrão das ferramentas |
| `ARTIA_API_URL` | não | Padrão `https://app.artia.com/graphql` |

### 3. Validar em 3 passos
```bash
python scripts/test_auth.py            # autentica e confirma o token
python scripts/dump_schema.py          # atualiza schema/ a partir do Artia
python scripts/validate_operations.py  # confere cada operação contra o schema
```

---

## 🔌 Conectando agentes

Substitua `<RAIZ>` pelo caminho absoluto deste projeto. O servidor usa transporte **stdio** (uso local individual); as credenciais vão no bloco `env`.

### Claude Code
```bash
claude mcp add artia \
  -e ARTIA_CLIENT_ID=... -e ARTIA_CLIENT_SECRET=... -e ARTIA_ORGANIZATION_ID=... -e ARTIA_ACCOUNT_ID=... \
  -- <RAIZ>/.venv/bin/python -m artia_mcp.server
```

### Cursor (`.cursor/mcp.json`) e Claude Desktop
```json
{
  "mcpServers": {
    "artia": {
      "command": "<RAIZ>/.venv/bin/python",
      "args": ["-m", "artia_mcp.server"],
      "env": {
        "ARTIA_CLIENT_ID": "...",
        "ARTIA_CLIENT_SECRET": "...",
        "ARTIA_ORGANIZATION_ID": "...",
        "ARTIA_ACCOUNT_ID": "..."
      }
    }
  }
}
```

### OpenAI Codex (`~/.codex/config.toml`)
```toml
[mcp_servers.artia]
command = "<RAIZ>/.venv/bin/python"
args = ["-m", "artia_mcp.server"]
env = { ARTIA_CLIENT_ID = "...", ARTIA_CLIENT_SECRET = "...", ARTIA_ORGANIZATION_ID = "...", ARTIA_ACCOUNT_ID = "..." }
```

### VS Code / GitHub Copilot (`.vscode/mcp.json`)
```json
{
  "servers": {
    "artia": {
      "type": "stdio",
      "command": "<RAIZ>/.venv/bin/python",
      "args": ["-m", "artia_mcp.server"],
      "env": { "ARTIA_CLIENT_ID": "...", "ARTIA_CLIENT_SECRET": "...", "ARTIA_ORGANIZATION_ID": "..." }
    }
  }
}
```

> No Windows, use `<RAIZ>/.venv/Scripts/python.exe`. Prefira guardar o secret em variável do sistema ou gerenciador de segredos, em vez de em arquivo versionado.

---

## 🔄 Sincronizar o Artia com uma planilha Gantt

`scripts/sync_gantt.py` compara uma exportação do Gantt (`.xlsx` ou `.csv`) com o Artia e aplica **só a diferença**.

```bash
# 1. Simulação (padrão): mostra o plano, não grava nada
python scripts/sync_gantt.py planilha.xlsx --sheet "Gantt Comparativo"

# 2. Aplicar criações, atualizações e datas de pastas
python scripts/sync_gantt.py planilha.xlsx --sheet "Gantt Comparativo" --apply --fallback-responsible <userId>

# 3. Exclusões exigem confirmação extra
python scripts/sync_gantt.py planilha.xlsx --apply --allow-delete
```

Regras principais:
* A atividade `A97` da planilha é o `uid` 97 do Artia (ou a de mesmo título na mesma pasta, para não duplicar).
* No campo *Recursos*, o primeiro nome é o responsável e os demais são participantes.
* Atividade marcada `[REMOVIDA]`, ou ausente da planilha, entra como **candidata** a exclusão.
* Atividades novas vão para a última pasta `F...` anterior na planilha. **Confira a pasta inferida no relatório antes de aplicar.**
* Responsáveis que não são participantes ativos do grupo de trabalho são listados e substituídos por `--fallback-responsible` nas atividades novas.

---

## 🧪 Testes automatizados

```bash
python -m pytest -v
```

54 testes cobrindo: autenticação e renovação de token, tratamento de erros GraphQL, montagem de operações (sem enviar `null` em campos opcionais), validação de **todas** as operações contra o schema real, trava de exclusão, paginação, conversão de esforço em horas e todo o fluxo de sincronização (leitura da planilha, plano e aplicação). Um workflow do GitHub Actions executa a suíte a cada push.

---

## ⚠️ Particularidades do Artia (aprendidas na prática)

* **IDs:** o `uid` exibido na tela (ex.: A84) **não é** o `id` interno usado pela API. Liste as atividades da pasta para mapear.
* **Hierarquia:** projeto > pastas > atividades. `artia_list_activities` retorna só as atividades diretas da pasta; pasta com apenas subpastas retorna lista vazia.
* **Responsável:** precisa ser participante **ativo** do grupo de trabalho. Usuário suspenso é recusado.
* **Atualização:** o schema exige `title` em todo `updateActivity`; a ferramenta lê e reenvia o título atual quando não informado.
* **Dependências:** `artia_list_dependencies` exige `activity_id`, apesar de o schema marcá-lo como opcional.
* **Caminho crítico:** só muda alterando dependências e datas; não pode ser gravado diretamente.
* **Apontamento de horas:** esforço em **horas** (`1,5` ou `01:30`, como no formulário do Artia). A API exige hora de início, que a tela trata como opcional.

---

## 📚 Documentação complementar

* [docs/artia-mcp.md](docs/artia-mcp.md): especificação técnica e arquitetura.
* [AGENTS.md](AGENTS.md): diretrizes para agentes de IA (quando usar, leitura, escrita segura).
