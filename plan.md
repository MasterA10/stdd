# Arquitetura CLI-First do Framework

## 1. Papel do CLI

O CLI será a principal interface do framework.

O usuário deverá conseguir realizar todo o fluxo de desenvolvimento por meio dele:

* iniciar ou analisar um projeto;
* identificar linguagens e tecnologias;
* configurar os adaptadores necessários;
* gerar testes com auxílio de agentes;
* explicar automaticamente as funções usadas nos testes;
* executar toda a bateria de testes;
* analisar trade-offs;
* implementar funcionalidades;
* corrigir bugs;
* revisar alterações com suporte a git diff;
* integrar com Git local e GitHub remoto;
* detectar segredos e variáveis sensíveis antes de commits e pushes;
* registrar aprendizado, decisões e retrabalho quando o recurso estiver habilitado;
* aplicar quality gates.

O CLI não será apenas um instalador ou executor de scripts. Ele será o **orquestrador do processo de desenvolvimento**.

Seu papel será decidir quando usar:

1. análise determinística;
2. scripts;
3. ferramentas nativas da linguagem;
4. agentes de IA;
5. combinação entre scripts e agentes.

A regra principal será:

> Sempre que uma tarefa puder ser resolvida de forma segura e previsível por scripts, não será necessário utilizar um agente de IA.

---

# 2. Camadas da solução

O framework terá quatro camadas principais.

## 2.1 CLI principal

Responsável por:

* interpretar comandos;
* carregar a configuração do projeto;
* selecionar os adaptadores;
* chamar scripts;
* ativar agentes;
* controlar o estado do fluxo;
* consolidar resultados;
* gerar relatórios.

O registro de aprendizado será opcional e não poderá bloquear comandos de
desenvolvimento, testes, commits, pushes, CI ou quality gates.

## 2.2 Adaptadores da stack

Cada adaptador compreenderá as particularidades de uma tecnologia.

Exemplos:

* Python;
* TypeScript;
* JavaScript;
* PHP;
* Java;
* Go;
* C#;
* Rust;
* PostgreSQL;
* MySQL;
* MariaDB;
* MongoDB;
* Redis;
* React;
* Next.js;
* FastAPI;
* Django;
* Laravel;
* Spring;
* NestJS.

Os adaptadores não precisam implementar o framework inteiro. Eles apenas precisam ensinar ao núcleo:

* como identificar a tecnologia;
* como analisar seus arquivos;
* como extrair funções e classes;
* como identificar tipos;
* como executar os testes;
* como interpretar os resultados;
* como escrever comentários válidos;
* como localizar configurações;
* como gerar scripts específicos.

## 2.3 Scripts determinísticos

Os scripts executarão operações previsíveis, como:

* localizar arquivos;
* identificar manifests;
* executar testes;
* analisar AST;
* extrair símbolos;
* extrair diffs e histórico de commits via Git (`git diff`, `git log`, `git blame`);
* atualizar blocos gerados;
* consolidar relatórios;
* validar arquivos modificados;
* atualizar o índice local.

### Detecção de segredos e variáveis sensíveis

O núcleo também deverá fornecer um scanner determinístico para impedir que
credenciais sejam enviadas ao GitHub ou a qualquer repositório remoto.

Comando:

```bash
framework security scan
```

O scanner deverá:

* verificar a existência de `.gitignore` e se ele ignora efetivamente `.env`,
  `.env.*` e arquivos equivalentes de credenciais;
* permitir e validar exceções seguras como `.env.example`, `.env.sample` e
  `.env.template`;
* detectar arquivos sensíveis já rastreados com `git ls-files`;
* analisar o workspace, o diff staged e o diff que será enviado ao remoto;
* analisar, por padrão, objetos alcançáveis no histórico local do Git;
* identificar chaves privadas, tokens conhecidos, JWTs, credenciais cloud,
  atribuições suspeitas (`API_KEY`, `SECRET`, `PASSWORD`, `TOKEN`, `ACCESS_KEY`) e
  strings de alta entropia;
* usar regras específicas dos adaptadores sem exigir um agente de IA;
* redigir valores e exibir somente caminho, linha, tipo e fingerprint não reversível;
* retornar código de saída diferente de zero quando encontrar um segredo novo;
* aceitar allowlists por fingerprint, com justificativa e expiração, nunca por valor
  literal.

Referências a `process.env`, `os.getenv`, secret managers e mecanismos equivalentes
serão consideradas o caminho normal. O scanner deverá tratar valores em
`.env.example` como fictícios e bloquear valores reais. Encontrar um segredo no
histórico deverá gerar instruções de revogação e rotação; apagar o valor em um novo
commit não será considerado correção suficiente.

`framework check` deverá executar esse scanner junto com duplicação, complexidade,
classes Deus, funções extensas, tipos e testes. O mesmo comando deverá poder ser
executado em um hook `pre-commit`, `pre-push` e no CI.

Esses scripts poderão ser:

* Bash;
* PowerShell;
* Python;
* JavaScript;
* binários;
* scripts nativos da própria stack.

O framework não deverá obrigar um projeto JavaScript a instalar Python apenas para executar uma tarefa simples.

A ferramenta escolherá o script mais adequado para o sistema operacional e para a stack detectada.

## 2.4 Comandos agentic

Algumas tarefas exigem raciocínio contextual e não podem ser resolvidas apenas com scripts.

Exemplos:

* interpretar uma descrição de feature;
* criar um teste inicial;
* analisar alternativas arquiteturais;
* implementar uma regra de negócio;
* reproduzir um bug descrito em linguagem natural;
* avaliar riscos de uma alteração;
* explicar inconsistências.

