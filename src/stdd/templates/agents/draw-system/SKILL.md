---
name: draw-system
description: Cria o desenho completo de um sistema no STDD Draw usando uma hierarquia de arquitetura, jornadas de usuário por papel, implementação e, quando necessário, relações com a codebase.
---

# Draw System

## Responsabilidade

Modelar um sistema inteiro como uma árvore navegável de desenhos JSON. O resultado deve permitir sair da arquitetura macro, entrar nas jornadas que cada tipo de usuário percorre e descer até a implementação do backend e da codebase quando esse detalhe for necessário.

Use esta skill quando o pedido falar de sistema, produto, aplicativo, arquitetura completa ou mapa de jornadas. Para um único comportamento isolado, use `$draw-feature`.

## Hierarquia obrigatória — mínimo 3 níveis

O sistema opera como uma **hierarquia estrita sem fluxos órfãos**: todo fluxo, etapa e subfluxo tem um pai. Subindo pela cadeia de pais, sempre se chega ao nível 1 (arquitetura). Todo desenho gerado por esta skill declara `hierarchy` e possui um pai explícito, exceto a raiz.

Os níveis são:

| Nível | Foco | Analogia MVC | O que pode aparecer |
| --- | --- | --- | --- |
| 1 — arquitetura | O que está **em volta** da codebase | — | aplicativo, linguagem, runtime, banco, cache, tipo de autenticação, sistemas externos, fronteiras e decisões macro — **não** explica comportamento |
| 2 — jornada (View) | Telas e navegação do aplicativo | **View** | telas, seções, áreas acessíveis, opções de navegação entre views, estados visíveis, caminhos entre telas — **95% de proximidade com o frontend real** |
| 3 — implementação (Controller) | Regras de negócio e como o backend atende | **Controller** | regras de negócio, validações, autorizações, orquestração de casos de uso, decisões de fluxo, API, persistência, integrações — a ponte entre view e model |
| 4 — codebase (baixo nível) | Linguagem técnica e de baixo nível | — | módulos, arquivos, símbolos, testes, dependências, contratos, queries, migrations; linguagem puramente técnica e de baixo nível |

**Regra fundamental de separação:**

- O **nível 1 não explica comportamento**. Ele não descreve o funcionamento do aplicativo. O que o usuário faz, regras de negócio, opções do cliente, sequência de telas — tudo isso pertence ao nível 2. O nível 1 é exclusivamente sobre as escolhas macro e o que está em torno da codebase: que linguagem, que banco, que sistema de cache, que tipo de autenticação, que provedores externos, que fronteiras existem.
- O **nível 2 é a View** — o mapa de telas e navegação do frontend. Representa as telas que existem, quais views o usuário pode acessar a partir de cada tela, e os caminhos de navegação entre elas. Ao olhar o nível 2, deve ser possível reconstruir 95% da interface do frontend. **A maioria dos nós do nível 2 deve apontar para um subfluxo no nível 3**, sempre que houver regra de negócio, decisão de fluxo ou detalhe de implementação relevante para explicar aquela tela/ação.
- O **nível 3 é o Controller** — a ponte entre a view e a implementação. Ele detalha as regras de negócio escolhidas, as decisões de fluxo, validações, autorizações e como o backend orquestra a resposta para cada ação do nível 2 **quando esse detalhamento for necessário**. Nem todo nó do nível 2 precisa de um subfluxo no nível 3: telas de transição, loading, confirmação ou outros nós sem lógica de negócio própria podem permanecer sem esse apontamento, desde que isso seja coerente com o que o nó faz.
- O **nível 4 explica em linguagem técnica e de baixo nível** — liga a implementação a fatos reais da codebase, com detalhes de código, queries, módulos e contratos. Sem inventar arquivos ou símbolos.

**Saltos entre níveis:** O nível 1 pode apontar diretamente para o nível 3 ou 4 quando o assunto for puramente técnico e não envolver jornada de usuário (exemplo: configuração de infraestrutura, pipeline de deploy, migração de banco). Mas para qualquer assunto que envolva comportamento do aplicativo, o nível 1 **deve** passar pelo nível 2 primeiro. A relação de pai é sempre obrigatória, independente do salto.

