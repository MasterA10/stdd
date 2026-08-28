---
name: test-application
description: "Lê o fluxo completo do Draw e da aplicação, propõe um plano de testes observável, confirma o escopo com o usuário e implementa cobertura de L2/L3 — incluindo jornadas e estados com Playwright, persistência, integração e API."
---

# Test Application

Use esta skill quando o usuário quiser descobrir o que testar, revisar a cobertura,
criar um plano de testes ou implementar testes para um fluxo da aplicação. Ela atende
interações comuns e também pode ser usada quando um backlog entregar um nó; não depende
de `looper backlog test`, não exige que o usuário conheça os IDs do Draw e não executa
`backlog complete` automaticamente.

## Resultado esperado

Transforme o comportamento descrito no Draw em uma estratégia executável e rastreável:

```text
ler árvore do Draw e code_refs
  -> mapear jornadas, estados, contratos e riscos
  -> propor plano de testes e perguntar o que precisa de confirmação
  -> aguardar aprovação/ajustes do usuário
  -> implementar os testes escolhidos
  -> executar testes focados e looper test
  -> corrigir o próprio teste/fixture/harness quando necessário
  -> relatar cobertura, evidências, falhas e limitações
```

O plano é obrigatório antes de criar ou alterar uma suíte. Se o usuário já tiver
aprovado um plano explícito na mesma conversa, prossiga sem repetir a pergunta.

## Leitura e descoberta

1. Procure `.looper/draws/`, índice, raiz de sistema e os Draws L1–L4 relacionados.
   Quando houver um recorte específico, leia diretamente `.looper/draws/<draw-id>.json`.
   Leia o pai antes dos filhos e preserve `draw_ref`, `parent_draw_ref`,
   `parent_node_id` e `root_draw_ref`.
2. Se o usuário indicar um Draw ou nó, use esse recorte; caso contrário, descubra a
   jornada mais provável pela solicitação e apresente o escopo encontrado. Não invente
   um fluxo quando houver mais de um candidato: peça a escolha.
3. Leia descrições, passos, grupos, condições, perguntas respondidas, estados de erro,
   permissões, integrações, persistência e `code_refs`. Folhas do grupo `Não
   implementado` são escopo futuro e não devem virar testes de comportamento existente.
4. Inspecione os arquivos e símbolos reais apontados pelos `code_refs`, o runner
   configurado, fixtures, scripts de desenvolvimento, rotas e configuração de
   navegador. Código não lido não é evidência.

O escopo inclui todos os subfluxos internos do nó entregue quando eles existirem. A
árvore `draw-system` é contrato: preserve referências, detecte fluxo órfão e não
confunda uma tela com cobertura somente de frontend. Cubra endpoints/handlers,
persistência e integrações quando forem parte do comportamento.

## Plano de teste

Antes de escrever testes, entregue um plano curto e verificável. Para cada cenário,
declare: ID do nó/fluxo, comportamento, pré-condições, entrada, resultado esperado,
efeitos observáveis, nível do teste, runner/arquivo provável, dados necessários e
critério de aprovação.

### Prioridade do L2: jornada e estado observável

Para nós L2, use principalmente `playwright-cli` para testar e validar a experiência
real do usuário, independentemente de conhecer ou inspecionar a implementação da
codebase. O objetivo principal é comprovar que:

- as telas estão conectadas e a navegação segue a jornada descrita;
- entradas, validações, mensagens, loading, sucesso e erro aparecem no estado correto;
- uma ação que deveria persistir algo continua refletida depois de sair, recarregar ou
  voltar à tela — valide o estado pelo próprio navegador, não somente por uma resposta de
  API ou por uma asserção interna;
- o estado que atravessa telas ou sessões permanece consistente e não é perdido em uma
  transição.

Quando a UI alterar dados, teste o ciclo completo: estado inicial, ação do usuário,
feedback visível, navegação/recarregamento e estado final observado. Isso inclui
configurações, preferências, credenciais de integração e demais valores persistentes,
respeitando redaction e nunca expondo segredos reais em screenshots, traces ou logs.

As validações L2 podem depender de implementações L3 (API, controller, persistência,
autorização e integrações), mas devem verificar a consequência observável no fluxo. Só
desça para testes de unidade, integração ou consulta direta ao banco para localizar a
causa, cobrir regras não visíveis ou confirmar a persistência quando o navegador não
conseguir observá-la.

Use `playwright-cli` primeiro para explorar, reproduzir e validar a jornada; depois
converta os cenários aprovados em Playwright Test executável e repetível. Não substitua
uma navegação L2 por chamadas diretas ao backend.

### Cobertura complementar L3 e infraestrutura

Sugira cobertura proporcional, combinando somente o que o fluxo justificar:

- unidade para decisões e regras puras;
- integração para controller, banco, filas, hooks e persistência;
- contrato/API para endpoints, autenticação e integrações;
- Playwright Test para automatizar os cenários L2 aprovados, usando snapshots,
  locators e asserções baseadas em estado;
- persistência para confirmar no banco o registro, alteração, relacionamento,
  transação, rollback, idempotência e limpeza esperados pelo Draw. Verifique o estado
  por consultas/portas públicas apropriadas ao projeto, sem afirmar persistência apenas
  pela resposta HTTP;
- testes live, performance, segurança, isolamento ou pentest apenas quando o risco e
  as pré-condições do Draw justificarem.

Inclua `teste live`, `pgTAP` ou SQL quando o banco/provedor exigir esse nível de
verificação; mantenha o resultado como `not_executed` quando a pré-condição faltar.

