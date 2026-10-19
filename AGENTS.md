# AGENTS.md — Guia de Uso do Artia MCP para Agentes de IA

Diretrizes operacionais para agentes (Claude, Codex, Copilot, Cursor) ao usar o **Artia MCP** da S4E.

---

## 1. O que é o Artia MCP?

Servidor MCP que dá acesso ao **Artia**: projetos, pastas, atividades, participantes, dependências e apontamentos de horas da S4E. Diferente do Knowledge MCP (somente leitura), ele **escreve no Artia**, e a exclusão é definitiva. Trate toda ferramenta de escrita como uma ação sobre dados reais de pessoas reais.

---

## 2. Quando usar?

### ✅ DEVE usar
* Consultar o andamento de projetos, pastas e atividades do Artia (datas, %, status, responsáveis).
* Atualizar o planejamento a pedido do usuário (criar/alterar atividades, ajustar datas de pastas, trocar status, gerenciar participantes e dependências).
* Sincronizar uma planilha Gantt com o Artia (`scripts/sync_gantt.py`).
* Lançar horas, **quando o usuário pedir explicitamente**.

### ❌ NÃO DEVE usar
* Para perguntas genéricas sobre gestão de projetos, Scrum, Gantt ou Artia como produto.
* Para "testar" escritas: **não crie, altere ou exclua dados de produção só para experimentar**.
* `artia_graphql` quando existir ferramenta específica: ele não tem as travas de segurança.

---

## 3. Protocolo de Leitura (do geral ao específico)

1. **Projetos:** `artia_list_projects` para achar o projeto.
2. **Pastas:** `artia_list_folders` (uma chamada traz todas, com a pasta pai).
3. **Atividades:** `artia_list_activities(folder_id)` só nas pastas necessárias. Não liste o projeto inteiro sem necessidade.
4. **Mapeie `uid` → `id`:** o código que o usuário vê (ex.: A84) é o `uid`; as ferramentas usam o `id` interno.
5. **Pasta sem atividades próprias** (só subpastas) retorna lista vazia: não é erro.

---

## 4. Protocolo de Escrita (obrigatório)

```
LER estado atual → PROPOR mudança ao usuário → CONFIRMAR → ESCREVER → RELER e conferir
```

1. **Leia antes de escrever.** Confirme que o alvo é o esperado (id interno, título, pasta).
2. **Mostre o que vai mudar** (campo: valor atual → novo) e peça confirmação para mudanças relevantes ou em lote.
3. **Escreva uma operação por vez** em ações destrutivas ou em lote, para poder parar se algo falhar.
4. **Reler e conferir** depois de escrever. Não declare sucesso só porque a chamada não deu erro.
5. **Reporte fielmente** o que foi e o que não foi aplicado, inclusive bloqueios de permissão.

### Exclusão (`artia_delete_activities`)
* Só com **confirmação explícita do usuário para aquele item**; aprovação anterior de outra ação não vale.
* Passe `expected_titles`. Se a ferramenta recusar por divergência de título, **pare e investigue**; não ajuste o título esperado para "fazer passar".
* Se uma exclusão for bloqueada por permissão do cliente, **não contorne**: explique e deixe o usuário decidir (ou excluir pela tela do Artia).

### Sincronização com planilha
* **Sempre simule antes** (`scripts/sync_gantt.py` sem `--apply`) e apresente o relatório.
* Revise INFO: usuários ausentes ou suspensos, pasta inferida de atividades novas.
* Use `--apply`; exclusões só com `--allow-delete` e confirmação do usuário.
* Ao terminar, rode a simulação de novo para provar que o Artia ficou igual à planilha.

---

## 5. Regras do Artia que quebram suposições

| Situação | O que acontece | O que fazer |
| :--- | :--- | :--- |
| Responsável suspenso/inexistente | Recusado ("responsável deve ser participante do Grupo de trabalho") | Consultar `artia_list_participants`; pedir um responsável provisório ao usuário |
| Caminho crítico, % e situação de pastas | **Calculados pelo Artia; não são graváveis** | Explicar ao usuário; para influenciar o caminho crítico, usar dependências |
| `updateActivity` sem título | O schema exige `title` | A ferramenta já reenvia o título atual |
| `artia_list_dependencies` sem `activity_id` | "Activity not found" | Sempre informar `activity_id` |
| Datas | Formato `AAAA-MM-DD` | |
| Apontamento de horas | Esforço em **horas** (`1,5` ou `01:30`); hora de início exigida pela API | Conferir o primeiro lançamento na tela |
| % completo e status de atividade | Podem ser alterados, mas % de pasta/projeto deriva das atividades | Atualizar a atividade, não a pasta |

---

## 6. Como Resolver Conflitos: Planilha x Artia

Quando a planilha e o Artia divergirem:

1. **Pergunte qual é a fonte da verdade** para aquele conjunto (normalmente a planilha aprovada pelo gerente de projetos).
2. **Separe diferenças reais de efeito de cálculo** (ex.: % de pasta, caminho crítico): estas não se corrigem gravando.
3. **Sinalize mudanças não declaradas.** Se a planilha tiver alterações que o resumo do usuário não menciona (ex.: um recurso removido, uma troca de caminho crítico), aponte-as antes de aplicar.
4. Não altere regras de planejamento silenciosamente.

---

## 7. Boas práticas de contexto e eficiência

* Prefira leituras pontuais (`list_activities` por pasta) a varreduras do projeto inteiro.
* Reaproveite ids já obtidos na conversa; não releia sem necessidade.
* Para "o que mudou?", use a simulação do sync em vez de comparar à mão.
* Nunca registre `ARTIA_CLIENT_SECRET` em código, commit, chat ou documento.

---

## 8. Checklist rápido antes de qualquer escrita

- [ ] Li o estado atual do alvo?
- [ ] O usuário confirmou esta mudança (e, se for exclusão, este item)?
- [ ] O responsável é um participante ativo?
- [ ] Estou gravando um campo que o Artia calcula? (Se sim, não grave.)
- [ ] Vou reler e conferir depois?
