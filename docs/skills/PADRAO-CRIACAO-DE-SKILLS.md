# Padrão de Criação de Skills

**Objetivo:** garantir que toda skill seja criada com o mesmo método, dispare quando deve, produza resultado consistente e seja fácil de manter.
**Público:** quem cria ou revisa skills (chat/claude.ai, Cowork ou Claude Code).
**Como usar:** siga as seções 3 a 8 na ordem; use a seção 9 como gate de publicação e a seção 10 como template.

---

## 1. Conceito em 30 segundos

Uma skill é uma **pasta** com um arquivo `SKILL.md` (instruções) e, opcionalmente, scripts, referências e modelos. O Claude **não carrega tudo de uma vez**. Isso se chama *divulgação progressiva*:

| Nível | O que é | Quando carrega | Custo |
|---|---|---|---|
| 1 | `name` + `description` (frontmatter) | Sempre, em toda conversa | Muito baixo |
| 2 | Corpo do `SKILL.md` | Só quando a skill é acionada | Médio |
| 3 | `references/`, `scripts/`, `assets/` | Só quando o corpo manda ler/executar | Sob demanda |

**Consequência prática:** a `description` decide se a skill é usada; o corpo decide se ela é bem usada; os arquivos de apoio permitem profundidade sem inflar o contexto.

---

## 2. Antes de criar: decida se vale a pena

Crie uma skill quando **todas** as respostas abaixo forem "sim":

1. A tarefa se repete (ou vai se repetir) com o mesmo padrão?
2. O resultado depende de método, formato ou critérios específicos que o Claude não conhece sozinho?
3. Um prompt avulso já falhou ou exigiu retrabalho para chegar ao padrão desejado?

Se a tarefa é única, curta ou não tem padrão estável, use um prompt, não uma skill.

**Onde criar**

| Cenário | Local |
|---|---|
| Uso pessoal em conversas (BPM, textos, acadêmico, estilo) | Chat/claude.ai (conta) |
| Uso em um repositório, com scripts ou versionamento | `.claude/skills/<nome>/SKILL.md` no repo |
| Uso pessoal em todos os projetos do Claude Code | `~/.claude/skills/<nome>/SKILL.md` |

---

## 3. Passo a passo (do zero à publicação)

### Passo 1: Definir o caso de uso (30 min)
Responda por escrito:
- **Quem** aciona e **em que situação** (3 a 5 frases reais que o usuário diria).
- **Entrada** esperada (texto, arquivo, link, dados) e **saída** esperada (formato, tamanho, tom, arquivo).
- **Critério de sucesso** observável: como saber, sem opinião, que o resultado está bom?
- **Fora de escopo:** o que a skill **não** deve fazer.

### Passo 2: Reunir exemplos reais
Junte 3 a 5 exemplos de **entrada → saída ideal** (feitos por você ou aprovados por você). Skill escrita sem exemplo reais tende a ser genérica.

### Passo 3: Mapear o processo
Escreva o passo a passo que um especialista humano seguiria. Marque:
- decisões (se X, então Y);
- pontos que exigem **script** (cálculo, parsing, validação, geração de arquivo);
- pontos que exigem **conhecimento de domínio** (vão para `references/`);
- erros comuns e como evitá-los.

### Passo 4: Escrever a `description`
É a parte mais importante. Fórmula:

> **O que a skill faz** + **quando usar (gatilhos e frases típicas)** + **quando NÃO usar** (se houver risco de confusão com outra skill).

Regras:
- Escreva em terceira pessoa ("Cria...", "Use quando...").
- Inclua palavras e formatos que o usuário realmente usa (ex.: "BPMN", ".docx", "ata", "levantamento").
- Seja específico o bastante para não disparar à toa e abrangente o bastante para não deixar de disparar. Na dúvida, inclua mais gatilhos: o erro mais comum é a skill **não** ser acionada.
- Limite: 1.024 caracteres. Sem tags XML.