Um desenho deve usar uma estrutura equivalente a:

```json
"hierarchy": {
  "level": 2,
  "role": "journey",
  "parent_draw_ref": "system-architecture",
  "parent_node_id": 4,
  "root_draw_ref": "system-architecture"
}
```

A raiz usa `level: 1`, `role: "architecture"`, `parent_draw_ref: null`, `parent_node_id: null` e `root_draw_ref` igual ao próprio ID. Os papéis permitidos são `architecture`, `journey`, `implementation` e `codebase`.

## Árvore sem órfãos

- Todo desenho abaixo do nível 1 declara `parent_draw_ref` e `parent_node_id`.
- O desenho pai deve conter um único bloco-cápsula com `draw_ref` apontando para o filho.
- O `draw_ref` do pai, o `parent_draw_ref` do filho e o `root_draw_ref` devem formar uma cadeia resolvível em `.stdd/draws/`.
- **Todo fluxo tem um pai. Todo caminho, subindo pela hierarquia, chega ao nível 1.** Não pode existir um fluxo que começa em um desenho sem ancestral nem termina em um nó sem explicar seu estado.
- Um nível pode apontar diretamente para um nível mais baixo quando não houver detalhe útil intermediário, mas a relação de pai continua obrigatória. Para um sistema completo, o nível 1 deve possuir pelo menos um ponto de entrada para o nível 2.
- Não duplicar os passos do filho no pai. O pai mostra a responsabilidade encapsulada; o filho mostra somente o interior dessa fronteira.
- Ao alterar uma cadeia, ler o pai, o filho e os descendentes necessários. Nunca criar um `draw_ref` para um arquivo inexistente.

## Como desenhar cada nível

### Nível 1 — arquitetura (o que está em volta da codebase)

O nível 1 trata **exclusivamente de escolhas macro**. Ele mostra o que envolve a codebase, **não** como o aplicativo funciona.

Criar um desenho raiz `kind: "system"` com os grandes domínios e sistemas ao redor da codebase. Conteúdo típico do nível 1:

- Tipo do aplicativo (mobile, web, API, CLI, etc.)
- Linguagem e runtime
- Banco de dados (tipo, motor, estratégia de acesso)
- Cache (tipo, estratégia)
- Tipo de autenticação (OAuth, JWT, sessão, etc.)
- Mensageria (filas, tópicos, broker)
- Provedores e serviços externos
- Fronteiras de domínio e sistemas auxiliares
- Monitoramento, observabilidade, CI/CD

Usar `depends-on`, `calls`, `stores-in`, `publishes` e `consumes` para relações macro.

**O que NÃO pertence ao nível 1:** "cliente clica", validações de formulário, regras de aprovação, sequência de telas, opções do usuário, estados do aplicativo, fluxos de navegação, qualquer descrição de comportamento. Tudo isso vai para o nível 2.

Incluir um bloco como `Jornadas do usuário` ou equivalente com `draw_ref` para o desenho de nível 2. Esse é o ponto que conecta arquitetura a comportamento sem misturar as abstrações. A arquitetura deve deixar claro que cliente, administrador, operador, suporte ou serviço automatizado podem ser usuários diferentes do mesmo sistema.

Para assuntos puramente técnicos (infraestrutura, deploy, migração), o nível 1 pode apontar diretamente para um nível 3 ou 4, sem passar pelo nível 2.

### Nível 2 — jornadas do usuário / View (95% de proximidade com o frontend)

> **O nível 2 é o nível mais importante de todo o desenho.** Ele será, quase sempre, o maior e mais detalhado. Isso é esperado e desejável — não compactar.

O nível 2 é a **View do aplicativo**. Ele representa as **telas** que o usuário vê e a navegação entre elas. Ao ler o nível 2, o desenvolvedor deve conseguir reconstruir **95% da interface do frontend**. A única coisa que o nível 2 **não** representa são botões individuais — ele representa telas, views e as opções de navegação entre elas.

