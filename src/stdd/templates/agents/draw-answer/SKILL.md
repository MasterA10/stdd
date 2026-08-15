---
name: draw-answer
description: Responde perguntas de um desenho marcadas explicitamente com @stdd usando a codebase e seus símbolos; quando a resposta não puder ser comprovada, associa o arquivo e o símbolo relevante ao nó.
---

# Draw Answer

## Responsabilidade

Responder perguntas de Draw endereçadas explicitamente a este agente. Esta skill investiga a codebase; ela não melhora a arquitetura, cria produção ou adivinha decisões.

Primeiro execute o localizador oficial de perguntas pendentes:

```bash
stdd draw questions
```

Trabalhe somente sobre os itens JSON retornados por esse comando. Cada item informa a pergunta e o `draw_file` — o JSON onde ela está — além de `node_id` e `question_id`. O comando já filtra perguntas cujo `prompt` contém `@stdd` (sem diferenciar maiúsculas de minúsculas) e cujo `answer` está ausente, `null` ou é uma string vazia. Não passe argumentos nem percorra os JSONs manualmente para descobrir perguntas. Perguntas sem o marcador pertencem ao usuário ou revisor humano. Respostas já preenchidas, inclusive `false` e `0`, não devem ser reprocessadas.

Quando precisar entregar o contexto para revisão humana, use também:

```bash
stdd draw answer
```

Esse comando é somente leitura e apresenta as perguntas pendentes agrupadas por desenho e nó, com o símbolo associado, arquivo, evidências e limitações em linguagem natural. O JSON de `stdd draw questions` continua sendo a fonte operacional para a investigação.

## Investigação baseada em evidências

Para cada item retornado:

1. Ler o desenho completo, o nó, seus pais, relações, fluxos, grupos e `draw_ref` dos subdesenhos relacionados.
2. Consultar a codebase e, quando disponível, os fatos em `.stdd/facts/`: símbolos, `qualified_name`, arquivo, posição, dependências, chamadas, testes, contratos, RPCs, procedures, migrations e schemas.
3. Ler os símbolos completos e dependências relevantes antes de concluir. Confirmar comportamento em testes ou contratos quando existirem.
4. Separar fatos observados de inferências. Não inventar arquivos, símbolos, respostas, permissões ou comportamento ausente.

## Resposta e rastreabilidade

Quando houver evidência suficiente para responder:

- gravar a resposta em `question.answer`, respeitando o tipo (`choice`, `boolean` ou `open`);
- marcar no próprio nó todos os símbolos relevantes comprovados em `code_refs`, preservando referências existentes e usando `symbol`, `qualified_name`, `identity`, `file` e `source_dependencies` quando disponíveis;
- remover somente `@stdd` do `question.prompt`, preservando o restante da pergunta e o histórico;
- não alterar outras perguntas, relações, grupos ou hierarquia.

Quando não houver evidência suficiente para responder, o agente mantém a pergunta aberta:

- manter `question.answer` sem resposta e conservar `@stdd`;
- procurar o arquivo e o símbolo mais relevante para a investigação;
- marcar esse símbolo no próprio nó em `code_refs`, sem inventar referências. Se não for possível comprovar nenhum símbolo, informar a limitação ao usuário.

Uma associação de símbolo não é uma resposta. Porém, se a resposta for encontrada, a pergunta não deve continuar aberta: ela recebe `answer`, os símbolos relevantes e perde o marcador.

## Formato obrigatório da resposta

Depois de concluir a investigação, apresente o resultado em linguagem natural, na língua da pergunta, e não despeje o JSON bruto nem uma lista solta de achados. Use este formato para cada pergunta:

### Resposta

Explique a conclusão diretamente em uma ou duas frases humanas. Não repita `@stdd` e não esconda a conclusão em código ou metadados.

### Nó e símbolo associado

- **Nó:** `<label do nó>` (id `<node_id>`)
- **Símbolo associado ao nó:** `<qualified_name>` ou `<symbol>`
- **Arquivo:** `<file>`, quando disponível

O símbolo associado ao nó deve aparecer explicitamente na saída, mesmo quando ele já estiver registrado em `code_refs`. Se houver mais de um símbolo relevante, liste todos com seus respectivos arquivos. Quando nenhum símbolo puder ser comprovado, escreva `Símbolo associado ao nó: não comprovado` e explique essa limitação; nunca invente um nome.

### Evidências

Descreva brevemente quais arquivos, símbolos, testes, contratos ou fatos sustentam a resposta. Separe fatos observados de inferências e cite os caminhos/símbolos de forma legível.

### Limitações

Informe somente as incertezas que afetam a conclusão. Se não houver limitações relevantes, escreva `Nenhuma limitação relevante encontrada.`

## Limites, gravação e encerramento

Não criar ou editar código de produção, testes, Markdown paralelo ou subdesenhos. Preservar `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`. Validar IDs, referências e tipos de resposta antes de salvar o JSON completo, preferencialmente com:

```bash
stdd draw create --data-json '<JSON_COMPLETO_ATUALIZADO>'
```

Execute um ciclo por invocação e registre o trabalho concluído:

```bash
stdd log "Responde perguntas endereçadas do Draw" --type implementacao
```

Ao encerrar, informe perguntas respondidas, nós atualizados com símbolos, perguntas que permaneceram abertas, evidências e limitações seguindo o formato acima. Uma pergunta sem evidência é resultado válido; nunca force uma resposta.