Essas tarefas serão executadas por skills ou comandos instalados para o agente escolhido.

## 2.5 Aprendizado opcional e memória de sessões

O framework oferecerá o comando `framework learn` para aprender com o processo de
desenvolvimento. O recurso será opt-in:
quando desabilitado, nenhum hook será instalado e a ausência de registros não
afetará o fluxo normal.

Comandos previstos:

```bash
framework learn                 # resume a sessão atual ou a última sessão
framework learn review          # revisa lições propostas
framework learn readiness --worktrees
                                # diagnostica riscos, sem autorizar paralelização
framework quiz generate          # gera/atualiza o banco de perguntas
framework quiz run               # executa uma avaliação da codebase
framework quiz refresh            # atualiza perguntas ligadas a símbolos alterados
framework quiz export --format yaml
                                # exporta perguntas para revisão/versionamento
```

O resumo deverá separar:

* o que funcionou;
* o que falhou;
* decisões e trade-offs;
* retrabalho detectado como sinal de aprendizado;
* causa provável, explicitamente marcada como inferência;
* evidências em commits, diffs, testes, gates e tarefas;
* lições propostas;
* próximos experimentos.

O detector de retrabalho deverá identificar, como indícios, alterações repetidas no
mesmo arquivo ou símbolo, revert/reaplicação, tarefas reabertas, tentativas após
falhas de testes/gates e mudanças que desfazem decisões anteriores. O resultado
deverá informar confiança e evidências, sem atribuir culpa ou afirmar causalidade
sem suporte. Esses sinais servirão para evitar repetir erros; não serão usados
isoladamente para decidir se o desenvolvimento pode ser paralelizado.

### Eventos e hooks de sessão

Quando habilitado, o framework deverá capturar os eventos:

```text
session.start
session.checkpoint
session.compacted
session.resumed
session.close
```

Integrações com Codex, Claude/Cloud Code e outros agentes utilizarão um contrato
comum de eventos, com adaptadores específicos para cada host. O evento de
compactação deverá salvar um checkpoint antes de a sessão ser resumida; o evento de
retomada deverá reconectar a sessão ao mesmo identificador. Se o host não oferecer
hooks, o CLI usará checkpoints em comandos, commits e encerramentos detectáveis e
marcará a cobertura como parcial.

Cada evento deverá conter `session_id`, `event_id`, timestamp, agente, branch,
worktree, commit-base, tarefas, arquivos/símbolos afetados, comandos, gates e
referências de evidência. Prompts brutos, segredos e dados sensíveis deverão ser
redigidos antes da persistência. Os eventos serão append-only e os resumos ficarão
separados dos fatos.

`framework learn review` será necessário antes de transformar uma lição em regra
permanente, instrução de agente ou alteração de processo. Nenhum `AGENTS.md`,
`CLAUDE.md`, código ou configuração de qualidade poderá ser alterado
silenciosamente pelo recurso.

### Avaliação de conhecimento da codebase

O módulo de perguntas será opcional. `quiz run`, `quiz sync`, a validação, a
redaction e a aplicação da prova serão determinísticos e não dependerão de um
agente de IA. `quiz generate` poderá delegar inferência para um executável local de
linha de comando (Codex, Claude, Cloud, Antigravity ou outro configurado), recebendo
apenas contexto redigido; deverá existir fallback determinístico ou local para
manter o quiz utilizável sem esse comando. Não haverá provider HTTP/API no core. O
módulo poderá construir perguntas a partir
do AST, grafo de dependências, documentação, specs, testes, contratos, decisões,
trade-offs, regras de negócio e histórico de alterações.

Categorias mínimas:

* arquitetura e limites entre módulos;
* modularização, coesão e acoplamento;
* boas práticas e convenções da stack;
* escolhas técnicas e trade-offs;
* regras de negócio e invariantes;
* testes, contratos e quality gates;
* segurança, configuração e operação.

Cada pergunta deverá conter uma única resposta correta, de três a cinco alternativas,
uma explicação curta, dificuldade, categoria, versão e evidências. As perguntas e
explicações deverão ser unidades pequenas de estudo: uma pergunta por objetivo e
explicação de até 80 palavras.

O SQLite local (`.framework/index.db`) será a fonte de relacionamento. As tabelas
`symbols` e `symbol_relations` deverão ser reconstruídas por `framework scan` e
`framework sync`, registrando funções, métodos, classes, documentação disponível,
métricas de complexidade, testes e relações de uso.
deverão associar perguntas e itens de conhecimento a `symbol_id`, módulo, regra,
teste, contrato, decisão e fingerprint da fonte. O comando `framework quiz refresh`
deverá marcar como `needs_review` qualquer pergunta cujo símbolo ou regra tenha
mudado, preservando tentativas antigas e evitando que uma resposta obsoleta seja
tratada como conhecimento atual. O conteúdo poderá ser exportado em YAML para
revisão humana e versionamento.

O resultado da prova deverá registrar perguntas apresentadas, respostas, acertos,
tentativas, confiança e data. O resultado é educacional e informativo; não bloqueia
implementação, CI ou paralelização. A paralelização futura dependerá de arquitetura,
plano, fronteiras de responsabilidade, contratos e método validados; o quiz apenas
mede e revela lacunas de conhecimento.

---

# 3. Inicialização do projeto

## Comando

```bash
framework init
```

O comando deverá funcionar tanto para projetos existentes quanto para projetos ainda não criados.

---

## 3.1 Inicialização em codebase existente

