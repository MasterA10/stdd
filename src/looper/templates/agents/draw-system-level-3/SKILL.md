---
name: draw-system-level-3
description: "Cria o nível 3 de um Draw System no Looper como plano de execução de implementação: nós com descrição em médio nível no card e especificação técnica detalhada em code_tasks (endpoints, métodos HTTP, parâmetros, payloads e tarefas cirúrgicas de código), acessíveis via botão no viewer e extraíveis por looper draw context --code. Exige injeção do contexto global da aplicação, fim de instruções genéricas e Q&A técnico pré-preenchido sem metadados temporais de status."
---

# Draw System — Nível 3: Plano de Execução Cirúrgico (Tasks de Implementação)

## Responsabilidade e Função Formal

O Draw Nível 3 deixa de ser uma documentação passiva e assume a função formal de **plano de execução cirúrgico (análogo às tasks de um Spec Kit)**, focado exclusivamente no **caminho crítico de código**.

Ele é a ponte entre a View do nível 2 e a codebase real do sistema. Cada subfluxo corresponde a uma tela/nó do nível 2 que foi avaliado como necessitando de detalhamento. O nível 3 não é um fluxo genérico nem documentação contemplativa: ele começa pelas ações que a pessoa pode executar naquela tela e explica o comportamento iniciado por cada uma através de um passo a passo cirúrgico de implementação. O texto explica o comportamento em linguagem simples; o nó recebe `code_refs` de funções, handlers, services, use cases, endpoints e validadores reais quando encontrados.

Use esta skill somente depois de ler o nível 2, sua raiz e os descendentes relevantes. Não refaça a navegação global do nível 2 e não transforme o nível 3 em lista de nomes técnicos descontextualizada.

## Descrição em Médio Nível e Tasks de Código (`code_tasks`)

Para manter o visual do canvas legível e ao mesmo tempo fornecer todo o detalhamento técnico cirúrgico:

- **Descrição do Nó em Médio Nível**: A descrição padrão do nó (`description`) deve permanecer em **médio nível** — concisa, técnica e focada no objetivo funcional daquela etapa (ex.: "Valida as credenciais enviadas pelo cliente, confere o hash de senha no repositório de usuários e emite token JWT com permissões"). Não despeje blocos de código bruto, JSONs ou tabelas de endpoints diretamente no card do nó.
- **Inserção Obrigatória em `code_tasks`**: Cada nó de implementação que envolver endpoints, chamadas de API, webhooks ou passos técnicos específicos de código deve conter o array `code_tasks` preenchido. Cada task deve estruturar:
  - `title`: Resumo da ação técnica (ex.: "Endpoint de autenticação").
  - `method`: Método HTTP em maiúsculas (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
  - `uri`: Rota completa (ex.: `/api/v1/auth/login`).
  - `params`: Parâmetros de rota ou query esperados.
  - `payload`: Schema ou exemplo do payload da requisição.
  - `response`: Schema ou exemplo da resposta esperada com status code.
  - `details`: Instruções cirúrgicas de código para controller, services, repositórios e regras de negócio.
- **Botão e Modal no Viewer**: No visualizador (`looper draw serve`), os nós de Nível 3 exibem o botão **`Tasks de Código`**, que abre o modal interativo com todos os endpoints, payloads e detalhes técnicos para consulta e edição.
- **Consumo via `looper draw context`**:
  - A execução padrão `looper draw context` omite as tasks de código para manter o contexto estruturado limpo.
  - Para obter os detalhes cirúrgicos de código e endpoints, utilize a flag explícita: `looper draw context --code`.

## Injeção de Contexto e Especificação de Endpoints

Elimina-se qualquer abstração genérica nas instruções do agente, exigindo detalhamento técnico nos fluxos externos e integração com a arquitetura:

- **Fim das Instruções Genéricas**: Ações vagas como "envia mensagem", "notifica usuário" ou "chama API" passam a ser expressamente proibidas nos prompts de spec e nas descrições de nós do Nível 3. A diretriz exige a menção explícita da plataforma, provedor e canal (ex.: "envia mensagem via WhatsApp Cloud API", "dispara e-mail transacional via SendGrid API", "publica evento via RabbitMQ topic exchange").
- **Declaração Obrigatória de Endpoints**: Todas as rotas de backend, webhooks e APIs externas devem constar obrigatoriamente no Draw Nível 3 dentro de `code_tasks` com URI, método HTTP, parâmetros de rota (e query) e formato esperado de payload (campos obrigatórios, tipos e schema de request/response).
- **Consumo do Contexto Global**: O gerador do Draw Nível 3 deve obrigatoriamente referenciar o contexto completo da aplicação (loop context, metadados gerais do Draw System via `looper draw context`, fronteiras do Nível 1 e jornadas do Nível 2) para não gerar passos desconectados da arquitetura existente. Toda task de implementação deve se apoiar nas decisões globais confirmadas, modelos de dados e contratos transversais já definidos.
- **Validação Prévia com `$documentation-conventions`**: Antes de iniciar a montagem das tasks do Draw Nível 3, acione a skill `$documentation-conventions` para varrer os requisitos do Nível 2, consultar a documentação oficial de cada API/SDK e compilar as convenções do projeto com header em `.agents/conventions/`. Caso existam múltiplos caminhos técnicos sem definição clara na UI, pause e solicite definição humana explícita.

## Escopo Estrito de Implementação

O Draw Nível 3 deve conter **apenas o passo a passo sequencial e detalhado do que deve ser codificado**, focado exclusivamente no caminho crítico de código:

- **Fases de bootstrap de projeto desacopladas**: Fases de bootstrap de projeto e cenários de testes automatizados são desacoplados e alocados em seus próprios artefatos. A preparação de repositório, scaffolding, arquivos de configuração inicial e setup pertencem à task de bootstrap do backlog e comandos de setup da stack, não ao Nível 3.
- **Cenários de testes automatizados desacoplados**: Testes automatizados (unitários, integração ou Playwright) são desacoplados e alocados em seus próprios artefatos e suítes com `$test-application`. O Nível 3 não documenta cenários de testes, focando puramente no código a ser produzido.
- **Caminho crítico de código**: Cada nó representa uma etapa concreta e necessária da codificação de endpoints, controllers, models, services, validações, persistência e integrações.

## Proibição de Metadados de Status

O arquivo não deve registrar flags temporais como "tarefa ainda não implementada" ou "concluída":

- O controle de progresso pertence ao cursor/agente (como `looper backlog`); o documento deve permanecer puramente como instrução técnica e especificação.
- É estritamente proibido criar nós, grupos ou anotações com marcações temporais de ciclo de vida (ex.: "tarefa ainda não implementada", "em andamento" ou "concluída"). O documento descreve a especificação técnica perene do comportamento que deve ser implementado.

## Seção de Q&A Técnico Pré-Preenchida

O agente deve sintetizar as definições do Draw Nível 2 em pares de perguntas e respostas operacionais para cobrir casos de borda antes de iniciar o código:

- A partir das jornadas, nós e fluxos do Nível 2, antecipe pontos de decisão, condições limites, regras de exceção, concorrência e autorização.
- Sintetize essas definições em pares de perguntas e respostas (`questions`) já respondidas e operacionais no próprio subfluxo do Nível 3.
- Essas respostas servem como diretriz técnica direta para a codificação dos casos de borda, evitando suposições ou bloqueios durante o desenvolvimento.

## Especificação antes da implementação e rastreabilidade posterior

O nível 3 pode ser criado antes da implementação. Esse é o modo de especificação
planejada do Draw System: documentar o comportamento que será construído não exige
que já exista um símbolo na codebase. A ausência de código não é motivo para recusar
o desenho, mas também não autoriza inventar arquivos, endpoints, permissões ou regras
como se já fossem fatos implementados.

A obrigatoriedade de leitura do símbolo vale para validar uma tela já implementada,
não para impedir a especificação de uma tela planejada.

- Quando houver implementação, faça a leitura prévia do símbolo associado ao nó do
  nível 2 e extraia dela as regras, pré-condições, autorizações, validações,
  ramificações e saídas observadas. Use análise estática e busca no repositório para
  localizar e ler a implementação completa quando a referência estiver pendente.
- Quando o sistema ainda estiver no planejamento, modele o comportamento esperado a
  partir do requisito, das decisões aprovadas e das perguntas respondidas. Marque
  incertezas em `questions`, descreva-as como planejadas e mantenha `code_refs`
  vazios ou explicitamente pendentes; nunca crie um símbolo placeholder.
- O texto deve deixar distinguíveis os fatos implementados dos comportamentos
  planejados. Quando a regra ainda não estiver comprovada pelo código, não a
  apresente como evidência da implementação.
- Depois que a implementação da tela for concluída, associe os símbolos reais e
  releia-os para validar o desenho; o gate de rastreabilidade pertence a essa etapa,
  não à criação da especificação.

## Hierarquia e encapsulamento

Para cada tela, crie um desenho filho com `hierarchy.level: 3`, `role: "implementation"`, `parent_draw_ref` igual ao desenho de jornada, `parent_node_id` igual ao nó da tela e `root_draw_ref` igual à arquitetura. Na mesma alteração, preencha o `draw_ref` no nó pai. Toda cadeia deve resolver em `.looper/draws/`; não criar fluxos órfãos, referências inexistentes, pais duplicados ou continuidades inventadas.

O pai mostra apenas a cápsula da tela e aponta para o filho. O filho mostra somente o interior daquela fronteira. Nunca duplicar os passos internos no nível 2, nem a sequência global no nível 3. Alterar sempre o nó que mais se relaciona ao pedido, procurando primeiro uma cápsula existente.

## Cada ação da tela inicia um caminho

O subfluxo de uma tela deve começar com um conjunto de nós-gatilho: crie um nó inicial para cada botão, link, aba, filtro, envio, confirmação, cancelamento, retorno ou outra ação de usuário comprovada que a tela permita. A tela fornece o contexto, mas não substitui os nós das ações. Não esconder várias ações em um único nó chamado `Controller`, `Interação` ou equivalente.

Cada nó-gatilho deve estar conectado a outros nós por edges e iniciar uma sequência que explique o caso de uso correspondente: intenção, pré-condições, dados necessários, regra de negócio, autorização, validações, decisões, resultado, erro, bloqueio, retry, recuperação e saída. O primeiro nó de cada caminho é a ação do usuário; os nós seguintes explicam o que o sistema faz e o que a pessoa observa com precisão.

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

Toda informação variável da tela deve apontar para uma chave/caminho do JSON
único de mock fake e ser lida pela função/adaptador `get_mock_fake` (ou pelo
casing idiomático equivalente). No L2, descreva somente a chave, o formato
esperado e os estados que dependem dela; não associe o símbolo dessa função de
mock. No L3, durante a implementação do backend, associe os símbolos reais das
funções, controllers, models e integrações implementados. Não registre payloads
dinâmicos diretamente em cada componente nem trate um valor de exemplo como dado fixo.

Se a evidência não for suficiente para decidir um passo, registrar a pendência em `questions` ou fazer uma pergunta. Nunca preencher lacunas com um molde genérico ou inventar permissões.

## Critérios de análise estática do nível 3

Todo desenho filho com `hierarchy.level: 3` deve possuir **no mínimo quatro nós**. Cada nó desse subfluxo deve possuir `description` com **no mínimo 80 caracteres**, contando a string efetivamente gravada no JSON depois de remover espaços no início e no fim. A regra vale para entradas, ações, decisões, validações, estados de erro, sucesso, retry e recuperação quando existirem nesse nível. `label`, `title`, `questions`, `code_refs` e `edge.description` não contam para atingir o mínimo.

A análise estática deve emitir warnings, sem bloquear a criação ou o `looper test`, quando o subfluxo tiver menos de quatro nós (`draw.level3_min_nodes`) ou quando qualquer `description` estiver ausente, não for string ou tiver menos de 80 caracteres (`draw.level3_short_description`). O finding deve identificar o arquivo do desenho, o ID do nó quando aplicável, o valor observado, o limite e a evidência; não transformar uma lacuna desconhecida em aprovação.

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

Ao concluir a última fase, encerrar a sequência de especificação do Nível 3, consolidando o plano de execução cirúrgico da implementação.

## Associação incremental de símbolos

- Nas Fases 2 e 3 (e lotes adicionais), associar funções, handlers, services, use cases, endpoints, controllers e validadores de backend.
- Manter o texto do nível 3 em linguagem clara e objetiva, associando os símbolos técnicos reais (handlers, controllers, rotas, services, models e procedures) diretamente nos nós correspondentes via `code_refs` e `source_dependencies`.
- Usar `code_refs` no nó correspondente, com símbolo qualificado real, `identity` e `source_dependencies` somente quando a análise estática fornecer esses fatos.
- Não colocar símbolos em nó genérico. Se o símbolo ainda não puder ser encontrado, marcar a associação como pendente.

## Funcionalidades não implementadas e escopo de execução

Funcionalidade planejada continua terminal em um grupo específico `Não implementado` ou `Planejado` no nível 2, sem cor individual, filhos ou passos seguintes. Não criar subfluxo de nível 3 para folha não implementada e não fingir que existe comportamento.

No Nível 3, não devem existir nós ou grupos com metadados ou flags de status ("tarefa ainda não implementada" ou "concluída"). O subfluxo de Nível 3 só é aberto para o que faz parte do escopo de implementação e atua puramente como especificação do plano de execução do código.

## Convenção lógica de conexões

Toda seta usa `condition` numérico:

- `1` (`então`) é consequência certa e pode coexistir com um conjunto de `3` (`se`) ou de `2` (`ou`);
- `3` (`se`) é guarda possível. Se houver um `se`, deve haver pelo menos outro `se` correspondente na mesma origem;
- `2` (`ou`) é alternativa mutuamente exclusiva.

Nunca misture `se` com `ou` na mesma decisão. Nunca misture `ou` com `se`: são a mesma proibição vista pela outra direção. O `então` pode acompanhar uma família porque é a continuação inevitável. Se os caminhos puderem ocorrer juntos, use sequência ou paralelismo. Decisões são expressas pelas setas, não por `nodes[].type`.

## Execução, validação e handoff

Use `groups` para fronteiras, `flows` para caminhos temporais e `code_refs` nos nós técnicos. Não grave layout, cor, posição, data, HTML, CSS, JavaScript, `request.md` ou `scenarios.md`.

Para cada lote:

1. Ler pai, jornada, raiz e divisão de lotes. Para telas implementadas, realizar a leitura prévia e obrigatória do símbolo associado; para telas planejadas, ler os requisitos, decisões e perguntas do Draw e registrar `code_refs` como pendentes ou ausentes.
2. Criar cada JSON separadamente com IDs estáveis usando `looper draw create --data-json '<JSON>'`.
3. Validar nós, arestas, fluxos, condições, grupos, `draw_ref`, pais, raiz, terminais e os critérios estáticos de quatro nós e 80 caracteres.
4. Revisar no viewer com `looper draw serve`.
5. Conferir que cada ação de usuário comprovada possui um nó-gatilho conectado e que nenhum caminho foi reduzido a um fluxo genérico.
6. Entregar IDs, telas concluídas, regras cobertas, `code_refs` resolvidos/pendentes, folhas não implementadas, perguntas, limitações e próximo lote.

Ao alterar o desenho, registrar:

```bash
looper log "Detalha comportamento do sistema no nível 3" --type implementacao
```

Depois da última fase, entregar a árvore completa ao `$test-application`. A skill deve ler os JSONs diretamente, transformar caminhos implementados em um plano transversal e tratar folhas não implementadas como escopo ausente. `$implement-backend` e `$implement-frontend` seguem seus respectivos loops de produção.

## Regras do ciclo interativo

Erros são consequências condicionais (`se`/`ou`), nunca sequência inevitável; validações pertencem ao ponto que antecede a ação e não a um terminal genérico. Funcionalidades planejadas são terminais no grupo `Não implementado`. Execute `backlog test` antes de produção, uma task por interação, testes de integração com API, persistência, validações e efeitos reais, e `backlog complete` com o ID individual.