**Cada tela = um nó.** O nível 2 é um mapa de telas onde cada nó é uma tela ou view distinta. Quando o usuário clica em algo e vai para outra tela, essa outra tela é outro nó. Quando nessa nova tela ele tem opções que levam para mais telas, cada uma dessas telas é mais um nó. Por isso, o nível 2 tende a ter **muitos nós**, e isso é o comportamento correto. O entendimento de cada nó é simples — é apenas uma tela — então mesmo com muitos nós a leitura permanece clara.

**Exemplo concreto:** Considere o Instagram. A tela de feed é um nó. Os ícones da barra inferior (Home, Search, Reels, Shop, Profile) levam para telas diferentes — cada uma é outro nó. Ao entrar no perfil, há opções como Editar Perfil, Configurações, Posts salvos — cada uma dessas telas é mais um nó. Configurações abre uma lista de sub-telas (Privacidade, Segurança, Notificações...) — cada sub-tela é um nó adicional. O nível 2 mapeia **todas** essas telas, para cada role, exaustivamente.

**O que o nível 2 NÃO contém:**
- Rotas ou URLs (isso é detalhe de implementação, pertence ao nível 3)
- Cores, fontes, tamanhos, aparência visual ou layout CSS
- Botões individuais (o nó é a tela, não o botão)
- Regras de negócio detalhadas (isso vai para o nível 3)

**O que o nível 2 DEVE conter:**
- Cada **tela**, seção ou área acessível como um nó
- A partir de cada tela, **para quais outras telas/views** o usuário pode ir
- A sequência de navegação: o que vem primeiro, o que vem depois
- Os estados visíveis em cada tela: loading, sucesso, erro, vazio, bloqueado
- As condições de negócio que determinam **quais opções aparecem** em cada tela (sem detalhar a regra — apenas qual opção aparece ou não)
- Os caminhos de navegação: ida, volta, atalhos, redirecionamentos
- Todas as opções que o usuário tem em cada tela, não apenas o caminho feliz

Olhando o nível 2, a pessoa deve conseguir dizer "preciso criar esta tela, que leva para essas outras telas, com essas condições".

**Ponto(s) de entrada — poucos nós iniciais que façam sentido:**

O nível 2 deve evitar sair de muitos nós iniciais dispersos. O fluxo precisa ter uma raiz coerente:

- **Aplicativos mobile** geralmente partem de **um único nó inicial** (a tela de abertura ou home). A partir dali, o mapa se ramifica naturalmente.
- **Sites** tipicamente partem da **home page** como nó inicial. Podem ter um segundo ponto de entrada quando há uma área administrativa ou painel que não é acessível pelo fluxo normal do cliente (URL diferente, login separado).
- **Roles com fluxos isolados** (ex: administrador vs. cliente) podem justificar pontos de entrada diferentes quando não há interseção entre os caminhos. Nesse caso, cada role tem seu próprio nó inicial, mas o número total de raízes deve ser mínimo e cada uma deve representar um ponto de acesso real do sistema.

A regra geral: **o número de nós iniciais do nível 2 deve ser o menor possível e cada um deve corresponder a um ponto de acesso real do sistema.** Se o fluxo tem muitos nós iniciais sem justificativa, o mapa está fragmentado e precisa ser reorganizado.

**Regra de detalhamento — nós do nível 2 apontam para o nível 3 quando necessário:**

Todo nó (tela/view) do nível 2 **deve ser avaliado** para decidir se precisa de um `draw_ref` apontando para um subfluxo no nível 3. O nível 2 mostra **o que** o usuário vê; o nível 3 mostra **como** aquilo funciona por dentro — as regras de negócio escolhidas, decisões, validações, autorizações e orquestração do backend. Criar o apontamento quando a tela ou ação tiver uma regra de negócio associada, depender de uma decisão relevante ou exigir um detalhe de implementação para ser compreendida. Como regra prática, isso se aplica à grande maioria dos nós (aproximadamente 90%), mas não é uma obrigação mecânica para todos eles.

