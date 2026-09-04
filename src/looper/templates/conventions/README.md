# Convenções do projeto

Esta pasta é a memória evolutiva das convenções e documentações técnicas específicas do projeto. Mantenha o
`AGENTS.md` curto e registre aqui orientações que não precisam ser carregadas em toda tarefa.

O `AGENTS.md` deve conter somente a visão geral do projeto, operação, escopo e rastreabilidade.
Contratos, arquitetura detalhada e outras documentações técnicas específicas e reutilizáveis
devem ficar nesta pasta; decisões visuais ficam no `.looper/design.html` e o comportamento
do sistema fica documentado nos Draws.

## O que é uma convenção

Uma convenção é uma orientação técnica específica, confirmada e reutilizável sobre como
implementar ou manter código e infraestrutura. Ela normalmente nasce de uma dificuldade
real, como um bug difícil de corrigir, uma integração incomum ou uma forma não óbvia de
implementar uma capacidade.

Exemplos: como criar um painel dentro da área administrativa, como estruturar um tipo de
integração externa ou como evitar um bug conhecido ao configurar uma infraestrutura.

Documentações técnicas específicas também pertencem aqui quando forem necessárias para
reutilizar uma implementação, como contratos de APIs/apps externos, pré-condições de uma
integração ou instruções de infraestrutura. O arquivo deve continuar focado em um assunto.

Não são convenções ou documentações desta pasta: a linguagem geral do sistema, regras de negócio, princípios genéricos
de programação, histórico de uma tarefa ou workaround temporário sem reutilização.

## Como usar

- Crie um arquivo Markdown por assunto, com nome curto e descritivo, como `painel-admin.md`,
  `contrato-pagamento.md`, `testes.md` ou `infraestrutura.md`.
- Atualize este índice sempre que criar, renomear ou remover uma convenção.
- Todo arquivo de convenção deve começar com metadados `name` e `description` curtos,
  no mesmo padrão das skills. O `name` aparece como título do catálogo e a `description`
  como resumo; o link aponta para o arquivo completo.
- Leia somente o arquivo relacionado à tarefa atual.
- Registre apenas orientações técnicas específicas, confirmadas e reutilizáveis; não registre
  hipóteses, segredos, IDs de execução, regras de negócio ou detalhes temporários.
- Quando uma convenção mudar comportamento documentado, atualize também o Draw correspondente
  e associe os símbolos reais da implementação.

## Convenções disponíveis

- [Especificação dos Draws antes da implementação](draw-specification-before-implementation.md)
- [Dados dinâmicos de telas](dynamic-screen-data.md)