Quando o diretório já possuir código, o CLI executará uma análise automática.

```bash
framework init --here
```

A análise deverá identificar, quando possível:

### Linguagens

* linguagens principais;
* linguagens secundárias;
* versões;
* distribuição aproximada por diretórios;
* projetos dentro de monorepos.

### Frameworks

* framework principal;
* frameworks auxiliares;
* bibliotecas de teste;
* ORMs;
* ferramentas de build;
* ferramentas de lint;
* ferramentas de tipagem.

### Bancos e armazenamento

* PostgreSQL;
* MySQL;
* MariaDB;
* SQLite;
* MongoDB;
* Redis;
* bancos vetoriais;
* armazenamento em arquivos;
* serviços externos.

### Infraestrutura

* Docker;
* Docker Compose;
* Kubernetes;
* filas;
* workers;
* cron jobs;
* GitHub Actions;
* outros pipelines de CI/CD.

### Estrutura de testes

* frameworks de teste existentes;
* diretórios de teste;
* testes unitários;
* testes de integração;
* testes de banco de dados;
* testes de inferência (live / provedores de IA);
* testes end-to-end;
* scripts já disponíveis.

A detecção poderá analisar:

* extensões de arquivos;
* manifests;
* lockfiles;
* arquivos de configuração;
* dependências;
* Dockerfiles;
* arquivos Compose;
* migrations;
* configuração de ORM;
* scripts de package manager;
* pipelines de CI.

Exemplos de arquivos detectáveis:

```text
package.json
pnpm-lock.yaml
pyproject.toml
requirements.txt
pom.xml
build.gradle
composer.json
go.mod
Cargo.toml
docker-compose.yml
pytest.ini
vitest.config.ts
jest.config.js
phpunit.xml
```

Ao final, o CLI apresentará um resumo para validação:

```text
Projeto detectado

Tipo: codebase existente
Estrutura: monorepo

Aplicações:
  backend:
    linguagem: Python 3.12
    framework: FastAPI
    testes: Pytest

  frontend:
    linguagem: TypeScript
    framework: React
    testes: Vitest

Bancos:
  principal: PostgreSQL
  cache: Redis

Infraestrutura:
  Docker Compose
  GitHub Actions

Deseja salvar esta configuração? [S/n]
```

A análise automática nunca deverá ser tratada como verdade absoluta.

O usuário poderá corrigir qualquer detecção antes que a configuração seja salva.

---

## 3.2 Inicialização de projeto novo

Quando o diretório estiver vazio, o CLI iniciará um fluxo guiado.

```bash
framework init
```

Perguntas possíveis:

```text
Qual será a linguagem principal?
Qual framework será utilizado?
O projeto terá frontend e backend?
Qual banco de dados será utilizado?
Qual framework de testes será utilizado?
O projeto será um experimento, MVP ou produto?
```

Também será possível inicializar a partir de um arquivo:

```bash
framework init --from requirements.md
```

Nesse caso, um agente poderá interpretar o documento e propor uma configuração.

A configuração somente será salva depois da validação do usuário.

---

## 3.3 Resultado da inicialização

O comando poderá criar:

```text
.framework/
├── project.yml
├── adapters/
├── scripts/
├── agents/
├── security/
├── quality/
├── learning/
├── cache/
├── history/
├── generated/
└── index.db
```

### `project.yml`

Contém o mapa tecnológico detectado.

### `adapters/`

Contém os adaptadores habilitados para o projeto.

### `scripts/`

Contém os scripts gerados para execução e análise.

### `agents/`

Contém os comandos, prompts ou skills instalados para o agente escolhido.

### `security/`

Contém a política de scanning e a allowlist por fingerprint, sem armazenar valores
secretos.

### `learning/`

Contém eventos de sessão, lições propostas/revisadas e evidências de retrabalho,
sem prompts brutos ou segredos. A persistência só é criada quando o recurso estiver
habilitado ou for solicitado explicitamente.

### `history/`

Contém registros de bugs e alterações comportamentais.

### `index.db`

Contém o índice de funções, classes, testes, tipos e relações.

---

# 4. Configuração gerada

A configuração deverá ser produzida automaticamente e exigir poucas alterações manuais.

Exemplo:

```yaml
version: 1
profile: mvp
mode: brownfield

applications:
  backend:
    path: apps/backend
    languages:
      - python
    frameworks:
      - fastapi
    tests:
      unit:
        command: pytest tests/unit
      integration:
        command: pytest tests/integration

  frontend:
    path: apps/frontend
    languages:
      - typescript
    frameworks:
      - react
      - vite
    tests:
      unit:
        command: pnpm vitest run

datastores:
  - id: primary
    engine: postgresql
    test_command: pytest tests/database

  - id: cache
    engine: redis

agent:
  integration: selected-agent

documentation:
  test_explanations: header
  include_builtin_functions: true
  include_external_functions: true
  include_project_functions: true

security:
  secret_scan: true
  scan_history: true
  scan_remote_diff: true
  env_files:
    - .env
    - .env.*
  safe_examples:
    - .env.example
    - .env.sample
    - .env.template
  allowlist: .framework/security/allowlist.yml

learning:
  enabled: false
  capture_events: false
  quiz_enabled: false
  quiz_source: index.db
  quiz_export: .framework/learning/questions.yml
  redact_sensitive_data: true
  retention_days: 365

scripts:
  preferred: auto
```

O usuário não deverá precisar escrever esse arquivo do zero.

---

# 5. Instalação automática dos comandos agentic

O framework não terá um comando separado chamado `skill generate`.

