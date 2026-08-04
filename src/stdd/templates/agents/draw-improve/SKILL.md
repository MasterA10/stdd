---
name: draw-improve
description: Revisa e melhora incrementalmente desenhos existentes do STDD Draw, acrescentando apenas o detalhe arquitetural, caso de uso, risco ou trade-off mais relevante por ciclo. Usar ao invocar $draw-improve ou pedir para revisar, completar, evoluir ou avaliar uma arquitetura desenhada antes de transformá-la em feature ou implementação.
---

# Draw Improve

## Responsabilidade

Evoluir um desenho existente sem substituir a intenção do usuário nem explodir sua escala. Trabalhar em um ciclo curto, gravar um incremento coerente, apresentar o resultado para revisão e parar. Considerar `Já está bom` uma conclusão válida quando não existir lacuna arquitetural relevante.

Alterar somente o JSON lógico em `.stdd/draws/`. Não criar HTML individual, documentação Markdown paralela, código de produção ou testes durante a melhoria do desenho.

## Revisão da hierarquia do sistema

Quando o desenho possuir `hierarchy`, revisar a árvore e não apenas o arquivo aberto. Confirmar que o nível 1 contém somente decisões macro de arquitetura, que o nível 2 representa a navegação e as regras observáveis do cliente, que o nível 3 contém a implementação da jornada e que o nível 4 só aparece quando a codebase exigir rastreabilidade ou detalhe técnico.

Todo descendente deve declarar `parent_draw_ref`, `parent_node_id` e `root_draw_ref`, enquanto o pai aponta para ele com `draw_ref`. Uma melhoria não pode criar fluxo órfão. Folhas não implementadas devem permanecer terminais, sem continuação inventada. Se o problema estiver entre dois níveis, corrigir a cápsula e o vínculo pai-filho preservando o escopo de cada desenho.

## Resolver o desenho

Resolver `<draw-id>` nesta ordem:

1. ID informado explicitamente pelo usuário;
2. desenho mencionado ou aberto no contexto atual;
3. único JSON de desenho alterado na tarefa atual;
4. único item disponível em `.stdd/draws/index.json`.

Se houver mais de um candidato, perguntar qual desenho usar. Não escolher silenciosamente. Ler `.stdd/draws/<draw-id>.json` e abrir `draw_ref` somente quando o subfluxo for necessário para avaliar o ponto atual.

## Análise arquitetural

Avaliar no nível de sistemas, domínios, atores, responsabilidades, decisões e fluxos. Procurar primeiro a maior lacuna entre:

- caminho principal incompleto;
- falha ou recuperação relevante ausente;
- fronteira de responsabilidade ambígua;
- dependência ou acoplamento arriscado;
- decisão sem condição, consequência ou alternativa;
- segurança, autorização ou isolamento arquiteturalmente relevante;
- observabilidade necessária para operar o fluxo;
- caso de uso importante não representado;
- parte complexa que merece um único `draw_ref` (respeitando a hierarquia de funções: o fluxo pai mantém a cápsula abstrata e o subfluxo isola os passos detalhados internos, sem duplicar etapas no pai).
- vínculo hierárquico ausente, `draw_ref` quebrado, pai que duplica o filho ou nível que mistura arquitetura, jornada e implementação;
- caminho de jornada não implementado que continua para passos fictícios em vez de terminar explicitamente.

### Revisão global obrigatória

Cada ciclo deve revisar o desenho inteiro, não apenas os nós ou relações inseridos no ciclo anterior. Ler e avaliar todos os nós, relações, grupos, fluxos, `draw_ref`, perguntas e decisões respondidas. Corrigir descrições vagas, caminhos duplicados, responsabilidades sobrepostas, ramos que bypassam decisões, nós órfãos e inconsistências entre o fluxo principal e subfluxos. É permitido alterar nós e relações existentes quando a correção for necessária para deixar o desenho coerente; preservar IDs e significado sempre que não houver inconsistência objetiva.

Organizar os nós em grupos arquiteturais coerentes. Criar ou ajustar `groups`, atribuir `group` a todos os nós quando o agrupamento trouxer clareza e verificar que os grupos não misturam responsabilidades sem justificativa. O resultado deve comunicar a arquitetura como um todo, e não apenas acumular detalhes.

Quando uma decisão depender do usuário, adicionar uma pergunta opcional ao nó responsável em vez de adivinhar. Usar `questions` com `type` `choice`, `boolean` ou `open`; contar como pendente e sem resposta somente quando `answer` for `null` ou vazio. Manter perguntas respondidas no JSON para formar histórico e tratar respostas como decisões do usuário nas próximas rodadas.

### Perguntas endereçadas ao agente

O marcador `@STDD` no `prompt` identifica uma pergunta feita explicitamente ao agente. Só agir sobre uma pergunta quando as duas condições forem verdadeiras: o `prompt` contém `@STDD` e `answer` está ausente, `null` ou é uma string vazia. Nesse caso, responder com base nos fatos e no desenho revisado, gravar a resposta no próprio `answer` e continuar o ciclo apenas se a resposta revelar uma melhoria coerente.

Perguntas sem `@STDD` pertencem ao usuário ou a um revisor humano: não responder, não preencher e não transformar em ação automática. Se o usuário remover `@STDD`, deixar de tratar a pergunta como pendência do agente. Se `answer` já estiver preenchido, considerar a decisão encerrada e não fazer nada; `false` e `0` são respostas válidas e não significam ausência de resposta.

