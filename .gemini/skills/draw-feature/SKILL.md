---
name: draw-feature
description: Cria JSONs de features, fluxos, arquiteturas e decisões para o viewer Draw do Looper, sem escrever HTML manualmente.
---

# Draw Feature

Use esta skill quando uma feature, decisão ou arquitetura ficar mais fácil de entender com um desenho de nós e relações.

## Hierarquia do sistema

Quando o desenho fizer parte de um sistema maior, preserve uma árvore explícita de níveis:

- **Nível 1 — arquitetura:** escolhas macro ao redor da codebase, como aplicativo, linguagem, runtime, banco, cache, autenticação e sistemas externos. Não descrever comportamento do aplicativo aqui.
- **Nível 2 — jornada:** navegação e operação de cada usuário, incluindo cliente, administrador e outros papéis, com opções, permissões, regras de negócio e estados observáveis. Uma opção ainda não implementada é uma folha terminal, sem continuação fictícia.
- **Nível 3 — implementação:** como o backend atende uma jornada, incluindo API, validações, autorização, persistência, eventos, integrações e falhas.
- **Nível 4 — codebase:** arquivos, módulos, símbolos, testes e dependências reais, somente quando a complexidade justificar.

Desenhos integrados a essa árvore devem declarar `hierarchy.level`, `hierarchy.role`, `hierarchy.parent_draw_ref`, `hierarchy.parent_node_id` e `hierarchy.root_draw_ref`. A raiz usa nível 1 e pai nulo. Todo descendente tem pai e o pai aponta para ele com `draw_ref`; não existem fluxos órfãos. Um nível pode pular diretamente para outro quando não houver detalhe útil intermediário, mas nunca pode perder a relação de pai.

## Fluxo

1. Modele o problema como dados: nós, grupos, relações, fluxos e, quando aplicável, a posição na hierarquia do sistema.
2. Use IDs estáveis, labels curtos e descrições que expliquem a responsabilidade de cada nó. Identifique o papel do usuário em cada jornada; não trate cliente e administrador como o mesmo ator quando as permissões ou objetivos forem diferentes.
3. Faça cada relação declarar origem, destino, tipo e motivo.
4. Gere ou atualize somente o JSON usando:

```bash
looper draw create --data-json '<JSON>'
```

Depois de criar ou atualizar o JSON, inclusive quando somente o Draw mudou, registre o checkpoint da interação:

```bash
looper log "Atualiza desenho da feature" --impl
```

## Regras obrigatórias do loop

Erros são consequências condicionais (`se`/`ou`), validações antecedem ações críticas e funcionalidade planejada fica terminal no grupo `Não implementado`. Consulte `backlog test` antes de produção, execute uma task por interação e conclua pelo ID com `backlog complete`. Perguntas gerais sem `node_id` pertencem ao painel geral de melhorias.

5. Abra o viewer com:

```bash
looper draw serve
```

6. Selecione o desenho gerado no índice e confira conexões, fluxo e decisões.

7. Para editar manualmente, interaja diretamente com o canvas: selecione e mova blocos, altere os controles embutidos ou arraste a porta roxa de saída até o destino. O botão `Conectar blocos` mantém o fluxo alternativo por dois cliques. Toda exclusão pede confirmação.
8. Para começar do zero, use `Novo desenho`, informe o título e adicione o primeiro bloco. Um canvas sem nós é válido. As mudanças ficam pendentes até o usuário pressionar `Salvar alterações`.
9. Para iniciar uma feature a partir de um desenho, informe ao Create Tests Agent o ID do JSON; ele deve ler `.looper/draws/<draw-id>.json` diretamente e interpretar a lógica do desenho.

Antes de persistir um desenho, `looper draw create` exige que todo nó tenha pelo menos uma conexão por edge, em qualquer direção. `draw_ref`, `flows.steps` e vínculos hierárquicos não substituem uma edge. A análise de repetição de títulos, fluxos, subfluxos e estruturas semelhantes é somente warning: nunca bloqueia a criação e não deve ser tratada como prova de geração por script.

Não escreva HTML, CSS ou JavaScript para um desenho individual. O layout e os componentes pertencem ao viewer React Flow empacotado pelo Looper.

## Modelo de dados

O JSON deve conter `id`, `title`, `kind`, `nodes` e `edges`. Pode conter `groups`, `flows` e `notes`. Decisões ficam em perguntas respondidas; não há chave de alternativas no contrato ativo.

O `id` do desenho deve ser descritivo, seguro e corresponder ao nome do JSON, por exemplo `checkout-resiliente`. `draw_ref` usa o mesmo tipo de ID para relacionar um fluxo a um subfluxo. IDs internos de nós, grupos, relações e fluxos devem ser números inteiros não negativos.

