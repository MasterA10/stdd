---
name: create-tests
description: Especifica funcionalidades por testes executáveis no STDD sem alterar código de produção. Usar ao transformar pedidos, desenhos, contratos de API, integrações de IA, regras de banco ou requisitos de segurança e desempenho em cenários verificáveis.
---

# Create Tests Agent

## Responsabilidade

Transformar intenção em comportamento observável e testes que falhem pelo motivo esperado. Tratar testes como documentação executável. Não implementar código de produção, não enfraquecer testes existentes e não duplicar a especificação em arquivos Markdown intermediários.

## Papéis e permissões

Quando a entrada vier de um sistema ou jornada de usuário, identificar explicitamente o papel que executa cada ação — por exemplo cliente ou administrador. Especificar caminhos separados quando objetivos, permissões, dados visíveis ou estados forem diferentes. Cobrir autorização negativa e tentativa de acesso indevido quando a regra fizer parte do comportamento; não testar uma permissão inventada. Se o papel ou escopo ainda estiver indefinido, registrar a decisão como pendência antes de criar o teste.

## Leitura hierárquica de Draws

Quando a entrada vier de uma das skills `$draw-system-level-1` a `$draw-system-level-4` ou de um desenho com `hierarchy`, tratar a árvore como contrato navegável: nível 1 fornece contexto arquitetural, nível 2 define as jornadas e regras observáveis, nível 3 delimita a implementação a ser testada e nível 4 fornece referências reais da codebase. Ler o desenho pai antes do filho e preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`.

Não transformar decisões macro de arquitetura em testes de comportamento sem uma jornada correspondente. Não testar uma folha marcada como não implementada como se ela existisse. Se houver fluxo órfão, caminho implementado sem pai, `draw_ref` não resolvido ou pai e filho duplicando passos, interromper a especificação e reportar a inconsistência antes de criar testes.

## Triagem da entrada

Antes de especificar testes, identificar de onde vem a feature. Há três entradas possíveis:

1. **Texto:** quando o pedido descreve diretamente o comportamento. Usar a solicitação, critérios aceitos e contexto do código como fontes principais.
2. **Desenho informado:** quando o usuário fornece um ID, caminho ou indica explicitamente um Draw. Ler `.stdd/draws/<draw-id>.json` completo e abrir `draw_ref` somente quando o subfluxo fizer parte do escopo.
3. **Desenho alterado:** quando o pedido não informa um desenho específico, inspecionar o estado do Git para descobrir fluxos novos ou modificados. Usar:

   ```bash
   git status --short -- .stdd/draws
   git diff --name-status -- .stdd/draws
   git diff --cached --name-status -- .stdd/draws
   ```

   Incluir também arquivos JSON não rastreados listados pelo `git status`. Para cada desenho alterado, ler o JSON atual completo e, para desenhos rastreados, comparar o patch com `git diff` (e com `git diff --cached` quando aplicável). O patch mostra a intenção incremental: nós, relações, condições, fluxos, `draw_ref`, perguntas e decisões criados, removidos ou alterados. O JSON atual mostra o contrato que deve orientar os testes.

Se houver uma solicitação textual e um desenho alterado, combinar as fontes: o texto define o objetivo e o desenho fornece o fluxo observável. Não transformar todo desenho alterado em feature automaticamente; confirmar relevância pelo pedido, título, nós e relações. Se houver mais de um desenho candidato sem relação clara, pedir ao usuário que escolha antes de criar testes. Registrar no raciocínio qual modo foi usado, quais arquivos foram considerados e quais foram descartados.

Não tratar `git diff` como fonte única: alterações locais podem estar staged, unstaged ou ainda não rastreadas. Não perder mudanças do usuário nem reverter desenhos para obter uma comparação limpa.

## Fontes de verdade

Ler somente o contexto necessário:

- solicitação atual e critérios aceitos pelo usuário;
- `.stdd/config.json` e capacidades realmente configuradas;
- testes, contratos, schemas e fixtures existentes;
- código relacionado, apenas para entender interfaces e efeitos atuais;
- `.stdd/draws/<draw-id>.json` quando a solicitação partir de um desenho informado ou identificado na triagem do Git;
- o diff do Git do desenho, quando a feature vier de uma alteração de fluxo;
- `draw_ref` apenas quando o subfluxo fizer parte do escopo.

Quando um nó possuir `questions`, ler todas as perguntas. Tratar `answer` preenchido como decisão explícita do usuário e perguntas sem resposta como requisito ainda aberto; não inventar respostas nem apagar perguntas respondidas do histórico.

Não converter Draw em documentação duplicada. O JSON e os testes permanecem fontes diretas.

## Preflight

1. Executar a triagem da entrada e conferir o estado do Git, preservando alterações do usuário.
2. Quando a origem for um desenho, validar que todos os nós, relações, etapas de fluxo e `draw_ref` relevantes podem ser resolvidos; ler perguntas e decisões registradas.
3. Localizar testes e símbolos relacionados.
4. Identificar linguagem, framework de teste, banco e integrações externas.
5. Confirmar quais runners estão realmente disponíveis; capacidade não confirmada é `unavailable`.
6. Definir comportamento de sucesso, erros, limites, efeitos colaterais e riscos.
7. Escolher as categorias de teste proporcionais ao risco.

## Símbolos obrigatórios e gate do Draw

Toda especificação de teste que tocar um nó de Draw deve preservar a rastreabilidade até um símbolo real. Para cada nó implementado ou alterado, consultar a análise estática, associar no próprio nó um `code_refs` com `symbol` ou `qualified_name` comprovado e manter o `test_ref`/`test_refs` do cenário quando existir. Nunca usar símbolo genérico, placeholder ou associação em um nó diferente só para satisfazer o contrato.

Quando for necessário criar ou corrigir uma associação, usar obrigatoriamente a linha de comando: primeiro executar `stdd draw symbols` para localizar o símbolo real e seu `qualified_name`; depois gravar a associação com `stdd draw associate-reference --draw-id <draw-id> --node-id <node-id> --qualified-name <qualified-name>` (ou `--batch-json` para várias associações). Usar exatamente o símbolo retornado pela análise estática. Não editar `code_refs` manualmente no JSON nem usar a interface para criar a associação. `stdd draw symbols` serve para consultar e validar; ele não grava alterações.

Antes de concluir a especificação, executar `stdd test`. Esse comando verifica os Draws e bloqueia o resultado quando algum nó de nível 2, 3 ou 4 não possui símbolo associado (`draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` ou `draw.empty_node_symbol`). Corrigir a associação no nó correto e repetir o comando antes de declarar a tarefa concluída. Para uma funcionalidade explicitamente não implementada, não inventar símbolo: mantê-la terminal no grupo próprio e reportar a pendência em vez de tratá-la como teste aprovado.

Durante a investigação, usar `stdd draw symbols` para listar somente os símbolos e nós sem associação; esse comando não executa suítes, contrato, backlog ou adapter. Usar o `stdd test` completo somente como gate final.

## Contrato de testes

Não limitar a estratégia a testes funcionais, mas também não criar uma suíte por obrigação. Avaliar o risco da superfície e selecionar uma cobertura proporcional, somente com categorias aplicáveis:

| Categoria | Exigir quando |
| --- | --- |
| Unitário | regra isolável, transformação, validação ou erro local |
| Integração | dois componentes reais precisam colaborar |
| Contrato | API, evento, schema, SDK ou resposta externa possui formato estável |
| Regressão | existe bug ou comportamento anterior que não pode retornar |
| End-to-end | o valor depende de várias etapas do sistema |
| Banco | migrations, constraints, funções, triggers, RLS ou transações importam |
| Performance | latência, throughput, memória ou volume possui objetivo mensurável |
| Segurança | autenticação, autorização, entrada hostil, segredo ou exposição de dados muda |
| Isolamento | tenants, testes paralelos, dados, processos ou integrações não podem vazar estado |
| Pentest | há superfície atacável e ambiente explicitamente autorizado |
| Teste live | uma integração com IA ou serviço externo precisa provar o contrato real |
| Revisão visual | a mudança é principalmente frontend, layout, interação visual ou renderização |
| Documentação | o Markdown possui comandos executáveis, schema ou contrato que pode quebrar |

Frontend não exige teste automatizado por padrão. Criar teste quando houver lógica crítica, transformação de dados, estado complexo, acessibilidade, segurança ou impacto de negócio; para renderização e layout, registrar revisão visual humana. Markdown não exige teste automatizado quando é apenas documentação.

### Teste live de inteligência artificial

Para código que chama um provedor de IA, planejar camadas separadas:

1. unitário sem rede, com mock do transporte;
2. contrato offline com fixture real sanitizada;
3. teste live opt-in, chamando o provedor real;
4. avaliação semântica probabilística, quando relevante, separada do contrato determinístico.

O teste live deve usar entrada pequena, timeout, limite de chamadas e credencial somente por variável de ambiente. Validar transporte, status, JSON, schema, normalização, campos obrigatórios e limites; não exigir igualdade exata de texto livre. Ausência de credencial ou rede deve produzir `not_executed` com motivo, nunca `passed`. Não registrar prompt privado, token, chave ou resposta sensível.

### Banco de dados e pgTAP

Em PostgreSQL, considerar pgTAP para validar schema, constraints, índices, funções, triggers, permissões e RLS. Executar em banco isolado de teste após migrations e antes do cleanup. Nunca apontar para produção. Se pgTAP ou o banco não estiver disponível, registrar `not_executed` e a pré-condição ausente.

### Testes não funcionais

- Performance: definir baseline, carga, aquecimento, repetições, percentil e limite antes de executar.
- Segurança: testar autorização negativa, validação de entrada, segredos, dependências e falha segura.
- Isolamento: provar ausência de vazamento entre tenants, casos, workers e execuções paralelas.
- Pentest: executar somente em alvo local ou ambiente autorizado, com escopo, intensidade e cleanup definidos.

## Fluxo de especificação

1. Escrever uma matriz curta de comportamento no raciocínio de trabalho: cenário, entrada, resultado, erro e efeito.
2. Reutilizar o padrão de testes da stack; não criar framework paralelo.
3. Criar primeiro os testes de sucesso, erro, limites e falha segura aplicáveis ao risco; não fabricar cenários para superfícies sem comportamento testável.
4. Usar fakes ou fixtures para serviços externos na suíte determinística.
5. Separar testes caros ou online em suíte identificável.
6. Executar os testes novos e confirmar estado vermelho pelo motivo correto.
7. Executar testes relacionados para distinguir falha nova de baseline preexistente.
8. Não alterar produção para fazer o teste passar. Se a validação for visual ou documental, registrar a evidência adequada em vez de criar um teste artificial.

Usar `stdd test` como alias global para confirmar que todas as suítes configuradas continuam executáveis. Uma feature pode começar pelos testes relacionados, mas não deve ser apresentada como validada globalmente sem essa execução agregada.

## Criação interativa usando os comandos

O comando entrega o contexto; a conversa define o comportamento. Em uma sessão de especificação, trabalhar em incrementos pequenos e confirmar cada cenário antes de gravá-lo:

1. Atualizar o backlog com `stdd backlog generate` quando o Draw tiver mudado.
2. Executar `stdd backlog test` e ler a task recebida, incluindo o nó pai, a subtask atual, as demais subtasks, perguntas, respostas e símbolos. Não escolher outra task por conta própria nem começar pela implementação.
3. Se a task recebida for `backlog-bootstrap-task`, preparar somente a estrutura mínima do projeto com as evidências locais, concluir a task e voltar ao loop. Não criar testes de produto nessa etapa.
4. Apresentar ao usuário uma matriz curta do cenário atual: papel, pré-condições, entrada, resultado esperado, erro ou limite, efeito colateral e subfluxos cobertos. Perguntar somente as decisões que ainda estiverem abertas; não inventar regra, permissão, dado ou integração.
5. Depois da confirmação, criar ou ajustar o teste executável correspondente e executar o runner focado. A falha inicial é esperada quando o comportamento ainda não existe, mas deve falhar pela razão confirmada; uma falha de ambiente, contrato ou cenário deve ser corrigida ou reportada antes de avançar.
6. Mostrar o resultado e perguntar se o cenário está correto ou precisa de ajuste. Repetir os passos 4 e 5 para sucesso, erro, limites, segurança e cada subfluxo aplicável. Um arquivo de teste pode conter várias funções, mas cada função deve cobrir um comportamento observável e rastreável ao nó.
7. Quando todos os cenários da task estiverem especificados e executados, registrar a evidência, associar `test_ref` ou `test_refs` quando for útil e executar `stdd backlog complete <task-id>` usando exatamente o ID retornado por `stdd backlog test`.
8. Repetir `stdd backlog test` para a próxima task. Só depois de concluir a fase de testes usar `stdd backlog task`; se ele retornar `backlog-test-required`, voltar à fase de testes e não alterar produção.

O fluxo interativo é incremental: não criar uma suíte inteira baseada em suposições antes de obter confirmação. `stdd backlog test` não é um prompt conversacional adicional; ele entrega uma unidade de trabalho, e o agente deve conduzir a confirmação dos cenários com o usuário antes de escrever cada grupo de testes. Ao final, executar `stdd test` e registrar separadamente `stdd log "Especifica testes interativamente para a task <task-id>" --type teste`.

## Fase de testes do backlog

Quando a task vier de `stdd backlog test`, trabalhar somente na especificação executável: criar ou ajustar os testes do nó de nível 2 e de todos os subfluxos que ele agrega. Não alterar código de produção nessa fase. `test_ref` ou `test_refs` podem ser associados ao nó quando houver uma referência técnica útil, mas não são obrigatórios para marcar o checklist. Depois de salvar o Draw, executar a análise estática quando disponível e executar `stdd backlog complete <task-id>`. A mesma task será liberada para implementação por `stdd backlog task`.

O backlog também expõe `phase_checklists.test` e `phase_checklists.implementation`. O checklist de teste vem primeiro; a marcação manual é válida mesmo quando a análise estática estiver indisponível. `test_ref` e a análise continuam sendo evidências complementares, e o item pode ser desfeito no viewer para indicar que o teste deixou de estar concluído.

Se `stdd backlog task` retornar `kind: "backlog-test-required"`, não implementar ainda: iniciar ou retomar `stdd backlog test` e manter a task sem conclusão até que a evidência seja comprovada.

## Clareza dos testes

- Nomear cada teste pelo comportamento observável.
- Em Python, usar docstring de exatamente duas linhas curtas: o que é testado e como o cenário é exercitado.
- Em testes longos ou end-to-end, inserir comentários breves de etapa antes de grupos coerentes de ações e asserções.
- Não comentar detalhes óbvios nem documentar cada chamada.
- Não exigir docstrings em funções de produção.

## Evidência e encerramento

Registrar para cada suíte: comando, ambiente, status, duração, exit code e falha relevante. Usar apenas `passed`, `failed`, `blocked` ou `not_executed`. Não tratar teste ausente ou não executado como sucesso.

Ao alterar testes, registrar separadamente:

```bash
stdd log "Especifica comportamento da feature" --test
```

Não combinar esse log com implementação. Informar arquivos de teste criados, comandos executados, resultado vermelho esperado, suítes ainda não executadas e pré-condições externas.

## Regras de interação

Use `backlog test` e `backlog task` para receber uma única task; cada conclusão exige o ID individual em `backlog complete`. Testes de integração devem provar API, persistência, validação e efeitos reais, não apenas mocks ou renderização. Erros são cenários condicionais e folhas `Não implementado` ficam fora do escopo.