Não detalhar classes, funções, métodos, chamadas internas triviais, campos ou passos de implementação. Um bom desenho de alto nível pode permanecer pequeno. Ao criar um subfluxo (`draw_ref`), garanta separação estrita de escopo: o que está no subfluxo não deve ser duplicado no fluxo principal.

## Contrato incremental

Executar um ciclo por invocação. Por padrão, um ciclo pode adicionar no máximo 3 novos nós, 5 novas conexões, 1 subdesenho e deve criar ou refinar pelo menos 5 perguntas arquiteturais relevantes. Distribuir as perguntas pelos nós responsáveis, evitando perguntas genéricas duplicadas. Em toda pergunta `choice`, manter o enunciado e as opções neutros, sem inserir sugestões no JSON. Apresentar a sugestão arquitetural separadamente na resposta ao usuário, identificando a pergunta e a opção recomendada, sem registrar a resposta por conta própria. Alterações menores são preferíveis nos nós e relações, mas a revisão global pode corrigir qualquer elemento inconsistente. Se a melhoria coerente exigir mais de 3 nós, 5 relações ou 1 subdesenho, explicar a expansão e pedir aprovação antes de gravá-la.

Preservar IDs e significado dos elementos existentes. Não remover, renomear ou redirecionar elementos do usuário sem corrigir uma inconsistência objetiva; quando isso ocorrer, declarar a correção no encerramento.

Não repetir automaticamente outro ciclo. Depois de gravar a melhoria, parar para revisão do usuário. Uma nova invocação de `$draw-improve` inicia o próximo ciclo sobre o JSON já revisado.

Se o desenho já comunicar responsabilidades, fluxo principal, falhas relevantes e trade-offs suficientes para a decisão atual, não alterar o arquivo. Responder `Já está bom` e apresentar os sinais que sustentam essa conclusão.

## Fluxo de melhoria

1. Conferir Git e preservar alterações existentes, sem usar o diff geral como fonte da melhoria.
2. Executar `stdd draw diff`; sem `--run-id`, o comando compara o estado atual com o último snapshot salvo por `stdd log` e mostra somente alterações em `.stdd/draws/*.json`, excluindo `.stdd/draws/index.json`.
3. Para um ponto específico, executar `stdd draw diff --run-id <run-id>`. Nunca usar GitHub, pull request, `git diff` ou o snapshot geral da codebase para decidir o que mudou no desenho.
4. Ler o índice, o JSON escolhido e apenas os subdesenhos necessários.
5. Transformar o diff de Draws em revisão: identificar o que mudou, verificar coerência com a arquitetura inteira, responder somente às perguntas marcadas com `@STDD` e sem `answer`, gravar essas respostas no JSON, fazer perguntas humanas sem o marcador permanecerem abertas e apresentar sugestões de correção separadas.
6. Validar IDs numéricos internos, referências, condições, integridade das conexões e a árvore `hierarchy`/`draw_ref` sem órfãos.
7. Identificar a maior lacuna arquitetural e escolher um único incremento.
8. Atualizar o JSON preservando seu `id` descritivo e usando `condition`: `1` para `então`, `2` para `ou` e `3` para `se`.
9. Manter posição, cor, dimensão, data e estilo fora do JSON.
10. Gravar pelo contrato existente, preferencialmente com:

```bash
stdd draw create --data-json '<JSON_COMPLETO_ATUALIZADO>'
```

11. Validar o desenho gerado, abrir com `stdd draw serve` quando a revisão visual for útil e registrar o trabalho como implementação do desenho.
12. Informar o incremento, as mudanças encontradas no diff salvo, as perguntas e sugestões, o que ficou deliberadamente fora e pedir revisão. Encerrar o ciclo.

## Handoff para feature e implementação

O desenho não autoriza alteração direta de produção.

- Se o usuário disser apenas `$feature`, resolver o desenho pelo contexto e entregar seu ID ao Feature Agent. O Feature Agent deve ler `.stdd/draws/<draw-id>.json`, criar os testes executáveis e confirmar o estado vermelho pelo motivo esperado. Não exigir que o usuário repita a descrição já presente no desenho.
- Se o usuário disser `$implement` ou pedir para implementar o desenho, executar primeiro o contrato de `$feature`. Somente depois de existirem testes adequados em estado vermelho, seguir o contrato do Implement Agent para obter verde.
- Não pular a etapa de feature, não criar produção antes dos testes e não tratar desenho aprovado como teste aprovado.
- Se o desenho for ambíguo a ponto de produzir contratos incompatíveis, pedir a menor decisão necessária antes da feature.

## Encerramento de cada ciclo

Informar:

- desenho analisado;
- diagnóstico: `melhorado` ou `Já está bom`;
- nós, relações ou subdesenhos adicionados/alterados;
- risco, caso de uso ou decisão esclarecida;
- detalhes deliberadamente não adicionados;
- comando ou URL para revisão visual;
- próxima opção: revisar manualmente, chamar `$draw-improve` novamente, seguir com `$feature` ou iniciar `$implement` pela etapa de feature.

Quando houver alteração, registrar somente o tipo correspondente:

```bash
stdd log "Melhora incrementalmente o desenho <draw-id>" --impl
```