Use `nodes` para representar sistemas, módulos, atores, decisões, tabelas ou etapas. Use `edges` para relações como:

- `depends-on`;
- `calls`;
- `stores-in`;
- `publishes`;
- `consumes`;
- `blocks`;
- `alternative-to`;
- `flow`.

Use `flows` para mostrar caminhos temporais ou operacionais. Registre decisões como perguntas respondidas no nó mais relacionado, preservando a evidência e o histórico.

Toda seta deve declarar `condition` como código numérico: `1` representa `então`, `2` representa `ou` e `3` representa `se`. O viewer converte os códigos para os nomes no HTML. Use `label` e `description` para explicar o significado específico do caminho sem inventar um novo código.

### Semântica das condições

As condições precisam representar a lógica do fluxo, não apenas colorir setas. Os códigos do JSON são:

- `condition: 1` → **então**: sequência/default; use para o próximo passo após a etapa atual.
- `condition: 2` → **ou**: escolha alternativa mutuamente exclusiva; use quando exatamente uma opção pode acontecer.
- `condition: 3` → **se** (`C`): condição/guarda; use quando o caminho depende de um predicado explícito.

Regras de consistência:

- Caminho sequencial: setas `condition: 1` são válidas quando representam apenas a continuação do fluxo.
- Condicionais: quando uma etapa tem caminhos baseados em condições, use uma seta `C` para cada condição: `se A` e `se B`. Não represente uma dessas condições com `ou`.
- Alternativas: use várias setas `condition: 2` quando representam opções do mesmo nível e somente uma pode acontecer: `A ou B`; nunca modele esse caso como se ambas as opções fossem executadas.
- Não misture `C` e `O` para representar a mesma decisão. `C` responde “em que condição este caminho acontece?”; `O` responde “qual alternativa exclusiva será escolhida?”.
- Para “se A ou B”, use uma única condição `C` com o predicado `se A ou B` quando A ou B forem apenas partes da mesma guarda. Se A e B forem caminhos distintos, use duas setas `C`, uma `se A` e outra `se B`, desde que as condições sejam mutuamente exclusivas no domínio. Se ambas puderem acontecer, o fluxo precisa representar sequência ou paralelismo, não uma escolha `O`.
- Não use uma condição para esconder uma etapa que é apenas sequência. Se a combinação não puder ser explicada em linguagem natural, revise o grafo antes de gravar o JSON.

Exemplos válidos:

```json
[
  {"from": 1, "to": 2, "condition": 1, "label": "então valida"},
  {"from": 2, "to": 3, "condition": 3, "label": "se aprovado"},
  {"from": 2, "to": 4, "condition": 3, "label": "se recusado"}
]
```

Exemplo inválido: uma seta `condition: 3` com label `se aprovado` e outra `condition: 2` com label `ou Pix` saindo da mesma decisão. Isso mistura guarda e alternativa sem uma decisão semântica clara.

Para decompor sistemas complexos, use `draw_ref` em um nó:

```json
{"id":3,"label":"Pagamento","draw_ref":"payment-details"}
```

Ao utilizar subfluxos, observe rigorosamente as regras de **hierarquia de funções e encapsulamento**:

1. **Separação Clara de Níveis de Abstração**:
   - **Desenho pai**: mantém somente a abstração do nível em que está e aponta para o filho por `draw_ref`.
   - **Desenho filho**: mantido em arquivo próprio (`.looper/draws/<subflow-id>.json`), detalha exclusivamente a fronteira interna e declara seu `parent_draw_ref` e `parent_node_id`.
   - Em sistemas, use nível 1 para arquitetura, nível 2 para jornadas, nível 3 para implementação e nível 4 para codebase. Um desenho de feature pode começar no nível que corresponde ao seu escopo, mas não pode criar um filho sem pai.

2. **Proibição de Duplicação e Poluição**:
   - Um nó com `draw_ref` no fluxo principal atua como um **bloco/cápsula abstrato**. Ele **não deve expor ou duplicar** os subprocessos e passos detalhados que pertencem ao subfluxo.
   - O subfluxo detalha o funcionamento interno daquela etapa específica, sem reinspecionar a sequência global externa do fluxo pai.
   - **Nunca duplique etapas**: Um processo individual que ocorre dentro do subfluxo **jamais deve aparecer no fluxo principal** (e vice-versa), garantindo que a divisão de escopos seja limpa e modular.

3. **Navegação sob Demanda**:
   - O valor de `draw_ref` deve ser o ID descritivo de outro JSON em `.looper/draws/`. O viewer carregará esse subdesenho somente quando o usuário abrir o nó e permitirá voltar ao desenho pai. Não duplique os nós detalhados no desenho abstrato.

