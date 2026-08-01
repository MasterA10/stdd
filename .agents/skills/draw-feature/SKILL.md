---
name: draw-feature
description: Cria JSONs de features, fluxos, arquiteturas e trade-offs para o viewer Draw do STDD, sem escrever HTML manualmente.
---

# Draw Feature

Use esta skill quando uma feature, decisão, arquitetura ou trade-off ficar mais fácil de entender com um desenho de nós e relações.

## Fluxo

1. Modele o problema como dados: nós, grupos, relações, fluxos e trade-offs.
2. Use IDs estáveis, labels curtos e descrições que expliquem a responsabilidade de cada nó.
3. Faça cada relação declarar origem, destino, tipo e motivo.
4. Gere ou atualize somente o JSON usando:

```bash
stdd draw create --data-json '<JSON>'
```

5. Abra o viewer com:

```bash
stdd draw serve
```

6. Selecione o desenho gerado no índice e confira conexões, fluxo e trade-offs.

7. Para editar manualmente, interaja diretamente com o canvas: selecione e mova blocos, altere os controles embutidos ou arraste a porta roxa de saída até o destino. O botão `Conectar blocos` mantém o fluxo alternativo por dois cliques. Toda exclusão pede confirmação.
8. Para começar do zero, use `Novo desenho`, informe o título e adicione o primeiro bloco. Um canvas sem nós é válido. As mudanças ficam pendentes até o usuário pressionar `Salvar alterações`.
9. Para iniciar uma feature a partir de um desenho, informe ao Feature Agent o ID do JSON; ele deve ler `.stdd/draws/<draw-id>.json` diretamente e interpretar a lógica do desenho.

Não escreva HTML, CSS ou JavaScript para um desenho individual. O layout e os componentes pertencem ao `.stdd/draw.html`.

## Modelo de dados

O JSON deve conter `id`, `title`, `kind`, `nodes` e `edges`. Pode conter `groups`, `flows`, `tradeoffs` e `notes`.

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

Use `flows` para mostrar caminhos temporais ou operacionais. Use `tradeoffs` para registrar uma decisão, as opções consideradas, prós, contras e impacto.

Toda seta deve declarar `condition` como código numérico: `1` representa `então`, `2` representa `ou` e `3` representa `se`. O viewer converte os códigos para os nomes no HTML. Use `label` e `description` para explicar o significado específico do caminho sem inventar um novo código.

### Semântica das condições e atalhos

As condições precisam representar a lógica do fluxo, não apenas colorir setas:

- `Z` → `condition: 1` → **então**: sequência/default; use para o próximo passo após a etapa atual.
- `O` → `condition: 2` → **ou**: alternativa mutuamente exclusiva; use quando o mesmo ponto oferece caminhos alternativos.
- `C` → `condition: 3` → **se**: condição/guarda; use quando o caminho depende de um predicado explícito.

Regras de consistência:

- Caminho sequencial: `Z` seguido de `Z` é válido.
- Decisão com várias guardas: vários `C` saindo do mesmo nó são válidos quando cada seta possui uma condição clara, como `se aprovado` e `se recusado`.
- Alternativas: vários `O` saindo do mesmo nó são válidos quando representam opções do mesmo nível, como `ou cartão` e `ou Pix`.
- Não misture `C` e `O` para representar a mesma decisão, nem use `O` como continuação de um `C`. Para expressões como “se A ou B”, crie uma decisão explícita ou um único predicado: não codifique a expressão alternando condições de setas.
- Não use `Z` para esconder uma condição, nem `C`/`O` em uma etapa que é apenas sequência. Se a combinação não puder ser explicada em linguagem natural, revise o grafo antes de gravar o JSON.

Exemplos válidos:

```json
[
  {"from": 1, "to": 2, "condition": 1, "label": "então valida"},
  {"from": 2, "to": 3, "condition": 3, "label": "se aprovado"},
  {"from": 2, "to": 4, "condition": 3, "label": "se recusado"}
]
```

Exemplo inválido: uma seta `condition: 3` com label `ou Pix` seguida de uma seta `condition: 2` com label `se aprovado`. Isso mistura guarda e alternativa sem uma decisão semântica clara.

Para decompor sistemas complexos, use `draw_ref` em um nó:

```json
{"id":3,"label":"Pagamento","draw_ref":"payment-details"}
```

O valor deve ser o ID de outro JSON em `.stdd/draws/`. O viewer carregará esse subdesenho somente quando o usuário abrir o nó e permitirá voltar ao desenho pai. Não duplique os nós detalhados no desenho abstrato.

### Perguntas de esclarecimento

Um nó pode declarar `questions` opcionalmente para registrar decisões que ainda precisam de resposta. O viewer mostra no bloco a quantidade de perguntas sem resposta; o indicador continua visível quando chegar a zero para preservar o histórico.

Cada pergunta possui ID numérico, `prompt`, `type` e `answer` opcional. Use:

- `choice` para múltipla escolha, com pelo menos duas opções `{ "id": 1, "label": "..." }` e `answer` igual ao ID escolhido;
- `boolean` para sim ou não, com `answer` booleano ou `null`;
- `open` para resposta aberta, com `answer` textual ou `null`.

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

- Nunca inclua tokens, credenciais ou dados privados no JSON.
- Não use HTML ou JavaScript dentro dos campos de dados.
- O ID do desenho e `draw_ref` devem ser slugs descritivos; IDs internos devem ser números inteiros não negativos.
- Toda relação deve apontar para nós existentes.
- Toda etapa de fluxo deve apontar para um nó existente.
- Um desenho inválido deve ser corrigido antes de ser registrado.

Depois de alterar código ou documentação, registre a alteração com um único tipo de log apropriado:

```bash
stdd log "Atualiza desenho da feature" --impl
```
