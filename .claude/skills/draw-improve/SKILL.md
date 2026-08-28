---
name: draw-improve
description: Identifica lacunas arquiteturais em um Draw existente por meio de perguntas, abre somente as perguntas necessárias para lacunas descobertas depois e, após a clarificação, aplica as respostas e enriquece os nós correspondentes com o contexto consolidado.
---

# Draw Improve

## Responsabilidade

O `$draw-improve` trabalha em duas fases explícitas:

1. **Perguntar:** revisar o Draw inteiro, criar exatamente dez perguntas arquiteturais em uma sessão separada de `.looper/improvements/` e parar para a resposta humana. Nesta fase não alterar `.looper/draws/<draw-id>.json`, não criar nós e não criar conexões.
2. **Aplicar:** em uma nova invocação, localizar sessões completas com `looper draw improve --pending`, ler as respostas, revisar novamente o Draw associado e aplicar somente o próximo incremento coerente. Quando o gate final confirmar que não existem mais lacunas abertas pelas respostas, consolidar cada pergunta e resposta no nó correspondente, salvar o Draw enriquecido e só então marcar a sessão como `applied`.

O ciclo só termina depois de apresentar o resultado e pedir revisão. `Já está bom` continua sendo uma conclusão válida quando não houver lacuna relevante, mas a fase de perguntas deve existir sempre que uma decisão arquitetural depender da pessoa. Uma nova invocação inicia um ciclo posterior; não repetir automaticamente o ciclo atual.

## Sessão de perguntas

Uma sessão é um JSON separado em `.looper/improvements/<improvement-id>.json`, associado por `draw_id`. Ela não é um subdraw, não pertence à hierarquia arquitetural e nunca deve ser gravada dentro do JSON do fluxo. O campo `questions` guarda as respostas, e o status `applied` identifica o histórico imutável.

A sessão inicial deve possuir exatamente dez perguntas. Uma sessão de acompanhamento criada pelo gate de lacunas deve possuir somente a quantidade necessária para resolver as novas lacunas, com pelo menos uma pergunta. Cada pergunta usa um destes tipos:

- `boolean`: sim ou não;
- `choice`: de duas a quatro opções neutras, exibidas como A, B, C ou D;
- `open`: resposta curta em texto.

Todas começam com `answer: null`, isto é, sem resposta. Não registrar recomendações, respostas presumidas ou perguntas para investigação da codebase. As perguntas devem ser específicas, independentes e capazes de alterar arquitetura, casos de uso, riscos, responsabilidades, conexões, grupos ou fluxos.

Criar a sessão pelo contrato oficial:

```bash
looper draw improve --create --data-json '<JSON_DA_SESSAO>'
```

Depois, orientar a pessoa a abrir o viewer, responder as perguntas da sessão e salvar. A UI salva somente `.looper/improvements/`; o Draw continua intacto.

## Revisão da hierarquia e do Draw inteiro

Em ambas as fases, ler o Draw completo e, quando houver `hierarchy`, revisar a árvore. Confirmar que o nível 1 contém decisões macro, o nível 2 representa jornadas por papel, o nível 3 contém a implementação da jornada e o nível 4 só aparece quando a codebase exigir rastreabilidade técnica.

Todo descendente deve declarar `parent_draw_ref`, `parent_node_id` e `root_draw_ref`, enquanto o pai aponta para ele com `draw_ref`. Nunca criar fluxo órfão. Folhas não implementadas permanecem terminais e pertencem ao grupo específico de funcionalidades não implementadas.

Na revisão global obrigatória, ler todos os nós, relações, grupos, fluxos, subdesenhos, perguntas e decisões respondidas; o objeto `groups` também faz parte da revisão. Procurar, nesta ordem, caminho principal incompleto, recuperação ausente, fronteira de responsabilidade ambígua, dependência arriscada, decisão sem condição, segurança ou autorização ausente, observabilidade necessária, caso de uso não representado e hierarquia incoerente.

Organizar os nós em grupos arquiteturais coerentes e corrigir descrições vagas, duplicações, nós órfãos, relações inválidas, branches que bypassam decisões e inconsistências entre o fluxo principal e seus subfluxos.

## Fase de aplicação

Executar:

```bash
looper draw improve --pending
```

Usar somente sessões `ready`, isto é, com todas as respostas válidas da própria sessão. Nunca aplicar uma sessão `draft` ou inferir resposta ausente. O comando entrega o `draw_id`, o arquivo da sessão, as perguntas e as respostas.

Para cada sessão pronta:

1. Ler o JSON atual do Draw pelo `draw_id`; não usar uma cópia antiga da sessão como fonte para substituir o Draw.
2. Interpretar as respostas como decisões explícitas da pessoa.
3. Antes de alterar qualquer fluxo, executar o **gate de lacunas abertas pelas respostas**: revisar novamente todos os nós, relações, grupos, flows, subdraws, perguntas e decisões do Draw e verificar se cada resposta criou uma nova regra, exceção, dependência, conflito, caminho incompleto ou decisão arquitetural ainda sem resposta.
4. Se o gate encontrar uma lacuna que exija decisão humana, não alterar o Draw, não marcar a sessão atual como `applied` e não inventar a decisão. Criar uma nova sessão de acompanhamento com somente a quantidade de perguntas necessária para resolver as lacunas recém-criadas, com pelo menos uma pergunta, e parar para a resposta humana. Enquanto essa sessão derivada estiver aberta, a sessão anterior não pode ser aplicada isoladamente.
5. Somente se nenhuma nova lacuna relevante for encontrada, fazer uma única melhoria coerente, podendo alterar nós, relações, grupos, flows ou um subdraw quando isso for consequência direta das respostas.
6. Depois que o gate confirmar que não há mais lacunas, enriquecer os nós com a memória da clarificação:
   - associar cada pergunta ao nó cujo assunto, descrição, decisões, símbolos, `draw_ref` ou papel arquitetural corresponda diretamente ao tema da pergunta;
   - preferir um único nó específico a um nó genérico; se o assunto atravessar nós, associar ao nó que possui a decisão ou responsabilidade principal;
   - injetar em `node.questions` a pergunta original, o tipo, as opções quando existirem e a resposta final, preservando o texto humano e o contexto da decisão;
   - manter a origem com `source_improvement_id` e `source_question_id` quando esses campos não existirem, para auditoria e para impedir duplicação em reaplicações;
   - atualizar uma associação existente pela origem em vez de criar outra cópia; não apagar perguntas anteriores nem substituir respostas de outra sessão;
   - se não houver correspondência inequívoca, não descartar a resposta nem inventar um vínculo: registrar a pendência para revisão humana e não marcar a sessão como `applied`.
