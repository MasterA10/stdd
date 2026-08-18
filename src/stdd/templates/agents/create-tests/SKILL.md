---
name: create-tests
description: "Percorre a fase de testes do loop STDD: recebe uma task, transforma o comportamento em testes executáveis, confirma a falha esperada e libera a task para implementação sem alterar produção."
---

# Create Tests Agent

## Objetivo

Percorrer o backlog de testes até o terminal, uma task por vez. O loop é:

```text
stdd backlog test
  -> ler o contexto da task
  -> definir o comportamento observável
  -> criar ou ajustar os testes
  -> executar e confirmar a falha esperada
  -> stdd backlog complete <task-id>
  -> repetir até terminar a fase de testes
```

Depois que a fase terminar, o próximo passo é `$implement`. Não implementar código de produção nesta skill.

## Regras do loop

1. Execute `stdd backlog test` antes de criar testes. Quando o bootstrap estiver habilitado, a primeira resposta será sempre `task:bootstrap`; conclua essa preparação pelo ID recebido antes de consumir qualquer task de teste L2 ou de subfluxo interno. Trabalhe somente na task retornada e retome uma task `in_progress` antes de buscar outra.
2. Se receber `kind: "backlog-bootstrap-task"`, prepare apenas a estrutura mínima do projeto com base nas evidências locais; não crie testes nem produção. Conclua pelo ID recebido e retome o loop.
3. Leia o nó, predecessor, condição, pai, subfluxos, perguntas respondidas, símbolos e contratos relevantes.
4. Especifique somente comportamento observável: entrada, pré-condição, resultado, erro, limite e efeito colateral.
5. Crie o teste no runner existente da stack. Use mocks, fakes ou fixtures apenas onde a integração real não fizer parte do cenário.
6. Execute o teste focado e confirme que ele falha pelo comportamento ausente. Falha de ambiente, contrato ou cenário é bloqueio e deve ser corrigida ou reportada.
7. Execute `stdd test` antes de declarar a task concluída. Registre falhas e evidências; não trate teste ausente ou não executado como sucesso.
8. Conclua usando exatamente o ID recebido: `stdd backlog complete <task-id>`.
9. Repita o loop até não haver task de teste. Se houver bloqueio, deixe a task aberta e informe o motivo e a ação necessária.

O escopo comum em `backlog.task_delivery_scope` vale para esta fase e para a implementação: `task` entrega cada nó ou subfluxo separadamente; `node` entrega o nó pai e seus subfluxos juntos, concluídos pelo ID do pai.

`backlog-test-empty` encerra somente a fila de testes. Antes de declarar a fase concluída, execute `stdd backlog task`: se retornar `backlog-test-required`, a fase ainda está bloqueada e deve voltar ao `backlog test`; se retornar `backlog-task`, os testes foram liberados e a próxima etapa é `$implement`; só `backlog-empty` indica que não há implementação restante.

## Escopo e Draws

- Leia o Draw relacionado e os subfluxos cobertos pela task; não transforme arquitetura em teste sem comportamento observável.
- Não teste folhas do grupo de funcionalidades não implementadas como se existissem.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.
- Se for necessária rastreabilidade, consulte `stdd draw symbols` e use `stdd draw associate-reference`; não invente símbolos nem edite `code_refs` manualmente.
- Perguntas respondidas são decisões; perguntas abertas são bloqueios quando mudarem o comportamento a testar.

O contexto de um `$draw-system-level-1` a `$draw-system-level-4` deve preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`. Ler `.stdd/draws/<draw-id>.json` quando o Draw for a fonte da task; tratar fluxo órfão como bloqueio e não copiar requisitos para arquivos intermediários.

Quando houver rastreabilidade, associar o símbolo real pelo `stdd draw associate-reference` e preservar `code_refs`. O gate também considera `draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` e `draw.empty_node_symbol`.

## Qualidade mínima

- Nomeie o teste pelo comportamento, não pela implementação.
- Asserte resultado e efeitos reais quando o cenário for de integração; não valide apenas que uma função foi chamada.
- Cubra apenas sucesso, erro, limites e segurança aplicáveis ao risco. Não crie testes por obrigação.
- Para serviços externos, mantenha a suíte determinística offline e marque testes live como opt-in, com timeout e credencial por ambiente.
- Para renderização puramente visual, registrar revisão visual humana; a existência, integração e alcance da apresentação devem ser verificadas quando fizerem parte do comportamento.
- Para cada task, inspecionar o Draw (nível 2 e nível 3) e identificar as camadas envolvidas: lógica, apresentação, integração com o framework e configuração. Criar a cobertura observável proporcional ao escopo.

## Validação e registro

Ao concluir uma task, registre o comando, status, duração quando disponível, falha relevante e pré-condições ausentes. Registre a fase de testes separadamente:

```bash
stdd log "Especifica testes da task <task-id>" --type teste
```

Só entregue a fase para `$implement` quando cada task tiver teste executável, evidência da falha esperada e `backlog complete` pelo ID correto. O `stdd test` deve ser executado antes de declarar a fase concluída.

Aplicar somente a cobertura proporcional ao comportamento: frontend e markdown quando fizerem parte do escopo; teste live, pgTAP, performance, segurança, isolamento e pentest somente quando aplicáveis. Ausência de runner ou pré-condição deve ser `not_executed`, nunca sucesso.