Telas de transição, loading, confirmação ou encaminhamento que apenas conectam estados/telas e não possuem lógica de negócio própria **podem não** apontar para o nível 3. Nesses casos, manter o nó no nível 2 com seu estado e destino claramente descritos. A ausência de um subfluxo só é válida quando o próprio nó não tiver decisão, regra ou implementação relevante a explicar; não usar essa exceção para omitir o detalhamento de uma tela que realmente possua comportamento.

**Separação por roles/papéis:**

Criar um desenho próprio que se pareça com a navegação e operação de cada usuário: entrada, áreas, opções disponíveis, retornos e estados observáveis. O nome deve ser `Jornadas do usuário`, nunca assumir que todo usuário é cliente. Antes dos fluxos, identificar os atores/papéis relevantes — por exemplo cliente e administrador — e registrar para cada um:

- objetivo e ponto de entrada;
- opções permitidas e ações proibidas;
- permissões, escopos, tenant ou contexto de acesso;
- dados e estados que consegue observar;
- caminhos de sucesso, erro, recuperação e encerramento.

**Caminhos separados para roles diferentes:** Quando não houver interseção entre as jornadas de dois papéis diferentes (cliente vs. administrador, por exemplo), criar caminhos completamente separados. Não misturar as jornadas de roles diferentes no mesmo fluxo se os passos, permissões ou objetivos forem distintos. Só compartilhar um fluxo quando a regra e o estado observável forem **realmente** os mesmos para todos os papéis; nesse caso, registrar os papéis autorizados na descrição ou em uma pergunta. Não reduzir duas jornadas diferentes a um único "usuário" genérico.

Se o papel de um usuário ainda não estiver confirmado, criar uma pergunta aberta ou de escolha; não inventar permissões.

**Funcionalidades não implementadas — nós terminais e grupo separado:**

Se uma opção ainda não foi implementada, ela é um **nó terminal** do caminho. Regras:
- Registrar o estado como `não implementado`
- **Não criar uma continuação fictícia** — o caminho para ali
- O nó não implementado nunca tem filhos, subfluxos ou passos seguintes; ele é um dos casos em que um nó do nível 2 não aponta para o nível 3, junto com nós implementados que não possuem lógica de negócio, decisão ou detalhe de implementação próprio (como telas de transição)
- Manter a pergunta/decisão pendente se for necessária
- Um caminho não implementado pode apontar para uma nota de produto ou trade-off, mas **nunca** para passos de execução que não existem

**Grupo de nós não implementados:** Quando o sistema tem telas que já foram implementadas e telas que ainda não foram, os nós não implementados **devem** ficar dentro de um `group` separado (ex: `"Não implementado"` ou `"Planejado"`). Isso torna visualmente claro no fluxo o que já existe e o que ainda precisa ser construído. As setas que levam a esses nós continuam saindo dos nós implementados normalmente — o grupo serve apenas para agrupar e destacar visualmente os nós que ainda não existem no sistema.


### Nível 3 — implementação / Controller (regras de negócio e orquestração)

O nível 3 é o **Controller** — a ponte entre o que o usuário vê (nível 2) e como o sistema executa. Cada subfluxo do nível 3 corresponde a um nó/tela do nível 2 que foi avaliado como necessitando de detalhamento e explica:

- **Regras de negócio escolhidas** para aquela tela/ação
- Entrada da API ou caso de uso correspondente
- Identidade do usuário, autenticação e autorização por papel/escopo/tenant
- Validações e suas mensagens de erro
- Orquestração do fluxo: decisões, condições, ramificações
- Transação, banco, cache, eventos, integrações
- Timeout, retry, compensação e falha segura
- Resposta formatada para o frontend

O nível 3 representa as **decisões de negócio e implementação** que estão por trás de cada tela. Ele não repete a navegação global do nível 2 — ele explica o interior de cada nó. Explicar quando cliente e administrador usam a mesma API com permissões diferentes ou quando percorrem casos de uso distintos.

