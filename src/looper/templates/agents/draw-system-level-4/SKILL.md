---
name: draw-system-level-4
description: "Cria sob demanda o nível 4 de um Draw System no Looper: a explicação técnica de baixo nível que liga um comportamento do nível 3 a arquivos, módulos, símbolos, contratos, banco, integrações e testes reais. Não iniciar automaticamente nem inventar fatos."
---

# Draw System — Nível 4: Codebase / baixo nível

## Responsabilidade

Explicar em linguagem puramente técnica como o código realiza um comportamento já descrito no nível 3. Esta skill é aberta somente quando o usuário solicita rastreabilidade, quando há integração complexa ou quando existe necessidade técnica explícita. Não iniciar automaticamente ao terminar o nível 3.

Leia sempre o nó de nível 3, seu pai de nível 2, a raiz e os descendentes relevantes antes de criar qualquer JSON.

## Hierarquia e encapsulamento

Crie o filho com `hierarchy.level: 4`, `role: "codebase"`, `parent_draw_ref` igual ao nível 3, `parent_node_id` igual ao nó/decisão aprofundado e `root_draw_ref` igual à arquitetura. Atualize o nó pai com um único `draw_ref`. Todo descendente precisa de `parent_draw_ref`, `parent_node_id` e `root_draw_ref`; toda cadeia deve ser resolvível em `.looper/draws/`, chegar ao nível 1 e permanecer sem fluxos órfãos.

O nível 3 permanece como Controller em linguagem simples e o pai permanece como cápsula. Não duplicar regras, navegação ou passos do pai. Não criar fluxo órfão, referência quebrada, continuação fictícia ou arquivo intermediário.

## Conteúdo técnico

Inclua somente fatos comprovados que explicam a decisão autorizada:

- módulos, arquivos, classes, funções e `qualified_name`;
- símbolos internos, identidade e posições retornadas pela análise estática;
- queries SQL, migrations, schemas, entidades, DTOs e contratos de interface;
- dependências entre pacotes, módulos, serviços e consumidores;
- testes e asserções que protegem o comportamento;
- procedures, funções, triggers e views de banco;
- handlers e consumidores de RPC, contrato/IDL e dependência remota;
- funções externas e provedores quando a implementação realmente atravessar essa fronteira.

Associe `code_refs` no próprio nó correspondente e declare `source_dependencies` quando o fato estiver disponível. Se o símbolo não puder ser resolvido, use uma `question` ou marque a associação como pendente. Nunca invente arquivo, classe, model, procedure, RPC, SQL, query ou qualified name.

Quando a implementação atravessar RPC, inclua o handler ou consumidor real e o contrato/interface remoto. Quando a lógica estiver no banco, associe o símbolo SQL e o arquivo de migration, schema ou SQL que contém a implementação.

## Nível 4 não é linguagem de produto

Não redesenhar arquitetura, telas ou regras em linguagem de usuário. O nível 4 detalha como o nível 3 é realizado: módulos, chamadas, contratos, persistência e testes. Se uma decisão de negócio ainda não estiver clara, voltar ao nível 3 e registrar a pergunta; não resolvê-la inventando código.

## Funcionalidades não implementadas

Uma funcionalidade planejada e não implementada permanece em grupo separado `Não implementado` ou `Planejado`, sem cor individual, sem filhos e sem passos seguintes. Não atribuir `code_refs` ou dependências a código que não existe.

## Convenção lógica de conexões

Toda seta usa `condition` numérico:

- `1` (`então`) é consequência certa e pode coexistir com uma família de `3` (`se`) ou de `2` (`ou`);
- `3` (`se`) é guarda possível e exige pelo menos outro `se` correspondente na mesma origem;
- `2` (`ou`) é alternativa exclusiva.

Nunca misture `se` com `ou` na mesma decisão. Nunca misture `ou` com `se`: são a mesma proibição vista pela outra direção. O `então` pode acompanhar qualquer uma das famílias por representar uma continuação inevitável. Use `label` e `description` para explicar as condições; não use `nodes[].type` para criar decisões.

## Execução sob demanda

1. Confirmar que o usuário autorizou o recorte técnico e que o nível 3 existe.
2. Ler pai, filho, raiz, perguntas, grupos, fluxos, `draw_ref` e fatos estáticos relacionados.
3. Consultar a análise estática e testes reais antes de associar símbolos.
4. Criar somente o subfluxo técnico necessário, sem abrir outras partes por simetria.
5. Usar `groups` para responsabilidades e `flows` para a execução técnica necessária.
6. Criar o JSON separadamente com IDs estáveis usando `looper draw create --data-json '<JSON>'`.
7. Validar pais, raiz, referências, relações, condições, `code_refs`, `qualified_name`, `source_dependencies` e terminais.
8. Revisar com `looper draw serve`. Manter o nível 4 terminal quando não houver detalhe técnico adicional necessário.

Ao alterar o desenho, registrar:

```bash
looper log "Rastreia codebase do sistema no nível 4" --type implementacao
```

Entregar IDs, arquivos e símbolos resolvidos, referências `unresolved` ou `drift`, queries, contratos, testes, limitações e o recorte para o `$test-application`. O `$implement-backend` (e `$implement-frontend`) seguem após a cobertura ser avaliada e o usuário aprovar a implementação de produção.

## Regras do ciclo interativo

Trate erros como consequências condicionais (`se`/`ou`) e valide no ponto correto antes dos efeitos. Mantenha funcionalidades ainda não implementadas terminais no grupo `Não implementado`. O nível 4 também segue TDD: uma task por interação, `backlog test` antes da produção, integração comprovada por API, persistência e validações reais e `backlog complete` pelo ID recebido.

## Regras gerais de todos os níveis

O JSON é a fonte de verdade. Não criar HTML, CSS, JavaScript, `request.md`, `scenarios.md` ou cópia intermediária. Não gravar layout, cor, posição, data ou viewport. Toda relação deve apontar para nós existentes; toda etapa de fluxo deve apontar para nó existente. Não registrar segredos.