### Perguntas de esclarecimento

Um nó pode declarar `questions` opcionalmente para registrar decisões que ainda precisam de resposta. O viewer mostra no bloco a quantidade de perguntas sem resposta; o indicador continua visível quando chegar a zero para preservar o histórico.

Cada pergunta possui ID numérico, `prompt`, `type` e `answer` opcional. Use:

- `choice` para múltipla escolha, com pelo menos duas opções `{ "id": 1, "label": "..." }`; `answer` é o ID escolhido ou um texto quando a pessoa usa a resposta livre;
- `boolean` para sim ou não, com `answer` booleano ou `null`;
- `open` para resposta aberta, com `answer` textual ou `null`.

Exemplo:

```json
{
  "id": 4,
  "label": "Pagamento",
  "questions": [
    {
      "id": 1,
      "type": "choice",
      "prompt": "Qual provedor deve ser priorizado?",
      "options": [{"id": 1, "label": "Stripe"}, {"id": 2, "label": "Adyen"}],
      "answer": null
    },
    {"id": 2, "type": "boolean", "prompt": "Precisa de fallback?", "answer": true},
    {"id": 3, "type": "open", "prompt": "Qual risco devemos explorar?", "answer": "Fraude"}
  ]
}
```

Perguntas respondidas permanecem no JSON como histórico. Não invente respostas: uma pergunta sem resposta é uma decisão aberta para o usuário ou para a próxima rodada do agente.

## Escala e clareza

- Não crie um nó para cada detalhe irrelevante.
- Separe domínios com `groups`.
- Prefira várias relações claras a uma descrição genérica escondida.
- Use `description` para explicar por que o nó existe.
- Use `edge.description` para explicar o efeito da conexão.
- Em grafos muito grandes, divida por feature ou fluxo relacionado.
- O viewer carrega apenas o JSON selecionado; não é necessário juntar o sistema inteiro em um arquivo.
- Subdesenhos também são carregados sob demanda; um desenho abstrato guarda apenas o `draw_ref`.
- Fluxos sem posições manuais são distribuídos em camadas da esquerda para a direita. Relações longas usam corredores externos para reduzir setas sobre blocos e cruzamentos difíceis de ler.
- O JSON contém somente lógica. Não grave posição, coordenadas, dimensões, cores, estilos, tema, layout, viewport ou datas no desenho.
- O script do viewer calcula distribuição, dimensões, quebra de texto, cores semânticas, portas, marcadores, rotas das setas, pan e zoom.
- Posições ajustadas manualmente valem apenas para a sessão aberta; ao recarregar, o algoritmo recompõe o layout usando a lógica atual.
- O JSON continua sendo a fonte de verdade interna, mas a edição humana acontece pelos controles visuais do Draw.
- Cada ID possui somente um JSON atual; salvar novamente substitui esse desenho, sem criar histórico automático.
- Não crie `request.md`, `scenarios.md` ou outra cópia intermediária: o JSON é a fonte de verdade.

## Segurança e validação

## Semântica dos blocos e grupos

- O nó não possui tipo estrutural: não use `processo`, `decisão`, `ator`, `api` ou qualquer outro campo `nodes[].type`.
- Pontos de decisão não são nós. A decisão é expressa pelas setas e por suas condições (`condition`, `label` e `description`).

Cada nó pode declarar `success_criteria` e `failure_criteria` como textos opcionais. Use-os quando o comportamento tiver uma condição objetiva de aceite: descreva como comprovar o sucesso e qual cenário caracteriza falha. O Looper injeta esses campos no contexto da task e transforma a definição em uma regra obrigatória de aceite do loop; não torne `tools` obrigatório para preencher esses critérios.
- Use `groups` para representar domínio, responsabilidade ou fronteira visual. A cor do bloco vem exclusivamente do grupo; não grave cores individuais no nó.
- Um bloco sem grupo usa a aparência neutra do viewer. Para alterar o grupo, edite o campo `group` do nó no editor.

- Nunca inclua tokens, credenciais ou dados privados no JSON.
- Não use HTML ou JavaScript dentro dos campos de dados.
- O ID do desenho e `draw_ref` devem ser slugs descritivos; IDs internos devem ser números inteiros não negativos.
- Toda relação deve apontar para nós existentes.
- Toda etapa de fluxo deve apontar para um nó existente.
- Um desenho inválido deve ser corrigido antes de ser registrado.

Depois de criar ou atualizar qualquer JSON lógico do Draw, mesmo sem alteração de código, registre a alteração com um único tipo de log apropriado:

```bash
looper log "Atualiza desenho da feature" --impl
```