### Passo 5: Escrever o corpo do `SKILL.md`
Use a estrutura da seção 4. Escreva no **imperativo**, explique o **porquê** das regras e inclua **exemplos**. Mantenha o corpo abaixo de ~500 linhas; o que passar disso vai para `references/`.

### Passo 6: Adicionar recursos de apoio
- `scripts/`: tarefas determinísticas (validar, converter, calcular). Código testado é mais confiável que instrução em prosa.
- `references/`: conhecimento extenso, consultado só quando preciso (normas, glossários, variações por cliente).
- `assets/`: modelos, templates, fontes, imagens usados na saída.

### Passo 7: Testar (obrigatório)
Veja a seção 6.

### Passo 8: Iterar
Corrija a causa raiz, não o sintoma. Reexecute os testes. Repita até passar no gate da seção 9.

### Passo 9: Publicar e versionar
- **Chat/claude.ai:** compacte a pasta em `.zip` (a pasta da skill na raiz) e envie em Configurações → Capacidades → Skills. Confirme os passos na interface atual, pois podem mudar.
- **Claude Code:** faça commit da pasta `.claude/skills/<nome>/` e push.
- Registre a versão e o histórico de mudanças (seção 8).

---

## 4. Anatomia da skill

```
nome-da-skill/
├── SKILL.md          # obrigatório
├── scripts/          # opcional: código executável
├── references/       # opcional: documentos de consulta
└── assets/           # opcional: modelos e arquivos usados na saída
```

### 4.1 Frontmatter (obrigatório)

```yaml
---
name: nome-da-skill
description: O que faz. Use quando [gatilhos]. Não use para [exclusões].
---
```

| Campo | Regra |
|---|---|
| `name` | minúsculas, números e hífens; até 64 caracteres; igual ao nome da pasta; nome descritivo (`ata-de-reuniao`, não `skill1`) |
| `description` | até 1.024 caracteres; o quê + quando; sem tags XML |

No Claude Code existem campos opcionais adicionais (por exemplo, restrição de ferramentas ou desativação do acionamento automático). Confirme na documentação vigente antes de usar, pois variam por versão.

### 4.2 Corpo recomendado

1. **Título e propósito** (1 a 2 frases)
2. **Quando usar / quando não usar**
3. **Entradas necessárias** e o que perguntar se faltar
4. **Processo** (passos numerados, com decisões)
5. **Formato de saída** (estrutura exata, com modelo)
6. **Regras e critérios de qualidade**
7. **Exemplos** (entrada → saída)
8. **Erros comuns / casos de borda**
9. **Checklist final** (autoverificação antes de entregar)
10. **Arquivos de apoio** (quando e por que ler cada um)

---

## 5. Melhores práticas

### Conteúdo
- **Seja específico e verificável.** "Resumo de até 5 linhas, começando pela conclusão" vale mais que "resumo bom".
- **Explique o porquê.** O modelo generaliza melhor quando entende a intenção; regras sem motivo viram comportamento rígido e frágil.
- **Evite excesso de MAIÚSCULAS, "SEMPRE" e "NUNCA".** Reserve ênfase para o que realmente é crítico e justifique.
- **Dê exemplos de entrada e saída**, incluindo um caso de borda.
- **Defina o formato exato da saída** com um modelo preenchível.
- **Defina o que fazer quando faltar informação:** perguntar, assumir (declarando a premissa) ou recusar.
- **Não invente.** Instrua a diferenciar fato, hipótese e inferência, e a citar a fonte quando houver.
- **Uma skill, um trabalho.** Se a descrição precisa de muitos "e" para caber, divida em skills menores.

### Estrutura
- **Divulgação progressiva:** corpo enxuto; detalhes em `references/`, com índice no `SKILL.md` dizendo quando ler cada arquivo.
- **Um nível de profundidade:** o `SKILL.md` aponta direto para cada referência; evite referência chamando referência.
- **Arquivo de referência grande (> 100 linhas):** inclua sumário no topo.
- **Scripts para o que é determinístico**, com mensagens de erro claras. Diga no `SKILL.md` se o script deve ser **executado** ou **lido**.
- **Caminhos relativos e com barras normais** (`references/guia.md`).