Criar nível 4 somente quando a decisão depender da codebase real, de uma integração complexa, de rastreabilidade ou de uma refatoração com risco. Caso contrário, manter o nível 3 como folha técnica.

### Nível 4 — codebase (linguagem técnica de baixo nível)

O nível 4 explica em **linguagem puramente técnica e de baixo nível** como o código realiza o que o nível 3 descreve. Conteúdo típico:

- Módulos, classes, funções e seus `qualified_name`
- Queries SQL, migrations, schemas
- Contratos de interface (tipos, DTOs, protobuf)
- Dependências entre pacotes e serviços
- Testes e suas asserções
- `code_refs` comprovados por análise estática

O nível 4 não é lugar para suposições: se o símbolo ainda não puder ser resolvido, usar uma pergunta aberta ou marcar a associação como pendente. Ligar nós a `code_refs`, `qualified_name`, testes e dependências reais.

### Símbolos nos nós correspondentes — associação incremental por fase

A vinculação de nós a símbolos da codebase ocorre de forma **incremental em cada fase** do desenho, conforme o nível trabalhado:

- **Fase 1 (Nível 2 — Views):** Para cada nó de tela/view criado, buscar na codebase os componentes frontend correspondentes (ex: componentes React, Vue, Angular, páginas `.tsx`, `.jsx`, `.vue`, templates HTML, arquivos de view) e associá-los ao nó via `code_refs`.
- **Fase 2 (Nível 3 — Controller):** Para cada nó de implementação/controller criado, buscar e associar os símbolos de backend (controllers, rotas/endpoints, handlers, use cases, services, validadores) aos nós de nível 3 via `code_refs`.
- **Fase 3 (Nível 4 — Codebase):** Mapear e associar os símbolos técnicos de mais baixo nível (funções internas, procedimentos SQL, migrations, schemas, entidades, DTOs e testes) aos nós de nível 4 via `code_refs`.

Todo nó que representar um elemento já existente na codebase deve carregar a associação no próprio nó, usando `code_refs`. Cada referência deve usar o símbolo qualificado real retornado pela análise estática, além de `identity` e `source_dependencies` quando esses fatos estiverem disponíveis. Não colocar os símbolos em um nó genérico diferente nem apenas na descrição.

Nós abstratos que não correspondam diretamente a um símbolo existente não devem receber referências inventadas. Se o símbolo correspondente ainda não puder ser encontrado, marcar a associação como pendente.

Quando uma implementação atravessar uma RPC, incluir no nó o handler ou consumidor real da RPC e declarar a interface, contrato ou dependência remota em `source_dependencies`. Quando a lógica estiver em uma procedure, função, trigger ou view do banco, referenciar o símbolo SQL no nó correspondente e apontar para o arquivo de migration, schema ou SQL que contém a implementação.

## Fluxo de criação — execução faseada

O draw-system é executado em **fases**. Cada fase produz um ou dois níveis completos. Ao final de cada fase, o agente **para e pergunta** se o usuário quer continuar para a próxima fase. Não produzir todos os níveis de uma vez.

### Fase 1 — Arquitetura + Views (nível 1 + nível 2)

Esta é a fase inicial e a mais importante. O agente deve:

1. Inspecionar o pedido, a stack disponível, `.stdd/config.json`, desenhos existentes e o estado do Git.
2. Criar o desenho raiz de **nível 1** (arquitetura) com as escolhas macro.
3. Concentrar-se **exclusiva e exaustivamente** no **nível 2**: mapear todas as telas, todos os fluxos de interação, para cada role diferente (usuário, administrador, vendedor, etc.). Não compactar. Cada tela é um nó. Buscar a riqueza máxima de detalhes sobre quais telas existem e como se conectam.
4. Para cada nó de tela/view que já existir na codebase, consultar a análise estática e associar os componentes frontend (React, Vue, HTML, views, `.tsx`, `.jsx`, etc.) em `code_refs`.
5. Criar cada JSON separadamente em `.stdd/draws/`, começando pela raiz e mantendo IDs estáveis.
6. Em cada JSON, usar `groups` para fronteiras de responsabilidade e `flows` para caminhos temporais. Não gravar layout, cor, posição, data ou HTML.
7. Validar que todas as relações apontam para nós existentes e todas as referências hierárquicas resolvem para um pai.
8. Gravar cada desenho com `stdd draw create --data-json '<JSON>'` e conferir pelo viewer com `stdd draw serve`.
9. Revisar a árvore de telas, incluindo terminais não implementados, perguntas e trade-offs.
10. **Parar e perguntar ao usuário** se quer continuar para a Fase 2.

