---
name: draw-system
description: Cria o desenho completo de um sistema no STDD Draw usando uma hierarquia de arquitetura, jornadas de usuário por papel, implementação e, quando necessário, relações com a codebase.
---

# Draw System

## Responsabilidade

Modelar um sistema inteiro como uma árvore navegável de desenhos JSON. O resultado deve permitir sair da arquitetura macro, entrar nas jornadas que cada tipo de usuário percorre e descer até a implementação do backend e da codebase quando esse detalhe for necessário.

Use esta skill quando o pedido falar de sistema, produto, aplicativo, arquitetura completa ou mapa de jornadas. Para um único comportamento isolado, use `$draw-feature`.

## Hierarquia obrigatória

Todo desenho gerado por esta skill declara `hierarchy` e possui um pai explícito, exceto a raiz. Os níveis são:

| Nível | Foco | O que pode aparecer |
| --- | --- | --- |
| 1 — arquitetura | O que envolve a codebase | aplicativo, linguagem, runtime, banco, cache, autenticação, sistemas externos, fronteiras e decisões macro |
| 2 — jornada | O que o cliente pode fazer | navegação do frontend, opções, estados visíveis, regras de negócio e caminhos de sucesso, erro e recuperação |
| 3 — implementação | Como uma jornada é atendida | API, caso de uso, validação, autorização, persistência, filas, eventos, integrações, retries e falha segura |
| 4 — codebase | Onde e como o código realiza isso | módulos, arquivos, símbolos, testes, dependências e contratos; usar somente quando a complexidade justificar |

O nível 1 não explica o comportamento do aplicativo. Funcionamento, regras de negócio e opções do cliente pertencem ao nível 2. O nível 3 explica a mecânica técnica de um caminho do nível 2. O nível 4 liga a implementação a fatos reais da codebase, sem inventar arquivos ou símbolos.

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
- Todo fluxo, etapa e subfluxo tem um pai. Um caminho não pode começar em um desenho sem ancestral nem terminar em um nó sem explicar seu estado.
- Um nível pode apontar diretamente para um nível mais baixo quando não houver detalhe útil intermediário, mas a relação de pai continua obrigatória. Para um sistema completo, o nível 1 deve possuir pelo menos um ponto de entrada para o nível 2.
- Não duplicar os passos do filho no pai. O pai mostra a responsabilidade encapsulada; o filho mostra somente o interior dessa fronteira.
- Ao alterar uma cadeia, ler o pai, o filho e os descendentes necessários. Nunca criar um `draw_ref` para um arquivo inexistente.

## Como desenhar cada nível

### Nível 1 — arquitetura

Criar um desenho raiz `kind: "system"` com os grandes domínios e sistemas ao redor da codebase. Mostrar escolhas como stack, armazenamento, cache, autenticação, mensageria e provedores externos. Usar `depends-on`, `calls`, `stores-in`, `publishes` e `consumes` para relações macro. Não inserir “cliente clica”, validações de formulário, regras de aprovação ou sequência de telas neste nível.

Incluir um bloco como `Jornadas do usuário` ou equivalente com `draw_ref` para o desenho de nível 2. Esse é o ponto que conecta arquitetura a comportamento sem misturar as abstrações. A arquitetura deve deixar claro que cliente, administrador, operador, suporte ou serviço automatizado podem ser usuários diferentes do mesmo sistema.

### Nível 2 — jornadas do usuário

Criar um desenho próprio que se pareça com a navegação e operação de cada usuário: entrada, áreas, opções disponíveis, retornos e estados observáveis. O nome deve ser `Jornadas do usuário`, nunca assumir que todo usuário é cliente. Antes dos fluxos, identificar os atores/papéis relevantes — por exemplo cliente e administrador — e registrar para cada um:

- objetivo e ponto de entrada;
- opções permitidas e ações proibidas;
- permissões, escopos, tenant ou contexto de acesso;
- dados e estados que consegue observar;
- caminhos de sucesso, erro, recuperação e encerramento.

Separar jornadas de cliente e administrador quando as permissões, objetivos ou passos forem diferentes. Só compartilhar um fluxo quando a regra e o estado observável forem realmente os mesmos; nesse caso, registrar os papéis autorizados na descrição ou em uma pergunta. Não reduzir duas jornadas diferentes a um único “usuário” genérico.