### Escrita
- Imperativo, frases curtas, termos consistentes (não alterne "cliente", "usuário" e "stakeholder" para a mesma coisa).
- Sem datas que expiram ("até agosto de 2026"); registre versões em seção própria.
- Português do Brasil quando o resultado for em português; declare o idioma de saída na skill.

### Segurança
- Nunca coloque credenciais, tokens ou dados pessoais na skill.
- Revise qualquer script de terceiros antes de usar.
- Para ações com efeito externo (enviar e-mail, publicar, apagar), exija confirmação explícita no processo.

---

## 6. Testes e validação

### 6.1 Conjunto mínimo de testes
Monte pelo menos **5 prompts**:

| Tipo | Quantidade | Objetivo |
|---|---|---|
| Caso típico | 2 | Funciona no cenário principal? |
| Caso de borda | 1 | Entrada incompleta, ambígua ou atípica |
| Variação de linguagem | 1 | Disparou com palavras diferentes das que usei? |
| **Negativo** (não deveria disparar) | 1 | Não ativa fora do escopo? |

### 6.2 O que medir
- **Disparo:** acionou quando devia e só quando devia?
- **Aderência ao processo:** seguiu os passos e o formato?
- **Qualidade da saída:** atende ao critério de sucesso do Passo 1?
- **Comparação:** a mesma tarefa **sem** a skill. Se a diferença é pequena, a skill é desnecessária ou está mal escrita.
- **Eficiência:** quantidade de turnos e tokens; o corpo não está inchado?

### 6.3 Ciclo de melhoria
1. Rode os testes e registre falhas.
2. Classifique a causa: *descrição* (não disparou), *instrução* (ambígua ou ausente), *exemplo* (faltou), *recurso* (script/referência).
3. Corrija **uma causa por vez** e reteste.
4. Se o modelo repete o mesmo erro, falta um **porquê** ou um **exemplo**, e não mais ênfase.

> No chat e no Cowork, a skill `skill-creator` automatiza criação, testes comparativos e otimização da descrição. Use-a como ferramenta de apoio a este padrão.

---

## 7. Antipadrões

| Antipadrão | Sintoma | Correção |
|---|---|---|
| Descrição vaga ("ajuda com documentos") | Não dispara ou dispara em tudo | Gatilhos concretos + exclusões |
| Skill "faz-tudo" | Instruções conflitantes | Dividir por trabalho |
| Corpo gigante | Contexto inflado, instruções ignoradas | Mover detalhes para `references/` |
| Regras sem motivo | Rigidez e erros em casos novos | Explicar o porquê |
| Sem exemplos | Saída genérica | 2 a 3 exemplos reais |
| Sem formato de saída | Resultado inconsistente | Template de saída |
| Prosa onde cabe script | Cálculo ou validação errados | Script testado |
| Informação desatualizada | Respostas obsoletas | Seção de versão e revisão periódica |
| Referências encadeadas | Leitura parcial | Tudo a um nível do `SKILL.md` |
| Nunca testada | Falha descoberta em produção | Seção 6 antes de publicar |

---

## 8. Governança e manutenção

- **Dono:** uma pessoa responsável por skill.
- **Versionamento:** `MAJOR.MINOR.PATCH` registrado no próprio `SKILL.md` (seção "Histórico").
- **Revisão:** a cada 90 dias ou quando o processo, a ferramenta ou a norma mudar.
- **Gatilho de revisão extra:** duas falhas seguidas do mesmo tipo.
- **Aposentadoria:** remova skills sem uso; descrições obsoletas competem com as boas.
- **Conflitos:** se duas skills disputam o mesmo gatilho, ajuste as exclusões nas duas descrições.

---

## 9. Checklist de publicação (gate)