### Fase 2 — Controller / Regras de negócio (nível 3)

Só executar quando o usuário aprovar a continuação após a Fase 1. O agente deve:

1. Ler os desenhos de nível 2 já criados.
2. Para cada nó/tela do nível 2, avaliar se há regra de negócio, decisão de fluxo ou detalhe de implementação relevante. Criar o subfluxo de **nível 3** correspondente para os nós que precisarem desse detalhamento; manter sem subfluxo as telas de transição e outros nós sem lógica própria, registrando essa decisão quando não for óbvia.
3. Consultar os fatos da análise estática e associar os símbolos de backend (controllers, endpoints, rotas, handlers, services e use cases) em `code_refs`.
4. Gravar, validar e revisar.
5. **Parar e perguntar ao usuário** se quer continuar para a Fase 3.

### Fase 3 — Codebase / Baixo nível (nível 4)

Só executar quando o usuário aprovar a continuação após a Fase 2. O agente deve:

1. Ler os desenhos de nível 3 já criados.
2. Para cada nó que justifique, criar o subfluxo de **nível 4** com `code_refs`, `qualified_name`, queries, migrations, testes e dependências reais.
3. Consultar os fatos da análise estática e associar os símbolos de baixo nível (funções internas, queries SQL, migrations, DTOs e testes) no nó correspondente em `code_refs`.
4. Gravar, validar e revisar.

### Regras gerais de todas as fases

- Cada JSON é criado separadamente em `.stdd/draws/`.
- Usar `groups` para fronteiras de responsabilidade, `flows` para caminhos temporais e `code_refs` nos nós técnicos correspondentes.
- Não gravar layout, cor, posição, data ou HTML.
- Validar que todas as relações apontam para nós existentes.
- Gravar cada desenho com `stdd draw create --data-json '<JSON>'` e conferir pelo viewer com `stdd draw serve`.

## Condições e decisões

Usar `condition: 1` para sequência (`então`), `condition: 2` para alternativas exclusivas (`ou`) e `condition: 3` para guardas explícitas (`se`). Nunca misturar `se` e `ou` na mesma bifurcação. Se dois caminhos puderem ocorrer, modelar sequência ou paralelismo; não tratá-los como alternativa.

Pontos de decisão são expressos pelas setas. Não usar `nodes[].type` para criar decisões. Perguntas devem registrar decisões que ainda dependem do usuário, inclusive qual papel executa uma ação e qual permissão deve ser exigida; respostas preenchidas permanecem como histórico e não podem ser inventadas pelo agente.

## Encapsulamento e handoff

O JSON é a fonte de verdade. Não criar HTML, CSS, JavaScript, `request.md`, `scenarios.md` ou cópia intermediária. Não colocar detalhes do filho no pai.

Depois de criar ou revisar o desenho, entregar o ID da raiz e os IDs dos descendentes ao `$feature`. O Feature Agent deve ler a árvore relevante diretamente, transformar os caminhos implementados em testes e tratar folhas não implementadas como escopo ausente, não como comportamento existente. `$implement` só pode ser chamado depois de testes vermelhos aprovados para o comportamento escolhido.

Ao concluir, informar a raiz, a árvore de níveis criada, folhas ainda não implementadas, perguntas pendentes, trade-offs, arquivos alterados e o comando de revisão visual.

Quando houver alteração, registrar:

```bash
stdd log "Cria desenho hierárquico do sistema" --impl
```