As skills e os comandos serão instalados automaticamente durante:

```bash
framework init
```

Também poderão ser atualizados com:

```bash
framework update
```

O CLI detectará qual agente está sendo utilizado e instalará os artefatos no formato esperado por ele.

Os arquivos poderão incluir:

* `SKILL.md`;
* comandos Markdown;
* prompts;
* instruções de execução;
* scripts SH;
* scripts PowerShell;
* templates;
* regras do projeto;
* referências ao CLI.

O conteúdo canônico permanecerá dentro de `.framework/agents`.

Os arquivos específicos de cada agente serão projeções desse conteúdo.

Isso evita manter manualmente diversas versões das mesmas instruções.

---

# 6. Criação de testes

## Comando

```bash
framework test create "descrição completa da feature e dos comportamentos esperados"
```

Exemplo:

```bash
framework test create \
  "Um cupom não pode reduzir o total do pedido abaixo de zero"
```

Esse comando funciona como uma especificação de testes. A descrição completa é
redigida em uma request e entregue a um agente local especializado, sem chamada
de API. O framework cria uma pasta sequencial em
`.framework/quality/features/NNN-nome-da-feature/` para os artefatos da operação.

O agente deverá:

1. localizar as funções relacionadas;
2. identificar o framework de testes;
3. identificar fixtures e helpers existentes;
4. criar um plano de testes e um checklist de qualidade;
5. criar todos os testes relevantes no padrão do projeto, não apenas um teste;
6. não implementar a funcionalidade;
7. não adicionar manualmente explicações das funções;
8. executar os testes criados;
9. confirmar que falham pelo motivo esperado;
10. apresentar o conjunto de testes para validação.

Os testes criados serão testes normais da linguagem, registrados em
`feature.json` junto com o plano e o checklist. A quantidade de arquivos e
cenários é decidida pelo agente conforme a complexidade da descrição.

Exemplo:

```typescript
test("não permite que o cupom torne o total negativo", () => {
  const order = createOrder({
    subtotal: 50
  });

  const total = calculateOrderTotal(order, {
    discount: 80
  });

  expect(total).toBe(0);
});
```

Nesse momento, o teste ainda não possuirá o cabeçalho explicativo.

---

## 6.1 Testes de inferência (live / APIs de IA)

Para aplicações que realizam inferência utilizando APIs de inteligência artificial (por exemplo, um chatbot chamando o Gemini para processar perguntas e transformar em respostas), é obrigatório a presença de testes do tipo **live**.

Esses testes devem:
* utilizar credenciais reais configuradas no ambiente de forma segura;
* chamar efetivamente os provedores externos de IA;
* verificar se o fluxo completo e os contratos de resposta (ex: schema de JSON retornado) permanecem válidos e funcionais, prevenindo quebras por mudanças silenciosas na API do provedor.

Para aplicações puramente lógicas e determinísticas (sem uso de IA para inferência), testes de inferência *live* não são exigidos.

---

# 7. Explicação automática das funções do teste

## Comando

```bash
framework test explain caminho/do/teste
```

Também poderá ser executado para toda a suíte:

```bash
framework test explain --all
```

Esse comando será preferencialmente determinístico.

O processo deverá:

1. analisar o arquivo de teste;
2. construir sua árvore sintática;
3. identificar todas as funções, métodos, construtores, hooks e assertions utilizados;
4. resolver aliases e imports;
5. remover símbolos repetidos;
6. localizar descrição e assinatura;
7. identificar os tipos de entrada;
8. identificar o tipo de saída;
9. inserir um único bloco explicativo;
10. validar que o arquivo continua sintaticamente correto.

---

## 7.1 Uma explicação por símbolo

Cada símbolo será explicado apenas uma vez dentro do arquivo.

Se `expect` for utilizado vinte vezes, ele aparecerá apenas uma vez no cabeçalho.

Se `createOrder` aparecer em vários testes diferentes, ele poderá aparecer uma vez em cada arquivo, pois cada teste deverá permanecer compreensível isoladamente.

Dentro de um mesmo arquivo:

```text
createOrder: uma explicação
expect: uma explicação
calculateOrderTotal: uma explicação
```

Não haverá uma explicação a cada chamada.

---

## 7.2 Tipos de símbolos explicados

O analisador deverá incluir:

* funções do projeto;
* métodos;
* classes;
* construtores;
* funções importadas;
* assertions;
* fixtures;
* hooks;
* decorators relevantes;
* funções da biblioteca padrão;
* helpers do framework de testes.

Estruturas da linguagem que não sejam funções não precisarão ser apresentadas como funções.

---

## 7.3 Fontes das explicações

A explicação poderá ser obtida de:

1. assinatura e tipos;
2. docstring ou comentário da função;
3. type definitions;
4. código-fonte local;
5. catálogo do adaptador;
6. documentação instalada com a dependência;
7. índice do framework;
8. inferência controlada por agente.

O uso de agente será a última opção.

O sistema não deverá inventar tipos ou comportamentos.

Quando não conseguir resolver uma informação, deverá indicar:

```text
Tipo de retorno: não resolvido
Descrição: não encontrada
```

O perfil do projeto decidirá se isso gera:

* informação;
* aviso;
* bloqueio.

---

## 7.4 Exemplo de cabeçalho gerado

