---
name: implement
description: "Percorre o loop de implementação do STDD: recebe uma task liberada pelos testes, entrega o melhor comportamento possível dentro do escopo pedido, valida e conclui a task. Usar quando a fase de testes já foi concluída."
---

# Implement

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

## Regras do loop

1. Execute `stdd backlog task` antes de alterar produção. Retome uma task `in_progress` antes de buscar outra.
2. Leia o nó, predecessor, condição, pai, subfluxos, perguntas respondidas, símbolos e testes entregues pelo comando. Use `--json` somente quando precisar dos campos estruturados.
3. Se a resposta for `kind: "backlog-test-required"`, não implemente: volte para `$create-tests`/`stdd backlog test`.
4. Se a resposta for `kind: "backlog-bootstrap-task"`, prepare somente a estrutura mínima do projeto com as evidências locais; não implemente funcionalidade de produto. Conclua pelo ID recebido e retome o loop.
5. Implemente apenas a task recebida, preservando contratos, autorização, dados e alterações locais do usuário.
6. Execute o teste mais específico, as suítes afetadas e `stdd test`. Falha é bloqueio; não use `backlog complete` para avançar com validação quebrada.
7. Conclua usando exatamente o ID recebido: `stdd backlog complete <task-id>`.
8. Repita o loop. Se houver bloqueio, deixe a task aberta e informe o motivo, a evidência e a ação necessária.

## Escopo e Draws

- Leia o Draw relacionado e seus subfluxos apenas na medida necessária para a task.
- Não implemente folhas do grupo de funcionalidades não implementadas sem escopo aprovado.
- Não invente símbolos, referências, respostas ou continuação de fluxo.
- Quando uma associação for necessária, consulte `stdd draw symbols` e grave-a com `stdd draw associate-reference`; não edite `code_refs` manualmente.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.

## Implementação

- Entregue a melhor mudança coerente, eficiente e segura dentro do escopo pedido, buscando a melhor experiência sem inventar escopo.
- Valide entradas antes de efeitos e mantenha falhas seguras.
- Não edite testes aprovados para obter verde nem contorne gates.
- Não adicione dependências ou mude contratos sem necessidade comprovada e escopo aprovado.
- Não grave segredos em código, Draws, logs ou evidências.

### Entrega completa da feature

Antes de implementar, inspecione o Draw (nível 2 e 3) da task e identifique todas as camadas que a feature exige. Consulte a codebase e a stack configurada em `.stdd/config.json` para descobrir onde cada camada vive no projeto. A implementação deve cobrir **todas** as camadas necessárias, não apenas a que o teste mais direto exercita:

- **Lógica de negócio**: use cases, services, handlers, controllers, validadores ou equivalentes da stack.
- **Apresentação**: templates, views, componentes, páginas ou qualquer artefato que renderize a resposta ao usuário. Se o Draw descreve uma tela, essa tela deve existir como artefato de apresentação na codebase, não apenas como retorno de dados de um método.
- **Integração com o framework**: registro de rotas, menus, endpoints, hooks, middleware, injeção de dependências ou qualquer mecanismo que conecte a lógica ao framework e torne a feature acessível ao usuário.
- **Assets e configuração**: scripts, estilos, migrações, seed data, configurações ou pacotes necessários para o funcionamento. Incluir enqueue, bundling, registro ou publicação conforme a convenção da stack.

Quando a stack exigir bootstrap, ponto de entrada ou manifesto (como um arquivo principal de plugin, app, módulo ou pacote), verificar se existe e se registra a feature. Se não existir, criá-lo faz parte do escopo da task.

Descobrir as convenções de cada camada pela análise da codebase existente, do `setup`, do `.stdd/design.md` e da documentação do framework. Não inventar convenções: seguir as que o projeto já usa ou, se o projeto for novo, seguir as recomendações oficiais da stack detectada.

## Validação e registro

Antes de concluir uma task, registre:

- testes executados e seus resultados;
- falhas preexistentes ou pré-condições ausentes;
- Draws e referências atualizados;
- limitações que permanecerem;
- camadas entregues e camadas ausentes em relação ao Draw.

### Critério de conclusão

Testes verdes são condição necessária, não suficiente. Para concluir uma task, verificar também:

1. **Feature alcançável**: o usuário consegue acessar a feature pelo caminho descrito no Draw (rota, menu, link, comando ou equivalente da stack). Se o Draw descreve uma tela, a tela deve existir e ser renderizável.
2. **Camadas completas**: todas as camadas que o Draw exige foram entregues — lógica, apresentação, integração e assets. Se alguma camada não puder ser entregue, registrar a limitação e o motivo.
3. **code_refs atualizados**: os `code_refs` do Draw devem apontar para todos os artefatos relevantes — não apenas para o caso de uso/service, mas também para a view, template, componente ou artefato de apresentação, quando existirem.
4. **Testes verdes**: `stdd test` deve passar.

Registre cada trabalho concluído separadamente:

```bash
stdd log "Implementa comportamento da task <task-id>" --type implementacao
```

O `stdd test` deve ser executado antes de declarar a tarefa concluída. Só reporte sucesso quando o diff estiver dentro do escopo, a validação passar e o backlog tiver sido avançado pelo ID correto.