**Definição**
- [ ] Caso de uso, entrada, saída e critério de sucesso escritos
- [ ] Fora de escopo definido

**Frontmatter**
- [ ] `name` em minúsculas com hífens, igual ao da pasta
- [ ] `description` com o quê + quando + (se preciso) quando não usar
- [ ] Descrição ≤ 1.024 caracteres e com frases reais do usuário

**Corpo**
- [ ] Processo em passos numerados, no imperativo
- [ ] Formato de saída com modelo
- [ ] Regras com justificativa
- [ ] Pelo menos 2 exemplos (um de borda)
- [ ] Tratamento de informação faltante
- [ ] Checklist final de qualidade
- [ ] Menos de ~500 linhas

**Recursos**
- [ ] Referências a um nível, com orientação de quando ler
- [ ] Scripts testados, com instrução "executar" ou "ler"
- [ ] Sem credenciais ou dados sensíveis

**Testes**
- [ ] ≥ 5 prompts (inclui 1 negativo e 1 variação de linguagem)
- [ ] Comparado com a execução sem a skill
- [ ] Falhas corrigidas e retestadas

**Governança**
- [ ] Dono, versão e data de revisão definidos

---

## 10. Template pronto (copie e preencha)

````markdown
---
name: nome-da-skill
description: [Verbo no presente] [o que entrega]. Use quando o usuário pedir [gatilho 1], [gatilho 2] ou mencionar [termos/formatos]. Não use para [exclusão], que é coberto por [outra skill].
---

# [Nome legível da skill]

[1 a 2 frases: propósito e resultado esperado.]

## Quando usar
- [Situação 1]
- [Situação 2]

## Quando NÃO usar
- [Situação fora de escopo → alternativa]

## Entradas necessárias
| Entrada | Obrigatória? | Se faltar |
|---|---|---|
| [Entrada A] | Sim | Perguntar |
| [Entrada B] | Não | Assumir [padrão] e declarar a premissa |

## Processo
1. [Passo 1: ação objetiva]
2. [Passo 2]
3. Se [condição], então [ação]; caso contrário, [ação].
4. [Passo final: validar antes de entregar]

## Formato de saída
```
[Estrutura exata: títulos, ordem, tamanho, tom]
```

## Regras e critérios de qualidade
- [Regra 1]. Motivo: [por quê].
- [Regra 2]. Motivo: [por quê].
- Diferencie fato, hipótese e inferência; não invente dados.

## Exemplos
**Entrada:** [exemplo realista]
**Saída:** [resultado ideal]

**Caso de borda:** [entrada atípica] → [tratamento esperado]

## Erros comuns
- [Erro] → [Como evitar]

## Checklist final
- [ ] Atende ao formato de saída
- [ ] Premissas declaradas
- [ ] [Critério específico do domínio]

## Arquivos de apoio
- `references/[arquivo].md`: leia quando [condição].
- `scripts/[arquivo].py`: execute para [finalidade]; não leia o código.

## Histórico
| Versão | Data | Mudança | Responsável |
|---|---|---|---|
| 1.0.0 | AAAA-MM-DD | Versão inicial | [nome] |
````

---

## 11. Exemplo curto de descrição: fraca × forte

**Fraca:** `Ajuda a criar atas.`

**Forte:** `Cria atas de reunião estruturadas (participantes, pauta, decisões, responsáveis e prazos) a partir de transcrições ou anotações brutas. Use quando o usuário pedir "ata", "registro da reunião", "resumo com encaminhamentos" ou colar notas/transcrição de uma reunião. Não use para resumos de artigos ou e-mails.`

---

## 12. Fluxo resumido

```
Caso de uso → Exemplos reais → Mapa do processo → Description
→ Corpo do SKILL.md → Recursos (scripts/refs/assets)
→ Testes (≥5, com negativo e comparação) → Iterar → Gate (seção 9)
→ Publicar → Versionar → Revisar a cada 90 dias
```