```typescript
// @framework:explanations:start
//
// FUNÇÕES UTILIZADAS NESTE TESTE
//
// createOrder(input: CreateOrderInput): Order
// Cria uma entidade de pedido a partir dos dados fornecidos.
// Não persiste o pedido.
//
// calculateOrderTotal(
//   order: Order,
//   coupon: Coupon
// ): number
// Calcula o total do pedido depois da aplicação do cupom.
// Retorna um número maior ou igual a zero.
//
// expect<T>(actual: T): Matchers<T>
// Cria um conjunto de verificações para comparar o valor observado
// com o comportamento esperado.
//
// test(name: string, callback: () => void): void
// Registra um cenário de teste identificado por um nome.
//
// @framework:explanations:end
```

Em Python, o mesmo conteúdo será escrito utilizando comentários válidos em Python:

```python
# @framework:explanations:start
#
# FUNÇÕES UTILIZADAS NESTE TESTE
#
# create_order(input: CreateOrderInput) -> Order
# Cria uma entidade de pedido sem persistir seus dados.
#
# calculate_order_total(
#     order: Order,
#     coupon: Coupon
# ) -> Decimal
# Calcula o total do pedido e impede valores negativos.
#
# assert result == expected
# Verifica se o resultado corresponde ao valor esperado.
#
# @framework:explanations:end
```

---

## 7.5 Assinatura usada, não todas as sobrecargas

Quando uma função possuir várias assinaturas, o cabeçalho deverá priorizar a assinatura utilizada no teste.

Isso evita transformar a explicação em uma documentação extensa da biblioteca.

---

## 7.6 Modos de inserção

O projeto poderá escolher entre:

```yaml
documentation:
  test_explanations: header
```

Insere todas as explicações no cabeçalho.

```yaml
documentation:
  test_explanations: first-use
```

Insere a explicação antes da primeira utilização do símbolo.

```yaml
documentation:
  test_explanations: virtual
```

Não altera o arquivo. As explicações aparecem apenas no terminal ou relatório.

O modo padrão recomendado será `header`.

---

# 8. Sincronização das explicações

Quando uma função for modificada, sua explicação poderá ficar desatualizada.

O comando responsável por atualizar os blocos será:

```bash
framework sync
```

O comando deverá:

* reanalisar funções alteradas;
* atualizar assinaturas;
* atualizar tipos;
* atualizar descrições;
* remover símbolos que não são mais utilizados;
* adicionar novos símbolos;
* preservar o restante do teste;
* atualizar o índice local.

Os blocos gerados não deverão ser modificados manualmente.

O CLI poderá verificar isso por hash ou por comparação estrutural.

---

# 9. Execução unificada dos testes

## Comando

```bash
framework test
```

Esse será o alias principal para executar toda a bateria relevante de testes.

Também poderá ser escrito como:

```bash
framework test run
```

O CLI deverá ler a configuração e executar todos os runners necessários.

Exemplo de projeto:

```yaml
tests:
  - id: python-unit
    command: pytest tests/unit

  - id: python-database
    command: pytest tests/database

  - id: frontend-unit
    command: pnpm vitest run

  - id: api-integration
    command: pytest tests/integration

  - id: migrations
    command: ./scripts/test-migrations.sh
```

Ao executar:

```bash
framework test
```

O CLI poderá chamar:

```text
[1/5] Python unitários
[2/5] Banco de dados
[3/5] Frontend
[4/5] Integração da API
[5/5] Migrations
```

Ao final:

```text
Resultado geral

✓ Python unitários: 84 testes
✓ Banco de dados: 19 testes
✓ Frontend: 37 testes
✗ Integração da API: 2 falhas
✓ Migrations: 8 testes

Status final: falha
```

O processo deverá retornar um único exit code, adequado para CI/CD.

---

## 9.1 Escopos

```bash
framework test --unit
framework test --integration
framework test --database
framework test --security
framework test --performance
framework test --changed
framework test --all
```

### `--changed`

Executa os testes relacionados aos arquivos modificados.

### `--all`

Executa toda a suíte, incluindo verificações mais demoradas.

---

## 9.2 Scripts gerados

Durante a inicialização, o CLI poderá criar scripts como:

```text
.framework/scripts/test-all.sh
.framework/scripts/test-changed.sh
.framework/scripts/test-database.sh
.framework/scripts/test-all.ps1
```

O script será gerado de acordo com:

* sistema operacional;
* linguagem;
* package manager;
* estrutura do projeto;
* ferramentas já instaladas.

O CLI permanecerá como interface principal:

```bash
framework test
```

Os scripts existirão como implementação interna e também poderão ser usados diretamente no CI.

---

# 10. Aprovação dos testes

Antes da implementação, o usuário poderá aprovar o comportamento definido.

## Comando

```bash
framework test approve caminho/do/teste
```

Esse comando registra:

* hash do teste;
* data da aprovação;
* comportamento validado;
* perfil do projeto;
* testes relacionados.

Após qualquer alteração relevante no teste, a aprovação será invalidada.

Em projetos do perfil Experimento, essa etapa poderá ser opcional.

Em projetos MVP ou Produto, poderá ser obrigatória para funções de negócio.

---

# 11. Análise de trade-offs

## Comando

```bash
framework tradeoff "descrição da decisão"
```

Exemplo:

```bash
framework tradeoff \
  "Usar eventos assíncronos ou chamada síncrona para processar pagamentos"
```

Esse será um comando agentic e somente de leitura.

Ele não poderá modificar o código.

A análise deverá considerar:

* complexidade;
* velocidade de implementação;
* custo operacional;
* dependências;
* acoplamento;
* capacidade de teste;
* desempenho;
* consistência;
* observabilidade;
* segurança;
* lock-in;
* manutenção;
* adequação ao estágio do produto;
* impacto sobre a equipe;
* facilidade para agentes de IA.

