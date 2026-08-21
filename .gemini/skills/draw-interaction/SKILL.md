---
name: draw-interaction
description: Interpreta perguntas e tarefas marcadas nos Draws, respondendo com evidências ou executando a correção na codebase.
---

# Draw Interaction

## Responsabilidade

Investigar cada marcação endereçada a esta skill e decidir se ela representa uma pergunta ou uma tarefa. O **escopo desta skill é expandido**: ela não se restringe apenas a responder perguntas pontuais, mas inclui também a inserção de nós, criação de conexões de fluxo e a manipulação visual do desenho como parte de suas tarefas. Uma pergunta pede uma resposta documentada; uma tarefa pede trabalho na codebase (editar produção, corrigir testes, criar regressão) ou atualização/alteração no fluxo do próprio Draw. Não tratar uma tarefa como se fosse apenas uma pergunta.

## Sistema de menções (@tags)

As marcações nos Draws utilizam um sistema de tags com comportamentos específicos:
- `@Looper`: indica uma pendência a ser resolvida pelo agente autônomo. Não significa apenas “responda”: quando o texto pedir uma ação concreta, o agente deve executá-la na codebase ou no Draw, validar o resultado e só então registrar a conclusão.
- `@developer`: indica uma pendência que necessita intervenção humana.
- `@OBS`: indica uma decisão arquitetural respondida que o agente deve ler e incorporar ao contexto; remova a tag somente com `looper draw consume-observation` depois do consumo explícito.
- Quando a pergunta tiver resposta, o backend remove automaticamente somente `@looper` e `@developer`; `@obs` permanece como contexto até ser consumida.

## Localização das marcações

Para perguntas, execute:

```bash
looper draw questions
```

Trabalhe somente sobre os itens JSON retornados por esse comando: o `prompt` contém `@looper` e o `answer` está ausente, `null` ou vazio (sem resposta). Cada item informa `draw_file`, `node_id`, `question_id` e os símbolos associados ao nó. Respostas existentes, inclusive `false` e `0`, não devem ser reprocessadas.

Para tarefas, execute também:

```bash
looper backlog missing
```

Leia a task, o nó do Draw, suas perguntas e respostas, `code_refs`, símbolos, arquivos, dependências, `test_ref`, testes associados e o subfluxo relacionado. Se a marcação descrever uma ação concreta, regra, bug, integração ou comportamento faltante, trate-a como tarefa de implementação.

Pedidos criados pelo ícone de loop do nó ficam em `changes`. Para consumi-los, execute `looper backlog change`. O comando reserva um pedido por vez com o nó e seus símbolos; conclua-o com `looper backlog complete <task-id>` depois de implementar, testar e registrar as evidências.

## Investigação baseada em evidências

1. Leia o desenho completo, o nó, seus pais, relações, fluxos, grupos e `draw_ref` dos subdesenhos relacionados.
2. Consulte os fatos disponíveis em `.looper/facts/` e a análise estática: `qualified_name`, arquivos, posições, dependências e chamadas.
3. Leia os símbolos completos e os testes relevantes antes de decidir. Compare o comportamento descrito com o que a codebase realmente implementa.
4. Separe fatos observados de inferências. Não invente arquivos, símbolos, respostas, permissões ou comportamento ausente.

## Quando a marcação for uma pergunta

- Grave a resposta em `question.answer`, respeitando `choice`, `boolean` ou `open`.
- Associe no próprio nó os símbolos comprovados em `code_refs`, preservando referências existentes.
- Remova somente `@looper` ou `@developer` do `question.prompt` quando a resposta estiver comprovada; deixe `@obs` para o consumo explícito.
- Se não houver evidência, mantenha a pergunta aberta e associe apenas o arquivo/símbolo relevante que puder ser comprovado.

Uma pergunta respondida não deve continuar aberta; uma pergunta sem evidência mantém a pergunta aberta.

As respostas preenchidas permanecem no Draw como histórico, inclusive `false` e `0`; não reprocessar decisões já respondidas.

## Quando a marcação for uma tarefa

- Execute o fluxo apropriado: pedidos do ícone de loop usam `looper backlog change`; demais tarefas usam `looper backlog task`. Se `backlog task` retornar `backlog-test-required`, execute `looper backlog test` e crie somente os testes antes de voltar à implementação.
- Leia os testes existentes e identifique exatamente o caminho, regra, estado, validação ou erro que falta.
- Edite a codebase dentro do escopo do nó para implementar o comportamento. Adicione ou ajuste teste de regressão quando necessário, sem enfraquecer asserções ou pré-calcular resultados.
- Execute os testes específicos, a suíte da área e `looper test` antes de concluir.
- Conclua somente o ID retornado, usando `looper backlog complete <task-id>`, e registre o trabalho com `looper log`.
- Se houver conflito entre Draw, testes e contrato, pare e informe o conflito; não escolha silenciosamente uma interpretação.

## Salvamento e rastreabilidade

Ao alterar um Draw, preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`; valide o JSON completo antes de salvar. Não altere outras perguntas, relações, grupos ou hierarquia sem relação com a marcação.

Depois de concluir, informe se a marcação era pergunta ou tarefa, a resposta ou implementação realizada, arquivos e símbolos envolvidos, testes executados, evidências e limitações. Uma pergunta sem evidência é mantida aberta; uma tarefa só é concluída com produção e testes consistentes.

## Formato obrigatório da resposta

### Resposta

Explique em linguagem natural se a marcação era uma pergunta ou tarefa e o que foi respondido ou implementado; não despeje o JSON bruto.

### Nó e símbolo associado

- **Nó:** `<label do nó>` (id `<node_id>`)
- **Símbolo associado ao nó:** `<qualified_name>` ou `<symbol>`
- **Arquivo:** `<file>`, quando disponível

### Evidências

Descreva os arquivos, símbolos, testes, contratos ou fatos que sustentam o resultado. O símbolo associado ao nó deve ser explícito; quando não houver comprovação, informe essa limitação.

### Limitações

Informe incertezas relevantes. Se não houver, escreva `Nenhuma limitação relevante encontrada.`

## Execução incremental

Consuma exatamente uma task por interação: `backlog test`, `backlog task` ou `backlog change`, leitura do contexto, mudança comprovada, testes e `backlog complete <task-id>`. Erros são caminhos condicionais (`se`/`ou`) e validações ficam antes de efeitos críticos. Use o grupo terminal `Não implementado` para escopo planejado, sem inventar sequência. APIs e apps externos devem ser registrados no `AGENTS.md` e consultados na documentação oficial.
