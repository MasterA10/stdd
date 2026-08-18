---
name: draw-system-level-3
description: "Cria o nível 3 de um Draw System no STDD: o Controller detalhado de cada tela ou nó, explicando em linguagem simples todas as funcionalidades, decisões, regras e estados de ponta a ponta. Use depois de draw-system-level-2 e execute em dois ou mais lotes completos, ampliando o número de fases quando houver muitas telas."
---

# Draw System — Nível 3: Comportamento / Controller

## Responsabilidade

Ser a ponte entre a View do nível 2 e a codebase do nível 4. Cada subfluxo corresponde a uma tela/nó do nível 2 que foi avaliado como necessitando de detalhamento. O nível 3 não é um fluxo genérico: ele começa pelas ações que a pessoa pode executar naquela tela e explica o comportamento iniciado por cada uma. O texto explica o comportamento em linguagem simples; o nó recebe `code_refs` de funções, handlers, services, use cases, endpoints e validadores reais quando encontrados.

Use esta skill somente depois de ler o nível 2, sua raiz e os descendentes relevantes. Não refaça a navegação global do nível 2, não transforme o nível 3 em lista de nomes técnicos e não abra nível 4 automaticamente.

## Obrigatoriedade de leitura do símbolo na codebase

O sucesso desta etapa depende obrigatoriamente da leitura do símbolo associado ao nó do nível 2 e da sua referência na codebase.

- **Nenhum fluxo pode ser criado sem a leitura prévia do símbolo correspondente da implementação.**
- Para explicar o fluxo de um nó vindo do nível 2 e criar o subfluxo de nível 3 para ele, o agente deve obrigatoriamente ler o símbolo e a referência dele no código-fonte.
- Não é para implementar ou criar nenhum fluxo sem reler a implementação do símbolo correspondente.
- Caso a referência ou o símbolo do nó do nível 2 ainda esteja pendente, utilize a análise estática e a busca no repositório para localizar a função, classe, handler ou service correspondente na codebase e faça sua leitura completa antes de desenhar o subfluxo.
- O detalhamento das regras de negócio, pré-condições, autorizações, validações, ramificações e saídas do nível 3 deve ser extraído diretamente da leitura do código do símbolo.


## Hierarquia e encapsulamento

Para cada tela, crie um desenho filho com `hierarchy.level: 3`, `role: "implementation"`, `parent_draw_ref` igual ao desenho de jornada, `parent_node_id` igual ao nó da tela e `root_draw_ref` igual à arquitetura. Na mesma alteração, preencha o `draw_ref` no nó pai. Toda cadeia deve resolver em `.stdd/draws/`; não criar fluxos órfãos, referências inexistentes, pais duplicados ou continuidades inventadas.

O pai mostra apenas a cápsula da tela e aponta para o filho. O filho mostra somente o interior daquela fronteira. Nunca duplicar os passos internos no nível 2, nem a sequência global no nível 3. Alterar sempre o nó que mais se relaciona ao pedido, procurando primeiro uma cápsula existente.

## Cada ação da tela inicia um caminho

O subfluxo de uma tela deve começar com um conjunto de nós-gatilho: crie um nó inicial para cada botão, link, aba, filtro, envio, confirmação, cancelamento, retorno ou outra ação de usuário comprovada que a tela permita. A tela fornece o contexto, mas não substitui os nós das ações. Não esconder várias ações em um único nó chamado `Controller`, `Interação` ou equivalente.

Cada nó-gatilho deve estar conectado a outros nós por edges e iniciar uma sequência que explique o caso de uso correspondente: intenção, pré-condições, dados necessários, regra de negócio, autorização, validações, decisões, resultado, erro, bloqueio, retry, recuperação e saída. O primeiro nó de cada caminho é a ação do usuário; os nós seguintes explicam o que o sistema faz e o que a pessoa observa, sem antecipar detalhes técnicos do nível 4.

Quando ações diferentes tiverem exatamente a mesma regra e o mesmo comportamento comprovado, elas podem convergir para um nó compartilhado depois de seus gatilhos. A convergência não autoriza apagar os gatilhos nem tratar ações diferentes como uma única ação. Quando os comportamentos divergirem, manter caminhos separados. Eventos automáticos, loading, atualização, timeout e reconexão podem aparecer como estados ou consequências do caminho acionado, mas não substituem as ações de entrada da tela.

## Detalhamento obrigatório de ponta a ponta

O nível 3 deve explicar **tudo o que é possível fazer naquela tela ou nó**, do início ao fim, quando a funcionalidade existir e houver evidência:

