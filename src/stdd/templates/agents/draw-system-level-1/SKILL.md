---
name: draw-system-level-1
description: "Cria o nível 1 de um Draw System no STDD: a arquitetura macro em volta da codebase, com fronteiras, tecnologias, integrações e símbolos reais de configuração/infraestrutura. Use para iniciar ou corrigir a raiz de um sistema; use draw-system-level-2 para jornadas e telas."
---

# Draw System — Nível 1: Arquitetura

## Responsabilidade

Modelar a raiz de um sistema como uma árvore navegável de desenhos JSON. Esta skill executa a parte arquitetural da Fase 1 do Draw System. Ela não descreve o funcionamento do aplicativo: prepara a fronteira que será aberta pelo `$draw-system-level-2`.

Use-a quando o pedido falar de sistema, produto, aplicativo, arquitetura completa ou mapa de jornadas. Para um comportamento isolado, use `$draw-feature`.

## Hierarquia obrigatória

A árvore é estrita e não possui fluxos órfãos. Todo desenho abaixo da raiz declara `hierarchy`, tem um pai explícito e pode ser alcançado subindo até o nível 1. Os níveis são:

| Nível | Foco | Papel | Conteúdo |
| --- | --- | --- | --- |
| 1 | escolhas macro em volta da codebase | `architecture` | aplicativo, runtime, banco, cache, autenticação, sistemas externos, fronteiras e infraestrutura |
| 2 | telas e navegação | `journey` | jornadas por papel, views, estados visíveis e caminhos de navegação |
| 3 | comportamento após a ação | `implementation` | regras, validações, autorizações, decisões e resultados em linguagem simples |
| 4 | baixo nível da codebase | `codebase` | arquivos, símbolos, contratos, queries, migrations, procedures, RPCs, testes e dependências |

A raiz usa `level: 1`, `role: "architecture"`, `parent_draw_ref: null`, `parent_node_id: null` e `root_draw_ref` igual ao próprio ID. Um descendente usa, por exemplo:

```json
"hierarchy": {
  "level": 2,
  "role": "journey",
  "parent_draw_ref": "system-architecture",
  "parent_node_id": 4,
  "root_draw_ref": "system-architecture"
}
```

Todo filho declara `parent_draw_ref`, `parent_node_id` e `root_draw_ref`. O pai contém um único bloco-cápsula com `draw_ref` para o filho. O `draw_ref` do pai, o `parent_draw_ref` do filho e o `root_draw_ref` devem formar uma cadeia resolvível em `.stdd/draws/`. A árvore permanece sem fluxos órfãos: nunca crie referência para arquivo inexistente, fluxo sem pai ou passos do filho duplicados no pai.

## Escopo arquitetural

Crie um desenho raiz `kind: "system"` com os grandes domínios e sistemas ao redor da codebase. Registre somente escolhas macro comprovadas:

- tipo do aplicativo: mobile, web, API, CLI ou outro;
- linguagem e runtime;
- banco de dados, motor e estratégia de acesso;
- cache e estratégia;
- autenticação: OAuth, JWT, sessão ou outra;
- mensageria, filas, tópicos e broker;
- provedores e serviços externos;
- fronteiras de domínio e sistemas auxiliares;
- monitoramento, observabilidade, CI/CD, deploy e infraestrutura.

Use `depends-on`, `calls`, `stores-in`, `publishes` e `consumes` para relações macro. Associe `code_refs` apenas a configuração, infraestrutura e símbolos reais retornados pela análise estática. Se a análise não comprovar um símbolo, registre a associação como pendente ou faça uma pergunta; não invente arquivos, tecnologias, integrações ou permissões.

O nível 1 não pode conter cliente clicando, telas, opções do usuário, regras de aprovação, validações, sequência de telas, estados do aplicativo ou qualquer comportamento. Tudo isso pertence ao nível 2 ou 3. A arquitetura pode mencionar cliente, administrador, operador, suporte e serviço automatizado como papéis que terão jornadas, mas não deve inventar suas permissões.