Pergunte ao usuário somente sobre escolhas que alteram o plano, por exemplo: ambiente
live ou sandbox, dados que podem ser criados, navegadores suportados, integração externa
obrigatória, escopo de acessibilidade/performance e cenários que devem ficar fora. Se a
resposta puder ser descoberta na codebase, descubra-a em vez de perguntar. Registre no
plano as suposições restantes e marque-as como bloqueio quando impedirem um teste
confiável.

Não comece a implementação sem aprovação do plano. Uma confirmação curta como
“pode implementar” vale quando não houver pergunta pendente.

## Implementação

1. Após a aprovação, crie ou ajuste testes no runner já adotado pela aplicação. Se não
   houver runner, proponha a menor configuração compatível e peça aprovação antes de
   instalar dependências ou iniciar serviços.
2. Implemente os cenários aprovados, incluindo sucesso, erro, limites, autorização,
   transições e efeitos reais descritos no fluxo. Nomeie testes pelo comportamento.
3. Para L2, use primeiro `playwright-cli` para abrir a aplicação, navegar pelas telas,
   inspecionar snapshots, verificar estados antes/depois e diagnosticar. Depois
   implemente os cenários aprovados com Playwright Test e execute-os pela CLI (`npx
   playwright test` ou o comando local equivalente). Consulte `playwright-cli --help`/
   `npx playwright --help` quando a versão instalada divergir. Use a aplicação real,
   aguarde estados observáveis — não tempos fixos — e capture screenshots/traces sem
   dados sensíveis quando ajudarem a diagnosticar.
4. Para persistência, prepare dados isolados, execute a ação pelo caminho público do
   sistema e confirme o antes/depois no banco. Inclua rollback, constraints,
   concorrência, duplicidade e limpeza quando forem consequências do fluxo. Nunca
   troque um teste de persistência por um mock do repositório.
5. Para integrações externas, mantenha a suíte determinística offline e deixe testes
   live explícitos, opt-in, com timeout e credenciais por ambiente.
6. Não masque falhas com asserções vazias, resultados pré-calculados, mocks da lógica
   testada ou skips silenciosos. O mock pode representar entrada externa quando ela não
   chega ao ambiente local; lógica, persistência e efeitos devem permanecer reais no
   nível escolhido.
7. Se um teste falhar por defeito da aplicação, registre a falha com evidência e pare
   para o usuário decidir sobre uma correção de produção. Corrija automaticamente apenas
   teste, fixture, configuração de teste ou harness dentro do escopo aprovado.

## Validação e rastreabilidade

- Execute o teste focado, a suíte afetada e `looper test` antes de concluir. Falha de
  ambiente, contrato ou cenário é `blocked`/`not_executed`, nunca sucesso.
- Quando houver navegador, execute o fluxo exploratório com `playwright-cli` e a suíte
  automatizada com Playwright; quando houver banco, prove a persistência com o estado
  real ou deixe o cenário explicitamente não executado com a pré-condição ausente.
- Verifique o Draw novamente e associe cada nó coberto ao símbolo real do teste; a
  associação não é automática. Em cada nó entregue, associe o símbolo real. Use,
  quando aplicável:

  A associação não é automática; associar o símbolo real de cada teste ao nó coberto
  é parte da entrega, mesmo fora do loop de implementação.

  ```bash
  looper draw associate-reference --draw-id <draw-id> --node-id <node-id> \
    --qualified-name '<símbolo-real-do-teste>' --source-dependency '<dependência-real>'
  looper draw symbols
  ```

- Não invente `qualified_name`, `code_refs` ou cobertura para um nó sem implementação.
  Diferencie `passed`, `failed`, `blocked` e `not_executed`, informando a causa.
- A associação de cada nó ao símbolo real do teste deve ser feita em todo ciclo de
  entrega; arquivo sem `qualified_name` não é evidência. Os gates
  `draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`,
  `draw.level4_missing_code_ref` e `draw.empty_node_symbol` permanecem bloqueios.
- Registre a conclusão sem segredos:

  ```bash
  looper log "Plano e testes da aplicação — <escopo> — <status>" --type teste
  ```

- Se o plano confirmar uma regra durável de operação, arquitetura ou contrato, atualize
  `AGENTS.md`; decisões visuais e de interação pertencem a `.looper/design.md`.

Testes de frontend e markdown entram somente quando fizerem parte do comportamento;
  aplique cobertura proporcional ao risco, nunca por quantidade fixa.

Não reduza a cobertura à interface quando o fluxo exigir endpoints/handlers,
persistência ou integrações. Não registre hipóteses como evidência. É obrigatório
associar cada teste ao símbolo real correspondente.
Não reduz a cobertura à interface: esta é uma regra para fluxos completos.

Mantenha memória contextual seletiva: registre somente decisões aceitas, não hipóteses,
IDs temporários, logs ou segredos. Se `backlog.test_loop_enabled: false`, a skill ainda
pode ser chamada como interação comum; apenas não deve fingir que um gate de backlog foi
executado.

Esta skill não pertence exclusivamente a um loop de implementação; ela pode conduzir
testes em uma interação comum.

## Relato final

Informe o status, o plano aprovado, arquivos e símbolos de teste alterados, comandos
executados, evidências, cobertura por camada, falhas encontradas, pré-condições ausentes
e o que ficou fora do escopo. Não declare a aplicação correta apenas porque o teste foi
criado: a conclusão depende da execução e das asserções observáveis.