Exemplo de resultado:

```text
Decisão analisada:
Processamento síncrono versus eventos assíncronos.

Processamento síncrono

Vantagens:
- implementação inicial mais simples;
- depuração mais direta;
- menor infraestrutura;
- adequado para o MVP atual.

Desvantagens:
- maior latência percebida;
- acoplamento com o serviço de pagamento;
- falhas externas afetam diretamente a requisição.

Eventos assíncronos

Vantagens:
- melhor isolamento de falhas;
- maior capacidade de escala;
- possibilidade de retentativas.

Desvantagens:
- exige fila e worker;
- aumenta a complexidade de testes;
- exige idempotência e observabilidade.

Recomendação atual:
Utilizar processamento síncrono no MVP, mantendo uma interface
que permita migração futura para eventos.

Condição para reconsiderar:
- aumento relevante no volume;
- latência do provedor;
- necessidade de retentativa automática.
```

O comando deverá considerar o perfil do projeto.

Uma arquitetura ideal para um sistema crítico pode ser inadequada para um MVP de validação.

---

# 12. Implementação

## Comando

```bash
framework implement
```

Também poderá receber um teste ou escopo:

```bash
framework implement tests/orders/discount.test.ts
```

O comando ativará um agente responsável por implementar o comportamento aprovado.

Antes de alterar o código, o agente deverá verificar:

1. se existe teste;
2. se o teste foi explicado;
3. se o teste falha;
4. se a falha ocorre pelo motivo esperado;
5. se o teste exige aprovação;
6. quais funções serão afetadas;
7. quais convenções o projeto utiliza.

Durante a implementação, o agente deverá:

* realizar a menor alteração funcional necessária;
* evitar alterar testes aprovados;
* respeitar tipos existentes;
* atualizar descrições das funções alteradas;
* evitar dependências desnecessárias;
* executar os testes relacionados;
* executar os gates do perfil.

O agente não poderá alterar um teste aprovado apenas para fazer a implementação passar.

Quando o teste estiver incorreto ou impossível de satisfazer, o comando deverá interromper a implementação e apresentar o conflito.

## 12.2 Catálogo e explicação obrigatória de funções

O processo de implementação terá um pós-fluxo determinístico, independente do
agente local utilizado:

1. antes da execução, `framework implement` e `framework fix` capturam um snapshot
   dos símbolos de código-fonte;
2. depois da execução, `framework scan` atualiza o catálogo SQLite de funções,
   métodos e classes, incluindo assinatura, localização, métricas, fingerprint e
   resumo curto;
3. o framework compara os fingerprints e identifica símbolos novos ou alterados;
4. cada símbolo novo ou alterado deverá possuir uma docstring ou JSDoc concisa;
5. o resultado registra os resumos encontrados em `function_documentation` e
   bloqueia a operação quando houver símbolo sem resumo.

O agente deverá informar resumidamente o que cada função criada ou alterada faz,
mas a fonte verificável é a documentação no próprio código e o registro em
`.framework/index.db`. O mecanismo não depende do texto livre retornado pelo
agente e funciona com Codex, Claude, Antigravity ou outro executável local.

---

## 12.1 Resultado da implementação

```text
Implementação concluída

Teste de origem:
  tests/orders/discount.test.ts

Funções criadas:
  calculateOrderTotal()

Funções alteradas:
  applyCoupon()

Testes executados:
  8 relacionados
  8 aprovados

Novas dependências:
  nenhuma

Alterações de comportamento:
  o total mínimo de um pedido agora é zero

Quality gates:
  aprovados
```

---

# 13. Resolução de bugs

O nome recomendado para o comando será:

```bash
framework fix
```

É mais curto e permite resolver bugs, regressões e comportamentos incorretos.

Exemplo:

```bash
framework fix \
  "O sistema permite aplicar o mesmo cupom duas vezes ao pedido"
```

O fluxo obrigatório será:

1. interpretar o bug;
2. localizar funções e testes relacionados;
3. reproduzir o bug em um novo teste;
4. executar o teste;
5. confirmar o estado vermelho;
6. apresentar a reprodução;
7. corrigir a implementação;
8. executar os testes relacionados;
9. executar testes de regressão;
10. atualizar o índice das funções alteradas;
11. registrar a alteração comportamental.

---

## 13.1 Registro da alteração na função

Não é recomendável adicionar um changelog completo dentro do comentário da função.

Isso faria os comentários crescerem indefinidamente.

O framework deverá utilizar um identificador estável para cada função:

```typescript
/**
 * @framework-id orders.apply-coupon
 *
 * Aplica um cupom válido ao pedido.
 * Recebe um pedido e um cupom e retorna o pedido atualizado.
 */
function applyCoupon(
  order: Order,
  coupon: Coupon
): Order {
  // ...
}
```

Quando o bug for corrigido, será criado um registro:

```yaml
id: BUG-2026-0042
symbols:
  - orders.apply-coupon

problem:
  O mesmo cupom poderia ser aplicado mais de uma vez.

behavior_before:
  Cupons repetidos reduziam o total diversas vezes.

behavior_after:
  Um cupom pode ser aplicado somente uma vez por pedido.

regression_test:
  tests/orders/coupon-duplication.test.ts
```

A descrição atual da função será atualizada apenas quando o seu comportamento atual tiver mudado.

O histórico completo permanecerá em:

```text
.framework/history/
```

Assim, será possível consultar:

```bash
framework inspect orders.apply-coupon
```

Resultado:

