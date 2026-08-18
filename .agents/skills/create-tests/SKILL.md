---
name: create-tests
description: "Percorre a fase de testes do loop STDD: recebe uma task, transforma o comportamento em testes executáveis, confirma a falha esperada e libera a task para implementação sem alterar produção."
---

# Create Tests

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

1. Execute `stdd backlog test` antes de criar testes. Trabalhe somente na task retornada e retome uma task `in_progress` antes de buscar outra.
2. Se receber `kind: "backlog-bootstrap-task"`, prepare apenas a estrutura mínima do projeto com base nas evidências locais; não crie testes nem produção. Conclua pelo ID recebido e retome o loop.
3. Leia o nó, predecessor, condição, pai, subfluxos, perguntas respondidas, símbolos e contratos relevantes.
4. Especifique somente comportamento observável: entrada, pré-condição, resultado, erro, limite e efeito colateral.
5. Crie o teste no runner existente da stack. Use mocks, fakes ou fixtures apenas onde a integração real não fizer parte do cenário.
6. Execute o teste focado e confirme que ele falha pelo comportamento ausente. Falha de ambiente, contrato ou cenário é bloqueio e deve ser corrigida ou reportada.
7. Execute `stdd test` antes de declarar a task concluída. Registre falhas e evidências; não trate teste ausente ou não executado como sucesso.
8. Conclua usando exatamente o ID recebido: `stdd backlog complete <task-id>`.
9. Repita o loop até não haver task de teste. Se houver bloqueio, deixe a task aberta e informe o motivo e a ação necessária.

## Escopo e Draws

- Leia o Draw relacionado e os subfluxos cobertos pela task; não transforme arquitetura em teste sem comportamento observável.
- Não teste folhas do grupo de funcionalidades não implementadas como se existissem.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.
- Se for necessária rastreabilidade, consulte `stdd draw symbols` e use `stdd draw associate-reference`; não invente símbolos nem edite `code_refs` manualmente.
- Perguntas respondidas são decisões; perguntas abertas são bloqueios quando mudarem o comportamento a testar.

## Qualidade mínima

- Nomeie o teste pelo comportamento, não pela implementação.
- Asserte resultado e efeitos reais quando o cenário for de integração; não valide apenas que uma função foi chamada.
- Cubra apenas sucesso, erro, limites e segurança aplicáveis ao risco. Não crie testes por obrigação.
- Para serviços externos, mantenha a suíte determinística offline e marque testes live como opt-in, com timeout e credencial por ambiente.
- Para renderização puramente visual (cores, fontes, espaçamento), registrar revisão visual humana. Entretanto, a existência e a funcionalidade da camada de apresentação devem ser testadas: o teste deve verificar que o artefato de apresentação existe, que recebe os dados do caso de uso e que a integração com o framework o torna acessível ao usuário (por exemplo, registro de rota, menu, endpoint, template, componente ou página). Verificar apenas o retorno de dados de um método sem confirmar que esses dados alcançam o usuário final não é teste de feature.
- Para cada task, inspecionar o Draw (nível 2 e nível 3) e identificar todas as camadas envolvidas: lógica de negócio, apresentação, integração com o framework e registro/configuração. Criar testes que cubram o comportamento observável de cada camada. Um teste que verifica apenas a camada de lógica quando o Draw descreve uma tela visível ao usuário é um teste incompleto.

## Cobertura de camadas

Uma feature descrita no Draw normalmente envolve mais de uma camada. Antes de criar os testes, identifique as camadas envolvidas inspecionando a codebase e a stack configurada:

- **Lógica de negócio**: regras, validações, transformações e decisões. Testar entradas, saídas, limites e erros.
- **Apresentação**: templates, views, componentes, páginas ou qualquer artefato que renderize a resposta ao usuário. Testar que o artefato existe, que recebe os dados corretos e que produz a resposta esperada.
- **Integração com o framework**: registro de rotas, menus, endpoints, hooks, middleware, configurações ou qualquer mecanismo que torne a feature acessível. Testar que o registro acontece e que a feature responde quando acessada pelo caminho esperado.
- **Assets e dependências**: scripts, estilos, migrações, configurações ou pacotes necessários para o funcionamento. Testar que são carregados, incluídos ou aplicados quando a feature é ativada.

Não é necessário criar todos os tipos de teste para toda task. Derive a cobertura necessária do comportamento descrito no Draw e da stack real. Quando o Draw descrever uma tela, o teste **deve** verificar que a tela existe e é alcançável, não apenas que o método de negócio retorna dados.

Se a stack não oferecer forma prática de testar uma camada (por exemplo, renderização HTML em um framework sem test helpers), registrar a limitação, criar o teste mais próximo possível e marcar revisão visual para o restante.

## Validação e registro

Ao concluir uma task, registre o comando, status, duração quando disponível, falha relevante e pré-condições ausentes. Registre a fase de testes separadamente:

```bash
stdd log "Especifica testes da task <task-id>" --type teste
```

Só entregue a fase para `$implement` quando cada task tiver teste executável, evidência da falha esperada e `backlog complete` pelo ID correto. O `stdd test` deve ser executado antes de declarar a fase concluída.