- inventário completo das ações de usuário comprovadas e um nó-gatilho para cada ação;
- o que a pessoa ou o sistema está tentando fazer;
- entrada, pré-condições, dados carregados e contexto do papel;
- opções e ações disponíveis, inclusive as que ficam ocultas por permissão;
- regras de negócio e condições que determinam o resultado;
- quem pode executar a ação, por papel, permissão, tenant e contexto;
- validações e mensagens de erro compreensíveis;
- decisões, ramificações, sucesso, falha segura e recuperação;
- efeitos colaterais, persistência, eventos e dependências descritas por responsabilidade;
- estados de vazio, bloqueio, loading, timeout, nova tentativa e compensação;
- resultado exibido à pessoa ou entregue ao próximo passo;
- atualização, retorno, encerramento e todos os caminhos de saída da tela.

Para uma tela dinâmica, como chat, marketplace, feed, busca, carrinho ou painel em tempo real, não trate uma tela dinâmica como sequência estática e não escreva apenas uma sequência linear. Explicar os ciclos e variações que a própria tela permite: carregamento incremental, atualização, filtros, paginação, concorrência, mensagens/eventos, envio e recebimento, indisponibilidade, reconexão, retry, consistência e recuperação. Associar tudo à tela correspondente e não espalhar a lógica por um nó genérico.

Se a evidência não for suficiente para decidir um passo, registrar a pendência em `questions` ou fazer uma pergunta. Nunca preencher lacunas com um molde genérico ou inventar permissões.

## Critérios de análise estática do nível 3

Todo desenho filho com `hierarchy.level: 3` deve possuir **no mínimo quatro nós**. Cada nó desse subfluxo deve possuir `description` com **no mínimo 80 caracteres**, contando a string efetivamente gravada no JSON depois de remover espaços no início e no fim. A regra vale para entradas, ações, decisões, validações, estados de erro, sucesso, retry e recuperação quando existirem nesse nível. `label`, `title`, `questions`, `code_refs` e `edge.description` não contam para atingir o mínimo.

A análise estática deve emitir warnings, sem bloquear a criação ou o `stdd test`, quando o subfluxo tiver menos de quatro nós (`draw.level3_min_nodes`) ou quando qualquer `description` estiver ausente, não for string ou tiver menos de 80 caracteres (`draw.level3_short_description`). O finding deve identificar o arquivo do desenho, o ID do nó quando aplicável, o valor observado, o limite e a evidência; não transformar uma lacuna desconhecida em aprovação.

A descrição não pode ser preenchida com repetição, adjetivos vazios ou texto decorativo. Os 80 caracteres devem explicar a responsabilidade daquele nó e, conforme o caso, sua intenção, papel autorizado, entrada, regra, condição, estado observável, efeito, resultado, falha ou dependência. Em uma tela dinâmica, escrever o contexto do ciclo específico — por exemplo atualização, paginação, concorrência, evento, reconexão ou indisponibilidade — no nó correspondente. Quando a evidência não sustentar esse nível de detalhe, registrar a lacuna em `questions` e manter a descrição factual; nunca inventar comportamento só para alcançar a contagem.

## Granularidade sem molde fixo

Não impor quantidade exata de nós, quatro nós por padrão ou simetria entre subfluxos. O mínimo de quatro nós é um critério de análise estática, não um molde: derivar os nós de ações, decisões, validações, estados, integrações e resultados reais. Não criar passos decorativos para evitar o warning; registrar a insuficiência e manter a descrição factual.

Preservar caminhos de sucesso, validação, autorização, vazio, timeout, nova tentativa, erro e recuperação quando forem possíveis no caso.

## Fases e lotes do nível 3

O nível 3 continua dividido em fases para permitir detalhe real:

### Fase 2 — primeiro lote do Controller

Só executar após aprovação da continuação do nível 2. Ler todos os nós elegíveis, inventariar os subfluxos e separar lotes completos, aproximadamente equilibrados, respeitando papéis, fronteiras e dependências. O primeiro lote não pode truncar uma tela nem ser escolhido por corte arbitrário.

Criar somente esse lote. Para cada tela, primeiro inventariar todas as ações de usuário e criar seus nós-gatilho; depois explicar o comportamento completo de cada caminho com a quantidade necessária de nós, incluindo regras, autorizações, validações, resultados e falhas. Consultar análise estática e associar handlers, controllers, endpoints, rotas, services, use cases e validadores nos próprios nós. Gravar, validar, revisar e pare e solicite confirmação antes de perguntar se o usuário quer continuar.

### Fase 3 — segundo lote e fechamento do Controller