Cobrir as opções relevantes do aplicativo, não apenas o caminho feliz. Representar regras de negócio com nós, relações e condições, sem descrever cores ou aparência. Se o papel de um usuário ainda não estiver confirmado, criar uma pergunta aberta ou de escolha; não inventar permissões.

Se uma opção ainda não foi implementada, ela é um nó terminal do caminho: registrar o estado como não implementado, não criar uma continuação fictícia e manter a pergunta/decisão pendente se for necessária. Um caminho não implementado pode apontar para uma nota de produto ou trade-off, mas não para passos de execução que não existem.

Cada jornada que tiver comportamento de backend deve ser uma cápsula com `draw_ref` para um desenho de nível 3. A jornada continua descrevendo o que o cliente escolhe e percebe; o subdesenho descreve como o servidor atende essa escolha.

### Nível 3 — implementação

Descrever a implementação dentro da fronteira da jornada: entrada da API ou caso de uso, identidade do usuário, autenticação, autorização por papel/escopo/tenant, validações, regras, transação, banco, cache, eventos, integrações, timeout, retry, compensação e resposta para o usuário correspondente. Explicar quando cliente e administrador usam a mesma API com permissões diferentes ou quando percorrem casos de uso distintos. Não repetir a navegação global nem transformar cada chamada trivial em um desenho separado.

Criar nível 4 somente quando a decisão depender da codebase real, de uma integração complexa, de rastreabilidade ou de uma refatoração com risco. Caso contrário, manter o nível 3 como folha técnica.

### Nível 4 — codebase

Ligar nós a `code_refs`, `qualified_name`, testes e dependências comprovados por análise estática. O nível 4 não é lugar para suposições: se o símbolo ainda não puder ser resolvido, usar uma pergunta aberta ou marcar a associação como pendente.

### Símbolos nos nós correspondentes

Todo nó que representar um módulo, serviço, caso de uso, função, classe, endpoint, teste ou outro comportamento já existente na codebase deve carregar a associação no próprio nó, usando `code_refs`. Cada referência deve usar o símbolo qualificado real retornado pela análise estática, além de `identity` e `source_dependencies` quando esses fatos estiverem disponíveis. Não colocar os símbolos em um nó genérico diferente nem apenas na descrição.

Nós abstratos de arquitetura ou jornada que não correspondam diretamente a um símbolo não devem receber referências inventadas; a associação deve ficar no nó de implementação ou codebase que realiza aquele comportamento. Se o símbolo correspondente ainda não puder ser encontrado, marcar a associação como pendente e não declarar rastreabilidade completa.

Quando uma implementação atravessar uma RPC, incluir no nó o handler ou consumidor real da RPC e declarar a interface, contrato ou dependência remota em `source_dependencies` quando ela também tiver fatos rastreáveis. Quando a lógica estiver em uma procedure, função, trigger ou view do banco, referenciar o símbolo SQL no nó correspondente e apontar para o arquivo de migration, schema ou SQL que contém a implementação. Não apontar somente para o model, DTO ou entidade se eles apenas carregarem dados.

## Fluxo de criação

1. Inspecionar o pedido, a stack disponível, `.stdd/config.json`, desenhos existentes e o estado do Git.
2. Definir o desenho raiz e uma árvore mínima com níveis 1, 2 e 3. Adicionar nível 4 somente onde a complexidade exigir.
3. Consultar os fatos da análise estática e mapear cada símbolo real para o nó de implementação ou codebase correspondente antes de gravar a árvore.
4. Criar cada JSON separadamente em `.stdd/draws/`, começando pela raiz e mantendo IDs estáveis.
5. Em cada JSON, usar `groups` para fronteiras de responsabilidade, `flows` para caminhos temporais e `code_refs` nos nós técnicos correspondentes. Não gravar layout, cor, posição, data ou HTML.
6. Validar que todas as relações apontam para nós existentes, todas as etapas apontam para nós existentes, todas as referências hierárquicas resolvem para um pai e cada símbolo está no nó que realmente o representa.
7. Gravar cada desenho com `stdd draw create --data-json '<JSON>'` e conferir pelo viewer com `stdd draw serve`.
8. Revisar a árvore inteira, incluindo terminais não implementados, trade-offs, perguntas sem resposta e associações de símbolos.

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
