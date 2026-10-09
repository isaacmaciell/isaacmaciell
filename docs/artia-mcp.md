# Arquitetura e Especificação do Artia MCP

Este documento define a especificação técnica do **Artia MCP**, servidor baseado no **Model Context Protocol (MCP)** que expõe a API GraphQL do Artia a assistentes de IA (Claude, Codex, Copilot, Cursor).

---

## 1. Visão Geral e Propósito

O Artia MCP permite que um agente consulte e atualize o planejamento de projetos da S4E no Artia (projetos, pastas, atividades, participantes, dependências e apontamentos) por meio de ferramentas tipadas, sem que o usuário precise montar consultas GraphQL.

### Objetivos
1. **Correção contra o schema real:** toda operação é validada contra o schema introspectado do Artia (`schema/`), em teste automatizado.
2. **Escrita segura:** operações destrutivas exigem confirmação explícita embutida na própria ferramenta; sincronizações simulam antes de gravar.
3. **Economia de contexto:** ferramentas devolvem só os campos necessários; listagens por pasta, não do projeto inteiro.
4. **Zero estado local:** o servidor não persiste dados; o Artia é a única fonte da verdade.

---

## 2. Princípios Arquiteturais

### 2.1. Operações declarativas (`operations.py`)
Cada operação é uma `OperationSpec`: tipo (query/mutation), campo raiz, tipos dos argumentos e campos retornados. O documento GraphQL é montado em tempo de execução **apenas com os argumentos informados**, para nunca enviar `null` em campos opcionais (o que, em atualizações, poderia apagar dados).

### 2.2. Validação contínua contra o schema
* `scripts/dump_schema.py` baixa o schema (introspecção) para `schema/artia_schema.json` e `.graphql`.
* `scripts/validate_operations.py` e o teste `test_operations_match_real_schema` falham se qualquer operação divergir do schema.
* Ao atualizar o schema, rode a validação: ela aponta exatamente o que ajustar.

### 2.3. Cliente GraphQL (`client.py`)
* Autentica com `authenticationByClient` (client ID + secret) e envia o token como `Bearer`, com o cabeçalho `OrganizationId`.
* **Cache do token** em memória, com renovação automática quando o Artia responde 401 / token expirado.
* Erros GraphQL viram `ArtiaError` com a mensagem original do Artia.
* Credenciais lidas somente de variáveis de ambiente.

### 2.4. Planejador de sincronização (`sync.py`)
Separa **calcular** de **aplicar**: `build_plan` produz uma lista de `Action` (CREATE, UPDATE, FOLDER, DELETE, INFO) sem tocar no Artia; `apply_plan` executa. Isso torna a simulação confiável e testável sem rede.

---

## 3. Modelo de dados do Artia (como o MCP enxerga)

```
Grupo de trabalho (accountId)
└── Projeto  (listingProjects)         → "Onda 1"
    └── Pasta (listingFolders, parent)  → "06-Desenvolvimento..."
        ├── Subpasta
        └── Atividade (listingActivities) → id interno + uid exibido (A84)
```

* **`id` x `uid`:** a tela mostra o `uid`; a API opera pelo `id` interno. Mapeie via `artia_list_activities`.
* **Status:** status personalizados por objeto (`Activity`, `Project`); use os ids de `artia_list_custom_status`.
* **Tipos de atividade:** ids de `artia_list_activity_types` (ex.: Planejamento, Desenvolvimento, Teste, Marco).

---

## 4. Catálogo de Ferramentas MCP (Tools)

### Leitura
| Ferramenta | Descrição | Parâmetros principais |
| :--- | :--- | :--- |
| `artia_test_connection` | Testa a autenticação | — |
| `artia_list_projects` | Projetos do grupo de trabalho | `account_id` |
| `artia_get_project` | Detalhes de um projeto | `project_id` |
| `artia_list_folders` | Todas as pastas (percorre as páginas), com a pasta pai | `account_id`, `page` |
| `artia_list_activities` | Atividades diretas de uma pasta | `folder_id` |
| `artia_get_activity` | Detalhes de uma atividade (id interno) | `activity_id`, `folder_id` |
| `artia_list_dependencies` | Predecessoras/sucessoras de uma atividade | `folder_id`, `activity_id` (obrigatório) |
| `artia_list_participants` | Participantes **ativos** (candidatos a responsável) | `account_id` |
| `artia_list_custom_status` | Status personalizados | `object_type` |
| `artia_list_activity_types` | Tipos cadastrados | `object_type` |
| `artia_list_time_entries` | Apontamentos de horas | `folder_id`, `activity_id`, `only_mine` |