Só executar após aprovação da Fase 2. Ler a divisão dos lotes e os subfluxos já criados. Criar somente o segundo lote, mantendo o detalhamento orientado pelas ações reais de cada tela e sem copiar a forma dos subfluxos da primeira metade. Associar símbolos de backend nos nós correspondentes.

Ao fechar, revisar o nível 3 completo: todos os nós elegíveis foram avaliados, cada tela tem uma entrada para cada ação comprovada, cada ação está ligada ao seu comportamento ponta a ponta, não há quantidade fixa de nós, as ramificações relevantes estão representadas e não existem referências órfãs, pais duplicados ou continuidades inventadas.

### Lotes adicionais

Se houver muitas telas, alta complexidade, muitos papéis ou dependências que tornem dois lotes insuficientes, dividir em três ou mais fases. A divisão deve ser explícita e estável, por lotes completos, e cada fase deve parar e pedir autorização antes da próxima. Nunca dividir um subfluxo no meio nem esconder detalhe na fronteira entre lotes.

Ao concluir a última fase, encerrar a sequência automática. Informar que `$draw-system-level-4` pode ser aberto sob demanda para rastreabilidade técnica.

## Associação incremental de símbolos

- Nas Fases 2 e 3 (e lotes adicionais), associar funções, handlers, services, use cases, endpoints, controllers e validadores de backend.
- Manter o texto do nível 3 em linguagem simples. Se mencionar procedure, função externa, RPC, tabela, rota, classe, arquivo ou símbolo, mover o detalhe técnico para o nível 4 quando essa camada for aberta.
- Usar `code_refs` no nó correspondente, com símbolo qualificado real, `identity` e `source_dependencies` somente quando a análise estática fornecer esses fatos.
- Não colocar símbolos em nó genérico. Se o símbolo ainda não puder ser encontrado, marcar a associação como pendente.

## Funcionalidades não implementadas

Funcionalidade planejada continua terminal em um grupo específico `Não implementado` ou `Planejado`, sem cor individual, filhos ou passos seguintes. Não criar subfluxo de nível 3 para folha não implementada e não fingir que existe comportamento.

## Convenção lógica de conexões

Toda seta usa `condition` numérico:

- `1` (`então`) é consequência certa e pode coexistir com um conjunto de `3` (`se`) ou de `2` (`ou`);
- `3` (`se`) é guarda possível. Se houver um `se`, deve haver pelo menos outro `se` correspondente na mesma origem;
- `2` (`ou`) é alternativa mutuamente exclusiva.

Nunca misture `se` com `ou` na mesma decisão. Nunca misture `ou` com `se`: são a mesma proibição vista pela outra direção. O `então` pode acompanhar uma família porque é a continuação inevitável. Se os caminhos puderem ocorrer juntos, use sequência ou paralelismo. Decisões são expressas pelas setas, não por `nodes[].type`.

## Execução, validação e handoff

Use `groups` para fronteiras, `flows` para caminhos temporais e `code_refs` nos nós técnicos. Não grave layout, cor, posição, data, HTML, CSS, JavaScript, `request.md` ou `scenarios.md`.

Para cada lote:

1. Ler pai, jornada, raiz, divisão de lotes, descendentes necessários e realizar a leitura prévia e obrigatória do símbolo associado a cada nó na codebase.
2. Criar cada JSON separadamente com IDs estáveis usando `stdd draw create --data-json '<JSON>'`.
3. Validar nós, arestas, fluxos, condições, grupos, `draw_ref`, pais, raiz, terminais e os critérios estáticos de quatro nós e 80 caracteres.
4. Revisar no viewer com `stdd draw serve`.
5. Conferir que cada ação de usuário comprovada possui um nó-gatilho conectado e que nenhum caminho foi reduzido a um fluxo genérico.
6. Entregar IDs, telas concluídas, regras cobertas, `code_refs` resolvidos/pendentes, folhas não implementadas, perguntas, limitações e próximo lote.

Ao alterar o desenho, registrar:

```bash
stdd log "Detalha comportamento do sistema no nível 3" --type implementacao
```

Depois da última fase, entregar a árvore completa ao `$create-tests-backlog`. O Create Tests Backlog Agent deve ler os JSONs diretamente, transformar caminhos implementados em testes e tratar folhas não implementadas como escopo ausente. `$implement-backlog` só pode ser chamado depois de testes vermelhos aprovados.

## Regras do ciclo interativo

Erros são consequências condicionais (`se`/`ou`), nunca sequência inevitável; validações pertencem ao ponto que antecede a ação e não a um terminal genérico. Funcionalidades planejadas são terminais no grupo `Não implementado`. Execute `backlog test` antes de produção, uma task por interação, testes de integração com API, persistência, validações e efeitos reais, e `backlog complete` com o ID individual.