```text
Função: orders.apply-coupon

Comportamento atual:
Aplica um cupom válido uma única vez ao pedido.

Tipos:
  entrada: Order, Coupon
  saída: Order

Testes:
  tests/orders/apply-coupon.test.ts
  tests/orders/coupon-duplication.test.ts

Bugs relacionados:
  BUG-2026-0042
```

Isso registra o que foi alterado sem poluir o código com históricos extensos.

---

# 14. Revisão de alterações

Um comando adicional importante será:

```bash
framework review
```

Esse comando deverá ser somente de leitura.

Seu objetivo será integrar a inspeção tradicional de código via **diffs do Git (`git diff`)** com a análise comportamental gerada por agentes de IA.

Ele deverá apresentar:

* **Diffs estruturais e de código (`git diff`)**: linhas inseridas, alteradas ou removidas;
* funções criadas;
* funções alteradas;
* assinaturas modificadas;
* comportamentos modificados;
* testes adicionados;
* testes removidos;
* testes que deixaram de passar;
* efeitos externos;
* alterações em banco de dados;
* novas dependências;
* riscos;
* trechos não cobertos;
* divergências entre teste e implementação.

Exemplo:

```text
Revisão da alteração

Diff do Git (resumo):
  apps/backend/src/orders.py | 14 +++++++++++---
  tests/orders/test_coupon.py | 22 ++++++++++++++++++++++
  2 files changed, 33 insertions(+), 3 deletions(-)

Comportamentos adicionados:
- um cupom não pode reduzir o total abaixo de zero;
- um cupom não pode ser aplicado duas vezes.

Funções alteradas:
- applyCoupon()
- calculateOrderTotal()

Banco de dados:
- nenhuma alteração.

Riscos:
- cupons antigos sem identificador podem exigir tratamento especial.

Testes:
- 2 adicionados;
- 94 aprovados;
- 0 removidos.

Pontos para revisão humana:
- comportamento de cupons legados;
- arredondamento de valores monetários.
```

O comando aceitará flags para visualização direta do diff do Git:

```bash
framework review --diff
```

Esse será um dos comandos mais importantes para o desenvolvedor que deseja validar visualmente as alterações no Git antes de aprovar ou realizar commits.

---

# 14.1. Integração com Git e GitHub (Local e Remoto)

O framework utilizará o **Git** como a fonte primária de verdade para alterações no código, suporte a histórico de bugs e revisão de diffs.

## Git Local

Para repositórios locais, o CLI irá:

* **Analisar o estado do repositório (`git status`)**: detectar arquivos modificados, não rastreados ou em staging;
* **Extrair Diffs (`git diff`)**: obter diffs exatos de arquivos modificados antes e depois da execução de comandos como `framework fix` ou `framework implement`;
* **Inspeção de autoria (`git blame` / `git log`)**: identificar em qual commit ou autor determinada função sofreu alteração recente, auxiliando a localizar a origem de bugs;
* **Proteção contra perdas**: criar checkpoints locais ou branches de trabalho temporárias durante refatorações automatizadas.

## Git Remoto & GitHub

O CLI integrará com o **GitHub** (via repositório remoto Git, GitHub CLI `gh` e GitHub API):

* **Rastreabilidade de Bugs e Issues**:
  * Vincular relatórios de bugs e correções executadas via `framework fix` diretamente a **GitHub Issues** ou Pull Requests;
  * Exemplo: `framework fix --issue 104` extrai o contexto da Issue do GitHub para orientar a reprodução e correção do bug.
* **Pull Requests e Revisões no GitHub**:
  * O comando `framework review --pr` poderá postar o resumo comportamental e a análise de riscos diretamente como comentário em um Pull Request no GitHub;
  * Integração do diff nativo do GitHub com o relatório do framework.
* **CI/CD via GitHub Actions**:
  * Execução dos quality gates (`framework check`) dentro de pipelines do GitHub Actions para bloquear PRs que violem testes aprovados ou contratos.

---

# 15. Verificação do projeto

## Comando

```bash
framework check
```

Esse comando executará os quality gates aplicáveis ao perfil atual.

Poderá verificar:

* testes aprovados modificados;
* funções públicas sem descrição;
* tipos não resolvidos;
* blocos explicativos desatualizados;
* testes ausentes;
* regressões;
* dependências adicionadas;
* scripts quebrados;
* falhas de segurança;
* regras ausentes ou inefetivas de `.gitignore` para arquivos de ambiente;
* arquivos sensíveis rastreados pelo Git;
* segredos hardcoded no workspace, staged diff, diff remoto ou histórico;
* alterações de contrato;
* inconsistências no índice.

Exemplo:

```text
Framework Check

✓ Configuração válida
✓ Todos os testes aprovados permanecem intactos
✓ Explicações sincronizadas
✓ Tipos das funções resolvidos
✓ Testes relacionados aprovados
⚠ Duas funções novas não possuem teste direto
✗ Um teste aprovado foi modificado

Status: bloqueado
```

---

# 16. Diagnóstico do ambiente

## Comando

```bash
framework doctor
```

Esse comando verificará:

* runtimes instalados;
* versões;
* package managers;
* banco de dados de teste;
* containers;
* permissões dos scripts;
* adaptadores;
* comandos de teste;
* integração com agente;
* arquivos gerados.

Ele será especialmente útil depois da inicialização ou em máquinas novas.

---

# 17. Atualização da análise da codebase

## Comando

```bash
framework scan
```

O comando deverá reanalisar o projeto quando:

* uma linguagem for adicionada;
* um framework mudar;
* um banco for substituído;
* novos serviços forem criados;
* o monorepo ganhar uma aplicação;
* o framework de testes mudar.

O comando apresentará um diff antes de alterar a configuração:

```text
Mudanças detectadas

+ Aplicação worker em Python
+ Redis detectado
+ Testes de integração em tests/worker
- Jest não é mais utilizado
+ Vitest detectado

Aplicar alterações? [S/n]
```

---

# 18. Classificação dos comandos

| Comando                  | Natureza         |          Modifica código |
| ------------------------ | ---------------- | -----------------------: |
| `framework init`         | Híbrido          |     Somente configuração |
| `framework scan`         | Script           |     Somente configuração |
| `framework doctor`       | Script           |                      Não |
| `framework security scan`| Script           |                      Não |
| `framework test create`  | Agente           |              Cria testes |
| `framework test explain` | Script           |      Apenas bloco gerado |
| `framework test`         | Script           |                      Não |
| `framework test approve` | Script           |       Registra aprovação |
| `framework tradeoff`     | Agente           |                      Não |
| `framework implement`    | Agente + scripts |                      Sim |
| `framework fix`          | Agente + scripts |                      Sim |
| `framework review`       | Script + agente  |                      Não |
| `framework sync`         | Script           | Apenas metadados gerados |
| `framework check`        | Script           |                      Não |
| `framework inspect`      | Script           |                      Não |
| `framework learn`        | Script           | Apenas memória opcional  |
| `framework quiz`          | Script           | Apenas avaliação opcional|

Essa classificação deverá ser visível na ajuda do CLI.

Exemplo:

```bash
framework implement --help
```

```text
Natureza: agentic
Permissão: modifica código
Pré-condições:
  - teste existente;
  - estado vermelho confirmado;
  - aprovação quando exigida.
```

---

# 19. Fluxo de uma nova feature

```bash
framework test create \
  "O usuário não pode cancelar um pedido já enviado"

framework test explain tests/orders/cancel-order.test.ts

framework test tests/orders/cancel-order.test.ts

framework test approve tests/orders/cancel-order.test.ts

framework tradeoff \
  "Bloquear o cancelamento na camada de domínio ou no serviço"

framework implement tests/orders/cancel-order.test.ts

framework review

framework check
```

---

# 20. Fluxo de correção de bug

```bash
framework fix \
  "Pedidos com cupom de 100% estão sendo salvos com total negativo"
```

Também será possível referenciar uma issue do GitHub:

```bash
framework fix --issue 104
```

```bash
framework review --diff

framework check
```

Internamente, `framework fix` realizará:

```text
bug descrito (ou GitHub Issue)
    ↓
análise de histórico e diffs via Git (git blame / git log)
    ↓
funções relacionadas identificadas
    ↓
teste de reprodução criado
    ↓
estado vermelho (falha confirmada)
    ↓
correção da implementação
    ↓
estado verde (teste aprovado)
    ↓
inspeção do git diff das alterações
    ↓
registro comportamental em .framework/history/
    ↓
vínculo/fechamento opcional no GitHub (Issue / PR)
```

---

# 21. Fluxo em codebase existente

```bash
framework init --here

framework doctor

framework scan

framework test explain --all

framework test

framework review
```

O framework deverá permitir adoção progressiva.

Não será obrigatório explicar e testar toda uma codebase legada imediatamente.

O índice poderá marcar funções como:

```text
documentada
inferida
não documentada
testada
parcialmente testada
não testada
legada
```

As regras mais rígidas poderão ser aplicadas apenas a código novo ou modificado.

---

# 22. Princípios do CLI

## CLI como interface única

O usuário não deverá precisar lembrar comandos diferentes de Pytest, Vitest, PHPUnit, Maven ou outros runners para executar o fluxo completo.

## Scripts antes de agentes

Operações previsíveis deverão utilizar scripts.

## Agentes com escopo limitado

Cada comando agentic terá permissões e responsabilidades claramente definidas.

## Nenhuma alteração silenciosa

O CLI deverá mostrar quais arquivos serão ou foram modificados.

## Tipos nunca devem ser inventados

Tipos desconhecidos deverão ser marcados como não resolvidos.

## Segredos nunca devem ser versionados

O scanner de segurança deve ser executado antes de commit, push e CI. Arquivos
`.env` e credenciais devem permanecer fora do Git; exemplos só podem conter valores
fictícios. Achados devem ser redigidos, rastreáveis por fingerprint e tratados com
revogação/rotação quando já tiverem alcançado o histórico.

## Aprendizado é opcional e revisável

`framework learn` pode registrar sessões, decisões, dificuldades, acertos e
retrabalho para evitar a repetição dos mesmos erros. O retrabalho é sinal de
aprendizado, não critério de paralelização. O recurso e o quiz de conhecimento não
são pré-condições para desenvolver, testar, commitar, fazer push ou executar CI.
Lições inferidas e perguntas alteradas devem ser revisadas antes de virar regra de
projeto ou instrução de agente.

## Testes aprovados são protegidos

Agentes não poderão alterar testes aprovados sem autorização.

## Adoção progressiva

Projetos legados não precisarão atingir conformidade total antes de utilizar o framework.

## Compatibilidade com projetos poliglotas

Cada aplicação de um monorepo poderá possuir seus próprios adaptadores e comandos.

## Configuração gerada

O usuário deverá editar apenas exceções, não configurar manualmente toda a stack.

## Rastreabilidade sem burocracia

Bugs e mudanças de comportamento serão vinculados às funções por identificadores estáveis, sem transformar comentários em changelogs.
