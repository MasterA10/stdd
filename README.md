# Framework CLI

Framework CLI é um fluxo de desenvolvimento orientado por especificações, testes,
quality gates, segurança e aprendizado de sessões.

O framework é CLI-first. Codex, Claude e Antigravity/Agy são agentes locais: o
framework executa seus binários pela linha de comando. Não há chamadas de API de
modelos.

## Instalação local

No repositório:

```bash
uv sync
uv run framework --help
```

Para instalar as instruções de um agente no projeto:

```bash
framework integration install codex .
framework integration install claude .
framework integration install agy .
```

Use apenas uma integração padrão por projeto quando ela usar o mesmo diretório de
skills. Codex e Agy compartilham `.agents/skills` e são protegidos contra instalação
simultânea.

## Fluxo recomendado

```bash
framework init --integration codex
framework check
framework security scan
framework test create "O checkout deve validar cupons, rejeitar descontos inválidos, persistir o resultado e impedir que o total fique negativo"
framework test explain
framework test approve
framework implement
framework check
```

Para uma correção:

```bash
framework fix "O mesmo cupom pode ser aplicado duas vezes quando duas requisições concorrentes chegam ao checkout"
framework review
framework check
```

## Comandos canônicos

Existe uma única entrada pública para cada área. `learn` é o comando de memória,
`quiz` é o comando de avaliação e `integration` é o comando de agentes.

### Projeto e diagnóstico

```bash
framework version
framework init [path]
framework scan [path]
framework check [path]
framework doctor
```

`init` cria `.framework/project.yml`, detecta a stack e instala a integração local
selecionada. Para um projeto existente:

```bash
framework init --here --integration claude
framework init --from requirements.md --integration agy
```

`scan` detecta mudanças na codebase. `check` executa qualidade, segurança e testes
configurados. `doctor` diagnostica o ambiente.

`scan` também reconstrói o catálogo central em `.framework/index.db`, incluindo
funções, métodos, classes, documentação disponível, métricas e relações entre
testes e símbolos. `framework inspect <símbolo>` consulta esse catálogo.

### Testes e contratos

Executar testes:

```bash
framework test
framework test --unit
framework test --integration
framework test --database
framework test --security
framework test --performance
framework test --changed
framework test --all
```

Operações sobre testes:

```bash
framework test run [path]
framework test create "descrição completa da feature e dos comportamentos esperados"
framework test explain [arquivo]
framework test approve [arquivo]
```

`test create` funciona como um comando de especificação: a descrição completa é
entregue ao agente local especializado em testes. Ele analisa a stack, as regras
e os testes existentes, cria um plano de cenários e pode criar vários testes de
uma vez — unitários, integração, banco, segurança e performance quando fizer
sentido. O agente cria somente os testes e os deixa vermelhos; não implementa a
produção. O framework registra os arquivos gerados em
`.framework/quality/features/001-<feature>/feature.json`.

Por padrão, a integração local instalada é usada. `--agent-command` só deve ser
usado quando for necessário escolher explicitamente um executável local.

Sem arquivo, `test explain` explica todos os testes encontrados. Sem arquivo,
`test approve` aprova todos os testes encontrados e salva um hash individual para
cada um. Se um teste aprovado for alterado, `framework check` bloqueia a alteração
conforme o perfil do projeto.

### Segurança

```bash
framework security scan
```

Verifica `.env`, `.gitignore`, chaves hardcoded, segredos em arquivos e alterações
staged. O scan não imprime valores secretos.

### Integrações locais

```bash
framework integration list
framework integration status
framework integration install codex
framework integration install claude
framework integration install agy
```

As projeções são gravadas nos diretórios esperados por cada agente:

```text
Codex:       .agents/skills/
Claude:      .claude/skills/
Antigravity: .agents/skills/
```

O estado e os hashes ficam em:

```text
.framework/agents/manifest.json
.framework/agents/integration.json
```

O índice SQLite é a fonte de relacionamento; YAML fica reservado para configuração
e exportações legíveis. `framework sync` atualiza explicações, símbolos e relações
após alterações no código.

### Decisão e implementação agentic

```bash
framework tradeoff "Comparar eventos assíncronos e chamada síncrona para processar pagamentos, considerando consistência, latência, retries, observabilidade e custo"
framework implement [teste]
framework fix "descrição do bug"
framework review
framework inspect <símbolo>
framework sync
framework update
```

Esses comandos carregam a cadeia aplicável de `AGENTS.md`, `CLAUDE.md`, `CLOUD.md`
ou `GEMINI.md` e recebem uma descrição completa quando a operação depende de
inferência. Cada operação usa um papel especializado (`test-create`, `implement`,
`fix`, `tradeoff` ou `generate-scripts`). Conflitos entre instruções bloqueiam o
fluxo. `tradeoff` é somente leitura; `implement` e `fix` podem modificar o projeto
através do agente local.

`fix` cria um teste de regressão, coleta contexto de `git log` e `git blame`,
registra o comportamento em `.framework/history` e executa os gates.

### Memória de sessões

```bash
framework learn
framework learn start
framework learn checkpoint
framework learn compact
framework learn resume
framework learn close
framework learn summary
framework learn rework
framework learn review <lesson_id> <approved|rejected|edited>
```

O recurso é opcional e redigido. A retenção é controlada por
`learn.retention_days`.

Handoff entre sessões e agentes:

```bash
framework learn handoff export
framework learn handoff import <pacote>
framework learn handoff send <pacote> --target codex
framework learn handoff send <pacote> --target claude
```

Hooks de ciclo de sessão:

```bash
framework learn hooks install
framework learn hooks event --event <start|checkpoint|compact|resume|close>
```

### Quiz da codebase

```bash
framework quiz generate
framework quiz run
framework quiz refresh
framework quiz export --format json
```

O quiz relaciona perguntas a símbolos, regras, testes e decisões. A geração pode
usar um agente local explicitamente autorizado, mas o agente principal recebe
somente o reconhecimento de que o job foi criado/concluído.

### Scripts gerados

```bash
framework scripts generate
```

O agente local analisa a stack e gera scripts adequados em `.framework/scripts`.

## Formato de saída

Os comandos aceitam saída humana ou JSON:

```bash
framework check --format text
framework check --format json
```

Opções globais adicionais:

```text
--non-interactive   não solicita entrada
--no-color          desativa cores
--verbose           inclui detalhes adicionais
```

## Estrutura gerada

```text
.framework/
├── agents/       requests, resultados, manifesto e integrações
├── history/      bugs e mudanças comportamentais
├── learn/        memória opcional de sessões
├── quality/      baseline e aprovações de testes
│   └── features/ planos e conjuntos de testes por feature
│       └── 001-feature-name/
│           ├── test-plan.md
│           ├── checklist.md
│           └── feature.json
├── scripts/      scripts gerados pela IA local
├── security/     política e fingerprints redigidos
├── project.yml   configuração do projeto
└── index.db      índice de símbolos e relações
```

## Validação do próprio framework

```bash
uv run pytest -q
uv run framework check --format json
uv run framework security scan --format json
```
