---
name: draw-improve
description: Identifica lacunas arquiteturais em um Draw existente por meio de dez perguntas e aplica as respostas em um ciclo posterior, preservando o JSON do fluxo enquanto as perguntas estão abertas.
---

# Draw Improve

## Responsabilidade

O `$draw-improve` trabalha em duas fases explícitas:

1. **Perguntar:** revisar o Draw inteiro, criar exatamente dez perguntas arquiteturais em uma sessão separada de `.looper/improvements/` e parar para a resposta humana. Nesta fase não alterar `.looper/draws/<draw-id>.json`, não criar nós e não criar conexões.
2. **Aplicar:** em uma nova invocação, localizar sessões completas com `looper draw improve --pending`, ler as respostas, revisar novamente o Draw associado e aplicar somente o próximo incremento coerente. Depois de salvar o Draw, marcar a sessão como `applied`.

O ciclo só termina depois de apresentar o resultado e pedir revisão. `Já está bom` continua sendo uma conclusão válida quando não houver lacuna relevante, mas a fase de perguntas deve existir sempre que uma decisão arquitetural depender da pessoa. Uma nova invocação inicia um ciclo posterior; não repetir automaticamente o ciclo atual.

## Sessão de perguntas

Uma sessão é um JSON separado em `.looper/improvements/<improvement-id>.json`, associado por `draw_id`. Ela não é um subdraw, não pertence à hierarquia arquitetural e nunca deve ser gravada dentro do JSON do fluxo. O campo `questions` guarda as respostas, e o status `applied` identifica o histórico imutável.

A sessão deve possuir exatamente dez perguntas. Cada pergunta usa um destes tipos:

- `boolean`: sim ou não;
- `choice`: de duas a quatro opções neutras, exibidas como A, B, C ou D;
- `open`: resposta curta em texto.

Todas começam com `answer: null`, isto é, sem resposta. Não registrar recomendações, respostas presumidas ou perguntas para investigação da codebase. As perguntas devem ser específicas, independentes e capazes de alterar arquitetura, casos de uso, riscos, responsabilidades, conexões, grupos ou fluxos.

Criar a sessão pelo contrato oficial:

```bash
looper draw improve --create --data-json '<JSON_DA_SESSAO>'
```

Depois, orientar a pessoa a abrir o viewer, responder as dez perguntas e salvar. A UI salva somente `.looper/improvements/`; o Draw continua intacto.

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

Usar somente sessões `ready`, isto é, com as dez respostas válidas. Nunca aplicar uma sessão `draft` ou inferir resposta ausente. O comando entrega o `draw_id`, o arquivo da sessão, as perguntas e as respostas.

Para cada sessão pronta:

1. Ler o JSON atual do Draw pelo `draw_id`; não usar uma cópia antiga da sessão como fonte para substituir o Draw.
2. Interpretar as respostas como decisões explícitas da pessoa.
3. Fazer uma única melhoria coerente, podendo alterar nós, relações, grupos, flows ou um subdraw quando isso for consequência direta das respostas.
4. Preservar IDs e significado existentes salvo quando houver inconsistência objetiva.
5. Usar `condition: 1` para `então`, `condition: 2` para `ou` e `condition: 3` para `se`.
6. Persistir o Draw completo com:

   ```bash
   looper draw create --data-json '<JSON_COMPLETO_ATUALIZADO>'
   ```

7. Somente depois de o Draw ser salvo com sucesso, executar:

   ```bash
   looper draw improve --mark-applied --id <improvement-id>
   ```

Uma sessão `applied` é histórica e imutável. Não reaplicá-la nem apagar suas perguntas e respostas.

## Limites incrementais

Na fase de aplicação, manter o contrato incremental: por padrão, no máximo 3 novos nós, 5 novas conexões e 1 subdesenho por ciclo. Se a resposta exigir uma expansão maior, explicar a expansão e pedir aprovação antes de gravar. Não repetir automaticamente outro ciclo.

Na fase de perguntas, não alterar o Draw para cumprir esses limites: o único artefato criado é a sessão de dez perguntas.

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

- `$create-tests` deve ler o Draw aprovado e criar testes executáveis em estado vermelho pelo motivo esperado.
- `$implement` deve executar primeiro o contrato de `$create-tests` e somente depois alterar produção.
- Não pular a etapa de testes nem tratar Draw aprovado como teste aprovado.

## Encerramento

Informar:

- Draw analisado e sessão de melhoria criada ou aplicada;
- diagnóstico: `melhorado` ou `Já está bom`;
- perguntas criadas, respostas consumidas e decisões resultantes;
- nós, relações, grupos ou subdesenhos adicionados/alterados, quando houver aplicação;
- o que ficou deliberadamente fora;
- comando ou URL para revisão visual;
- próxima opção: responder a sessão, revisar manualmente, chamar `$draw-improve` novamente, seguir com `$create-tests` ou iniciar `$implement` pela etapa de create-tests.