Para assuntos puramente técnicos — infraestrutura, pipeline de deploy ou migração — o nível 1 pode apontar diretamente para nível 3 ou 4, desde que o filho ainda declare o pai. Para comportamento do aplicativo, a cadeia deve passar pelo nível 2.

Inclua uma cápsula chamada `Jornadas do usuário` ou equivalente. Ela é o ponto de entrada para `$draw-system-level-2`; até o filho existir, não recebe `draw_ref` para um arquivo inexistente.

## Nó correto e consistência

Antes de criar um nó, procure na raiz o nó que mais se relaciona com o pedido. Toda alteração de relação, explicação ou referência deve ficar nesse nó; não espalhe uma decisão por vizinhos nem crie um nó genérico quando já existir uma cápsula específica.

Use `groups` para fronteiras de responsabilidade e `flows` somente para caminhos temporais. Não grave layout, cor, posição, data, HTML, CSS, JavaScript ou viewport. A cor vem do grupo no viewer, nunca de cor individual no nó.

## Convenção lógica de conexões

Toda seta usa `condition` numérico:

- `condition: 1` (`então`) é sequência/consequência certa: sempre acontece e pode coexistir com um conjunto de `se` ou com um conjunto de `ou` na mesma origem;
- `condition: 3` (`se`) é uma guarda que pode acontecer. Se houver um `se`, deve haver pelo menos outro `se` correspondente na mesma origem. Nunca misture `se` com `ou`;
- `condition: 2` (`ou`) é alternativa mutuamente exclusiva. Nunca misture `ou` com `se` na mesma decisão.

O `então` pode acompanhar qualquer uma das duas famílias, pois representa a continuação inevitável; não é uma alternativa nem uma guarda. Se dois caminhos puderem acontecer, modele sequência ou paralelismo. Pontos de decisão são expressos pelas setas, nunca por `nodes[].type`.

## Execução da Fase 1 — raiz

1. Inspecione o pedido, a stack disponível, `.stdd/config.json`, desenhos existentes, análise estática e `git status`.
2. Crie a raiz com IDs estáveis e o conjunto de escolhas macro confirmado.
3. Associe símbolos de configuração e infraestrutura nos próprios nós, usando `qualified_name`, `identity` e `source_dependencies` apenas quando disponíveis.
4. Crie a cápsula das jornadas e identifique os papéis conhecidos; deixe perguntas abertas para papéis, tenant ou permissões ainda não confirmados.
5. Crie cada JSON separadamente em `.stdd/draws/`, começando pela raiz. O JSON é a fonte de verdade; não crie `request.md`, `scenarios.md` ou cópias intermediárias.
6. Valide que relações apontam para nós existentes e que a raiz não possui pai. Grave com `stdd draw create --data-json '<JSON>'`.
7. Confira o desenho no viewer com `stdd draw serve` e revise fronteiras, perguntas e o ponto de entrada para jornadas.
8. Entregue o ID da raiz e pare. Informe que `$draw-system-level-2` deve ser executado para continuar; não produza telas nesta fase.

Se houver alteração, registre:

```bash
stdd log "Cria arquitetura do sistema no nível 1" --type implementacao
```

Ao concluir, informe raiz, escolhas macro, símbolos resolvidos ou pendentes, perguntas, arquivos alterados e o comando de revisão visual. O `$create-tests` deve receber o ID da árvore somente depois de o usuário aprovar a continuação.

## Regras do ciclo interativo

Erros são consequências condicionais (`se`/`ou`), nunca sequência inevitável; valide entradas no ponto que antecede o efeito e não crie um nó terminal genérico de validação. Funcionalidades planejadas ficam em grupo terminal `Não implementado`, sem continuação fictícia. Preserve TDD: `backlog test` antes de produção, uma task por interação e `backlog complete <task-id>` por ID. Em um projeto novo, registre tecnologias, integrações e permissões desconhecidas como planejadas ou perguntas; nível 1 não exige símbolos inexistentes.
