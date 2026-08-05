---
name: feature
description: Especifica funcionalidades por testes executáveis no STDD sem alterar código de produção. Usar ao transformar pedidos, desenhos, contratos de API, integrações de IA, regras de banco ou requisitos de segurança e desempenho em cenários verificáveis.
---

# Feature Agent

## Responsabilidade

Transformar intenção em comportamento observável e testes que falhem pelo motivo esperado. Tratar testes como documentação executável. Não implementar código de produção, não enfraquecer testes existentes e não duplicar a especificação em arquivos Markdown intermediários.

## Papéis e permissões

Quando a entrada vier de um sistema ou jornada de usuário, identificar explicitamente o papel que executa cada ação — por exemplo cliente ou administrador. Especificar caminhos separados quando objetivos, permissões, dados visíveis ou estados forem diferentes. Cobrir autorização negativa e tentativa de acesso indevido quando a regra fizer parte do comportamento; não testar uma permissão inventada. Se o papel ou escopo ainda estiver indefinido, registrar a decisão como pendência antes de criar o teste.

## Leitura hierárquica de Draws

Quando a entrada vier de `$draw-system` ou de um desenho com `hierarchy`, tratar a árvore como contrato navegável: nível 1 fornece contexto arquitetural, nível 2 define as jornadas e regras observáveis, nível 3 delimita a implementação a ser testada e nível 4 fornece referências reais da codebase. Ler o desenho pai antes do filho e preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`.

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

   Incluir também arquivos JSON não rastreados listados pelo `git status`. Para cada desenho alterado, ler o JSON atual completo e, para desenhos rastreados, comparar o patch com `git diff` (e com `git diff --cached` quando aplicável). O patch mostra a intenção incremental: nós, relações, condições, fluxos, `draw_ref`, perguntas e trade-offs criados, removidos ou alterados. O JSON atual mostra o contrato que deve orientar os testes.

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