7. Preservar IDs e significado existentes salvo quando houver inconsistência objetiva.
8. Usar `condition: 1` para `então`, `condition: 2` para `ou` e `condition: 3` para `se`.
9. Validar o JSON e as referências do Draw, inclusive os IDs das perguntas injetadas e a associação de cada resposta a um nó real.
10. Persistir o Draw completo com:

   ```bash
   looper draw create --data-json '<JSON_COMPLETO_ATUALIZADO>'
   ```

11. Somente depois de o Draw ser salvo com sucesso, executar:

   ```bash
   looper draw improve --mark-applied --id <improvement-id>
   ```

Uma sessão `applied` é histórica e imutável. Não reaplicá-la nem apagar suas perguntas e respostas.

Uma sessão não pode ser considerada aplicada enquanto suas respostas estiverem somente em `.looper/improvements/`; a aplicação exige que a pergunta e a resposta estejam também persistidas no `node.questions` correspondente do Draw.

O gate de lacunas é obrigatório mesmo quando todas as perguntas da sessão já foram respondidas. Responder uma pergunta pode revelar outra pergunta; nesse caso, a prioridade é abrir um novo ciclo com a quantidade necessária de perguntas, não gravar uma alteração parcial. Se as respostas apenas esclarecem decisões já suficientes e nenhuma lacuna nova surgir, seguir normalmente para o incremento único.

## Limites incrementais

Na fase de aplicação, manter o contrato incremental: por padrão, no máximo 3 novos nós, 5 novas conexões e 1 subdesenho por ciclo. Se a resposta exigir uma expansão maior, explicar a expansão e pedir aprovação antes de gravar. Não repetir automaticamente outro ciclo.

Na fase de perguntas, não alterar o Draw para cumprir esses limites: o único artefato criado é a sessão de perguntas — dez na sessão inicial ou somente as necessárias em um acompanhamento.

## Perguntas da codebase

Perguntas marcadas com `@looper` pertencem exclusivamente ao `$draw-interaction`. O `$draw-improve` não responde, não preenche `answer`, não implementa produção e não remove marcadores `@looper`; deve preservá-los.

## Fluxo operacional

1. Conferir Git e preservar alterações existentes, sem usar o diff geral como fonte da decisão.
2. Executar `looper draw diff`; sem `--run-id`, comparar o estado atual com o último snapshot salvo por `looper log` e considerar somente alterações em `.looper/draws/*.json`.
3. Resolver o Draw pelo ID explícito, contexto atual, único Draw alterado ou único item disponível no índice; se houver mais de um candidato, perguntar qual usar.
4. Ler o índice, o Draw escolhido e apenas os subdesenhos necessários.
5. Na primeira fase, gerar e salvar a sessão com `looper draw improve --create`.
6. Na fase posterior, executar `looper draw improve --pending`, aplicar respostas e salvar o Draw.
7. Validar IDs numéricos, referências, condições, conexões, `draw_ref` e a árvore hierárquica.
8. Abrir `looper draw serve` quando a revisão visual for útil.
9. Registrar uma aplicação concluída como implementação:

   ```bash
   looper log "Melhora incrementalmente o desenho <draw-id>" --impl
   ```

## Handoff

O desenho não autoriza alteração direta de produção.

- `$test-application` deve ler o Draw aprovado, propor a cobertura completa e criar os testes aprovados em estado verificável.
- `$implement-backend` (e `$implement-frontend`) permanecem responsáveis pela produção nos loops específicos; a skill de teste não altera produção sem aprovação explícita.
- Não pular a etapa de testes nem tratar Draw aprovado como teste aprovado.

## Regras do ciclo interativo

Uma melhoria pode, quando autorizada e comprovada, criar ou alterar nós, conexões, grupos e referências no ponto arquitetural correto; não fica limitada a perguntas. Erros são condicionais (`se`/`ou`), validações antecedem efeitos e funcionalidades planejadas permanecem terminais no grupo `Não implementado`. Após aplicar, use `$test-application` para propor e validar a cobertura antes de produção e registre a alteração com `looper log`.

## Encerramento

Informar:

- Draw analisado e sessão de melhoria criada ou aplicada;
- diagnóstico: `melhorado` ou `Já está bom`;
- perguntas criadas, respostas consumidas e decisões resultantes;
- nós, relações, grupos ou subdesenhos adicionados/alterados, quando houver aplicação;
- o que ficou deliberadamente fora;
- comando ou URL para revisão visual;
- próxima opção: responder a sessão, revisar manualmente, chamar `$draw-improve` novamente, seguir com `$test-application` ou iniciar o loop de implementação apropriado.
