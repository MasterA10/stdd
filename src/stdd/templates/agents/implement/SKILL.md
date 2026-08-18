---
name: implement
description: "Percorre o loop de implementação do STDD pelo cursor do backlog: recebe uma task liberada pelos testes, entrega o melhor comportamento possível dentro do escopo pedido, valida e conclui a task com backlog complete. Usar quando a fase de testes já foi concluída."
---

# Implement Agent

## Objetivo

Percorrer o backlog até o terminal, uma task por vez. O loop é:

```text
stdd backlog task
  -> ler o contexto da task
  -> implementar somente essa task
  -> executar testes focados e o gate global
  -> stdd backlog complete <task-id>
  -> repetir até backlog-empty
```

Não declarar conclusão no meio do loop. `backlog-empty` é o único sinal de que não há outra task de implementação.

## Cursor obrigatório

O cursor do backlog é a fonte de verdade da ordem de execução. Nunca escolha uma task manualmente, pule a task retornada ou avance pelo arquivo JSON.

1. Execute `stdd backlog task` e trabalhe exatamente na task e no `task-id` retornados.
2. Retome a task que o cursor indicar como `in_progress` antes de buscar qualquer outra.
3. Depois de implementar e validar a task, execute obrigatoriamente `stdd backlog complete <task-id>` usando o mesmo ID recebido.
4. Só procure a próxima task depois que o `backlog complete` terminar com sucesso; esse comando libera e avança o cursor.
5. Repita o ciclo. Termine somente quando `stdd backlog task` retornar `kind: "backlog-empty"`.

Concluir o código ou passar nos testes não conclui a task operacionalmente. Sem `backlog complete`, a task continua aberta no cursor.

## Escopo de entrega

Leia `backlog.task_delivery_scope` em `.stdd/config.json`:

- `task`: implemente somente o ID recebido; os subfluxos serão entregues em chamadas posteriores.
- `node`: implemente o nó pai e os subfluxos listados no mesmo contexto; conclua o conjunto usando o ID do nó pai.

Essa configuração é a mesma usada por `stdd backlog test`. Em qualquer modo, siga o cursor e não escolha IDs manualmente.

## Regras do loop

1. Leia a resposta em linguagem natural de `stdd backlog task`, incluindo task, ID, predecessor, condição, pai, subfluxos, perguntas respondidas, símbolos e testes entregues pelo comando.
2. Se a resposta for `kind: "backlog-test-required"`, não implemente: volte para `$create-tests`/`stdd backlog test`.
3. Se a resposta for `kind: "backlog-bootstrap-task"`, prepare somente a estrutura mínima do projeto com as evidências locais; não implemente funcionalidade de produto.
4. Implemente apenas a task recebida, preservando contratos, autorização, dados e alterações locais do usuário.
5. Execute o teste mais específico, as suítes afetadas e `stdd test`. Falha é bloqueio; não execute `backlog complete` para avançar com validação quebrada.
6. Se houver bloqueio, deixe a task aberta e informe o motivo, a evidência e a ação necessária.

## Escopo e Draws

- Leia o Draw relacionado e seus subfluxos apenas na medida necessária para a task.
- Não implemente folhas do grupo de funcionalidades não implementadas sem escopo aprovado.
- Não invente símbolos, referências, respostas ou continuação de fluxo.
- A associação não é automática. Em todo loop, antes de concluir, associe explicitamente cada nó entregue (o L2 e todos os L3 incluídos pelo `task_delivery_scope`) aos arquivos e símbolos reais criados ou alterados nessa fase.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.

### Rastreabilidade obrigatória em cada loop

Depois de criar ou alterar os artefatos e antes de `backlog complete`:

1. Identifique, no contexto da task, o `draw_id`, o `node_id` e todos os nós cobertos pelo escopo.
2. Execute `stdd test` para atualizar os fatos estáticos e confirme na codebase/fatos o caminho do arquivo e o `qualified_name` real de cada símbolo; nunca invente um nome nem trate o arquivo como associação implícita.
3. Para cada nó coberto, execute `stdd draw associate-reference` com o símbolo real e suas dependências reais. Inclua os símbolos de teste relacionados como `--source-dependency` para manter a ligação entre implementação e teste.
   ```bash
   stdd draw associate-reference --draw-id <draw-id> --node-id <node-id> \
     --qualified-name '<símbolo-real>' --source-dependency '<símbolo-de-teste>'
   ```
4. Execute `stdd draw symbols` e confira que as associações foram gravadas no nó correto e resolvem para os arquivos esperados. Se alguma associação estiver ausente, vazia ou não puder ser comprovada, deixe a task aberta e informe o bloqueio.

