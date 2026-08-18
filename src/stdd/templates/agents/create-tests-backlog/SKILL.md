---
name: create-tests-backlog
description: "Percorre exclusivamente a fase de testes do backlog STDD: recebe uma task liberada por stdd backlog test, transforma o comportamento em testes executáveis, confirma a falha esperada e libera a implementação."
---

# Create Tests Backlog Agent

Esta skill pertence exclusivamente ao loop de testes do backlog. Leia-a somente quando
`stdd backlog test` entregar uma resposta acionável (`backlog-bootstrap-task`,
`backlog-test-task` ou equivalente). Não leia esta skill para edições comuns, perguntas,
medições, revisões livres ou qualquer pedido que não tenha sido entregue
pelo comando `stdd backlog test`.

Se `.stdd/config.json` tiver `backlog.test_loop_enabled: false`, esta skill não deve ser executada:
o projeto optou pelo loop somente de implementação. Use `stdd backlog task` e a skill
`$implement-backlog` quando o cursor liberar a implementação.

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

Depois que a fase terminar, o próximo passo é `$implement-backlog`. Não implementar
código de produção nesta skill.

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

O escopo comum em `backlog.task_delivery_scope` vale para esta fase e para a implementação:
`task` entrega cada nó ou subfluxo separadamente; `node` entrega o nó pai e seus subfluxos
juntos, concluídos pelo ID do pai.

`backlog-test-empty` encerra somente a fila de testes. Antes de declarar a fase concluída,
execute `stdd backlog task`: se retornar `backlog-test-required`, a fase ainda está
bloqueada e deve voltar ao `backlog test`; se retornar `backlog-task`, os testes foram
liberados e a próxima etapa é `$implement-backlog`; só `backlog-empty` indica que não há
implementação restante.

## Escopo e Draws

- Leia o Draw relacionado e os subfluxos cobertos pela task; não transforme arquitetura em teste sem comportamento observável.
- Quando o Draw for a fonte da task, leia diretamente `.stdd/draws/<draw-id>.json`; não crie cópias intermediárias da especificação.
- Não teste folhas do grupo de funcionalidades não implementadas como se existissem.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`, inclusive nos Draws `draw-system-level-1` a `draw-system-level-4`; fluxo órfão é bloqueio.
- A associação não é automática e é obrigatória neste loop. Depois de criar ou alterar os testes, associe explicitamente cada nó entregue (o L2 e todos os L3 incluídos pelo `task_delivery_scope`) ao arquivo e ao símbolo real do teste.
- A implementação de teste deve cobrir a camada observável proporcional ao Draw: lógica, apresentação, integração com o framework e configuração quando fizerem parte do comportamento.
- Perguntas respondidas são decisões; perguntas abertas são bloqueios quando mudarem o comportamento a testar.

### Rastreabilidade obrigatória em cada loop

Antes de `backlog complete`:

1. Identifique, no contexto da task, o `draw_id`, o `node_id` e todos os nós cobertos pelo escopo.
2. Confirme na codebase e nos fatos estáticos o caminho do arquivo de teste e o `qualified_name` real do teste; o caminho do arquivo não é uma associação implícita e nenhum símbolo pode ser inventado.
3. Para cada nó coberto, execute `stdd draw associate-reference` usando o símbolo de teste real e as dependências reais. Não edite `code_refs` manualmente.
   ```bash
   stdd draw associate-reference --draw-id <draw-id> --node-id <node-id> \
     --qualified-name '<símbolo-real-do-teste>' --source-dependency '<dependência-real>'
   ```
4. Execute `stdd draw symbols` e confira que cada associação foi gravada no nó correto e resolve para o arquivo esperado. Se estiver ausente, vazia ou não puder ser comprovada, deixe a task aberta e informe o bloqueio.

Na fase de testes, associe o símbolo de teste que realmente foi criado ou alterado. Para
associar um nó, use o símbolo de teste real; arquivo sem `qualified_name` não é evidência.
Quando
a implementação ainda não existir, não invente um símbolo de produção para preencher o
Draw; a associação do teste deve permanecer explícita até o próximo loop. O
`backlog complete <task-id>` só pode ser o último comando do loop, depois da associação e
da verificação.

O contexto de um `$draw-system-level-1` a `$draw-system-level-4` deve preservar
`parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`. Ler o JSON do Draw quando
ele for a fonte da task; tratar fluxo órfão como bloqueio e não copiar requisitos para
arquivos intermediários.

## Qualidade mínima

- Nomeie o teste pelo comportamento, não pela implementação.
- Asserte resultado e efeitos reais quando o cenário for de integração; não valide apenas que uma função foi chamada.
- Cubra somente sucesso, erro, limites e segurança aplicáveis ao risco. Não crie testes por obrigação.
- Para serviços externos, mantenha a suíte determinística offline e marque testes live como opt-in, com timeout e credencial por ambiente.
- Para renderização puramente visual, registre revisão visual humana; a existência, integração e alcance da apresentação devem ser verificadas quando fizerem parte do comportamento.
- Para cada task, inspecione o Draw (nível 2 e nível 3) e identifique as camadas envolvidas: lógica, apresentação, integração com o framework e configuração. Crie a cobertura observável proporcional ao escopo.

## Validação e registro

Ao concluir uma task, registre o comando, status, duração quando disponível, falha relevante
e pré-condições ausentes. Registre a fase de testes separadamente:

```bash
stdd log "Especifica testes da task <task-id>" --type teste
```

Só entregue a fase para `$implement-backlog` quando cada task tiver teste executável,
evidência da falha esperada e `backlog complete` pelo ID correto. O `stdd test` deve ser
executado antes de declarar a fase concluída.

Aplicar somente a cobertura proporcional ao comportamento: frontend e markdown quando
fizerem parte do escopo; teste live, pgTAP, performance, segurança, isolamento e pentest
somente quando aplicáveis. Ausência de runner ou pré-condição deve ser `not_executed`,
nunca sucesso. O gate também considera `draw.level2_missing_code_ref`,
`draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` e
`draw.empty_node_symbol`.