### Escrita
| Ferramenta | Descrição | Observações |
| :--- | :--- | :--- |
| `artia_create_activity` | Cria atividade em uma pasta | Responsável deve ser participante ativo; datas `AAAA-MM-DD` |
| `artia_update_activity` | Atualiza campos informados | Reenvia o título atual se não informado (exigência do schema) |
| `artia_change_activity_status` | Troca o status | Usa `custom_status_id` |
| `artia_update_folder` | Atualiza datas/nome da pasta | % e situação são calculados pelo Artia |
| `artia_add_dependencies` | Cria predecessoras/sucessoras | Único caminho para influenciar o caminho crítico |
| `artia_add_participants` / `artia_remove_participants` | Gerencia participantes | `role`: `PARTICIPANT` ou `INFORMED` |
| `artia_create_time_entry` | Lança horas | Esforço em horas; hora de início obrigatória na API |
| `artia_delete_time_entry` | Exclui apontamento | |
| `artia_delete_activities` | **Exclui atividades de forma definitiva** | Exige `expected_titles` |
| `artia_graphql` | Query/mutation arbitrária | Uso avançado; sem as travas das demais |

---

## 5. Segurança

| Camada | Controle |
| :--- | :--- |
| Credenciais | Somente variáveis de ambiente; `.env` ignorado pelo Git |
| Privilégio | Usar integração dedicada, restrita ao grupo de trabalho necessário (recomendação) |
| Exclusão | `expected_titles` obrigatório; divergência de qualquer título aborta tudo |
| Sincronização | Simulação por padrão; `--apply` grava; `--allow-delete` libera exclusões |
| Campos calculados | Nunca gravados (% e situação de pastas, caminho crítico, datas reais de pastas) |
| `artia_graphql` | Não possui travas: o agente deve preferir as ferramentas específicas |

**Limitação conhecida:** o MCP não impede que um agente com `artia_graphql` execute qualquer mutation que a credencial permita. A proteção efetiva depende do escopo da credencial e da aprovação de ferramentas pelo cliente (Claude Code, Cursor etc.).

---

## 6. Protocolo de Sincronização Planilha → Artia

1. **Exportar** o Gantt (xlsx/csv) com a coluna *Status da Alteração* (opcional: `[NOVA]`, `[ALTERADA]`, `[REMOVIDA]`).
2. **Simular:** `python scripts/sync_gantt.py planilha.xlsx` e revisar o relatório (CREATE, UPDATE, FOLDER, DELETE, INFO).
3. **Resolver pendências** apontadas em INFO (usuários inexistentes ou suspensos, pasta inferida para atividades novas).
4. **Aplicar:** `--apply` (e `--fallback-responsible` se houver responsáveis ausentes).
5. **Excluir** (se houver DELETE aprovados): `--apply --allow-delete`.
6. **Reconferir:** rodar a simulação de novo; o resultado esperado é "Nada a fazer" ou apenas INFO de campos calculados.

Regras de correspondência: atividade `A<n>` ↔ `uid` n (ou título igual na mesma pasta); pasta `F<n>` ↔ id n; primeiro nome de *Recursos* = responsável, demais = participantes.

---

## 7. Operação e Testes

* **Transporte:** stdio (JSON-RPC 2.0), para uso local por IDE/CLI. O servidor lê as credenciais do ambiente do processo.
* **Testes:** `python -m pytest -q` (54 testes, sem rede, com transporte HTTP simulado). Um workflow do GitHub Actions executa a suíte a cada push.
* **Testes contra o Artia real:** `scripts/test_auth.py`, e `scripts/sync_gantt.py` em modo simulação, são seguros (somente leitura).

---

## 8. Limitações Conhecidas

* Apontamento de horas: operações validadas no schema, mas **nenhum lançamento real foi criado** por esta ferramenta; confira o primeiro na tela.
* Criação de pastas/projetos e movimentação de atividades entre pastas não são suportadas.
* A pasta de atividades novas na sincronização é inferida pela posição na planilha e pode errar em estruturas com subpastas.
* O caminho crítico depende de dependências cadastradas; planilhas sem predecessoras/sucessoras não o alteram.
* Não há transporte HTTP/SSE nem execução em container: o servidor roda localmente via stdio.