Na fase de implementação, `--qualified-name` deve apontar para o símbolo de produção real; os testes vinculados entram como dependências reais. Se a fase só produzir uma estrutura de bootstrap, associe o símbolo real dessa fase ao nó, sem fabricar um símbolo de produção. O `backlog complete <task-id>` só pode ser o último comando do loop, depois dessa associação e verificação.

Para tasks originadas de `$draw-system-level-1` a `$draw-system-level-4`, ler o Draw pai e o filho, preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`, e interromper diante de fluxo órfão. A triagem deve considerar `git diff -- .stdd/draws`, `git diff --cached -- .stdd/draws`, arquivos não rastreados e ler o JSON atual completo. O diff de desenho é entrada de implementação: diante de um pedido explícito de implementar, fazer uma mudança coerente antes de concluir.

## Implementação

- Entregue a melhor mudança coerente, eficiente e segura dentro do escopo pedido, buscando a melhor experiência sem inventar escopo.
- Valide entradas antes de efeitos e mantenha falhas seguras.
- Não edite testes aprovados para obter verde nem contorne gates.
- Não adicione dependências ou mude contratos sem necessidade comprovada e escopo aprovado.
- Não grave segredos em código, Draws, logs ou evidências.

### Entrega completa da feature

Antes de implementar, inspecione o Draw (nível 2 e 3) da task e identifique todas as camadas que a feature exige. Consulte a codebase e a stack configurada em `.stdd/config.json` para descobrir onde cada camada vive no projeto. A implementação deve cobrir todas as camadas necessárias, não apenas a que o teste mais direto exercita:

- **Lógica de negócio**: use cases, services, handlers, controllers, validadores ou equivalentes da stack.
- **Apresentação**: templates, views, componentes, páginas ou qualquer artefato que renderize a resposta ao usuário. Se o Draw descreve uma tela, essa tela deve existir como artefato de apresentação na codebase, não apenas como retorno de dados de um método.
- **Integração com o framework**: registro de rotas, menus, endpoints, hooks, middleware, injeção de dependências ou qualquer mecanismo que conecte a lógica ao framework e torne a feature acessível ao usuário.
- **Assets e configuração**: scripts, estilos, migrações, seed data, configurações ou pacotes necessários para o funcionamento. Incluir enqueue, bundling, registro ou publicação conforme a convenção da stack.

Quando a stack exigir bootstrap, ponto de entrada ou manifesto, verificar se existe e se registra a feature. Se não existir, criá-lo faz parte do escopo da task.

Descobrir as convenções de cada camada pela análise da codebase existente, do `setup`, do `.stdd/design.md` e da documentação do framework. Não inventar convenções: seguir as que o projeto já usa ou, se o projeto for novo, seguir as recomendações oficiais da stack detectada.

## Validação e registro

Antes de concluir uma task, registre:

- testes executados e seus resultados;
- falhas preexistentes ou pré-condições ausentes;
- Draws e referências atualizados;
- limitações que permanecerem;
- camadas entregues e camadas ausentes em relação ao Draw.

Associar símbolos reais em todos os nós entregues com `stdd draw associate-reference` e preservar `code_refs`. O gate inclui `draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` e `draw.empty_node_symbol`.

### Uso da análise estática para refatoração segura

Usar a análise estática para refatoração segura, comparando valores antes/depois e sem esconder achados. Valores de função entre 101–150 linhas são manutenção; findings bloqueantes exigem escopo e evidência antes de uma mudança maior.

Aplicar cobertura proporcional, incluindo frontend e markdown quando aplicáveis. Teste live, pgTAP, performance, segurança, isolamento e pentest exigem escopo próprio; ausência de pré-condição é `not_executed`. Em perfil MVP, qualquer ação de instalar, baixar, criar banco ou container exige aprovação explícita.

### Critério de conclusão

Testes verdes são condição necessária, não suficiente. Para concluir uma task, verificar também:

1. **Feature alcançável**: o usuário consegue acessar a feature pelo caminho descrito no Draw.
2. **Camadas completas**: todas as camadas que o Draw exige foram entregues — lógica, apresentação, integração e assets.
3. **code_refs atualizados**: os `code_refs` do Draw apontam para todos os artefatos relevantes.
4. **Testes verdes**: `stdd test` deve passar.

Registre cada trabalho concluído separadamente:

```bash
stdd log "Implementa comportamento da task <task-id>" --type implementacao
```

O `stdd test` deve ser executado antes de declarar a tarefa concluída. Só reporte sucesso quando o diff estiver dentro do escopo, a validação passar e o backlog tiver sido avançado pelo ID correto.
