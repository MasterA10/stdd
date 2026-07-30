# Implementation Plan: CLI Framework Foundation

**Branch**: `001-cli-framework-bootstrap` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-cli-framework-bootstrap/spec.md`

## Summary

Construir a fundação do framework como um CLI Python distribuído e gerenciado por
`uv`, capaz de inicializar projetos, detectar sua stack, instalar projeções para
Codex CLI e Claude Code, executar scripts determinísticos e consolidar testes,
análise estática, secret scanning e resultados em texto e JSON. O núcleo terá
adaptadores extensíveis e usará Git para recursos completos de diff, histórico,
rastreabilidade e bloqueio de credenciais.

Esta entrega não implementa `framework learn`, quiz, hooks de sessão ou suporte à
paralelização; ela preserva contratos de extensão para essas features futuras.

## Technical Context

**Language/Version**: Python 3.11+ gerenciado por `uv`  
**Primary Dependencies**: Python standard library, `PyYAML`, `pytest` para testes; ferramentas nativas da stack via subprocessos controlados  
**Storage**: `.framework/project.yml` para configuração; `.framework/index.db` para índice local; relatórios JSON e texto  
**Testing**: `pytest`, testes de subprocesso do CLI, fixtures de codebases e testes de contrato dos adaptadores  
**Target Platform**: macOS e Linux, em terminais interativos e CI  
**Project Type**: CLI/devtool distribuível  
**Performance Goals**: inicialização de uma codebase de referência em até 30 segundos, sem executar a suíte completa; `framework check` incremental em até 60 segundos para até 100 mil arquivos rastreados, excluindo comandos de teste externos  
**Constraints**: Git obrigatório para recursos completos; nenhum segredo em saída; operações previsíveis não usam agente; Windows fica fora desta entrega; aprendizado e quiz não são dependências  
**Scale/Scope**: codebases poliglotas de até 100 mil arquivos rastreados e aproximadamente 1 milhão de linhas, com análise incremental por arquivos alterados  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Applicable Markdown instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
      `CLOUD.md` e instruções locais) serão carregados e registrados antes de cada
      operação agentic.
- [x] O núcleo prioriza scripts determinísticos, subprocessos nativos e AST antes
      de agentes; agentes não serão usados para init, scan, check ou security scan.
- [x] Comandos que modificam código serão limitados a projeções/artefatos do
      framework, declararão permissões e manterão testes aprovados protegidos.
- [x] O plano define análise de duplicação, funções longas, classes Deus,
      complexidade e baseline por adaptador.
- [x] O plano define secret scanning de `.gitignore`, arquivos rastreados, staged
      diff, diff remoto e histórico, com bloqueio e redaction.
- [x] `learn` e quiz estão explicitamente desabilitados e fora da entrega; não são
      gates nem dependências desta feature.
- [x] `framework check` terá saída humana e JSON, com arquivo, linha, regra,
      métrica, severidade e ação recomendada.
- [x] Não há violações constitucionais a justificar; a adoção progressiva usa
      baseline explícito para legado.

## Phase 0: Research Decisions

As decisões abaixo resolvem os pontos técnicos necessários sem ampliar o escopo.
Os detalhes e alternativas estão em [research.md](./research.md).

1. Distribuição: pacote persistente `framework-cli` publicado por release e
   bootstrap temporário por uma referência GitHub versionada, seguindo o modelo
   escolhido na especificação.
2. CLI: `argparse` e `subprocess` da biblioteca padrão para reduzir dependências e
   manter comandos previsíveis; `PyYAML` apenas para a configuração editável.
3. Índice: SQLite local por `sqlite3`, com schema versionado e reindexação
   incremental; nenhuma base externa é necessária.
4. Adaptadores: contrato comum para detecção, scripts, símbolos, testes e análise;
   o núcleo não duplica regras específicas de cada stack.
5. Segurança: scanner próprio orientado por regras, entropia e adaptadores,
   chamando Git diretamente e redigindo valores; ferramentas externas são
   opcionais e não podem ser requisito do fluxo básico.
6. Agentes: fonte canônica em `.framework/agents`, com projeções verificadas por
   checksum para Codex CLI e Claude Code.
7. Bloqueio Git: em repositórios Git, a inicialização instala wrappers de
   `pre-commit` e `pre-push` após confirmação, sem sobrescrever hooks locais
   existentes; os wrappers executam `framework security scan` e `framework check`.

## Phase 1: Design

### Data Model

O modelo detalhado está em [data-model.md](./data-model.md). As entidades centrais
são `ProjectProfile`, `Application`, `Adapter`, `ScriptDefinition`,
`AgentProjection`, `InstructionFile`, `QualityRule`, `QualityFinding`,
`SecurityFinding`, `GitSnapshot` e `GeneratedArtifact`.

Regras principais:

- Cada projeto possui exatamente um perfil ativo e uma configuração versionada.
- Aplicações pertencem ao perfil e podem ter múltiplos adaptadores e comandos.
- Achados apontam para arquivo, linha, regra, severidade, fingerprint e evidência.
- Um arquivo gerado mantém origem canônica, destino, versão e checksum.
- Baselines identificam o commit e a regra que justificam um achado legado.
- Hooks de commit registram origem, estado e conflito sem apagar hooks locais.
- Segredos não são persistidos em claro; fingerprints não são reversíveis.

### Contracts

Os contratos de CLI, configuração, projeções e relatórios estão em `contracts/`:

- [cli.md](./contracts/cli.md)
- [project-config.md](./contracts/project-config.md)
- [agent-projection.md](./contracts/agent-projection.md)
- [quality-report.md](./contracts/quality-report.md)

### Project Structure

#### Documentation (this feature)

```text
specs/001-cli-framework-bootstrap/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── checklists/requirements.md
```

#### Source Code (repository root)

```text
pyproject.toml
src/framework_cli/
├── __main__.py
├── cli.py
├── commands/
│   ├── init.py
│   ├── scan.py
│   ├── doctor.py
│   ├── test.py
│   ├── check.py
│   ├── security.py
│   └── install.py
├── config/
├── adapters/
│   ├── base.py
│   ├── generic.py
│   ├── python.py
│   └── javascript.py
├── scripts/
├── git/
├── security/
├── agents/
├── reporting/
└── index/

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

**Structure Decision**: Um pacote Python único mantém o núcleo, os comandos e os
contratos internos co-localizados; adaptadores ficam isolados para permitir adição
de stacks sem alterar o orquestrador. A separação `src/` + `tests/` suporta a
distribuição por `uv` e execução local/CI.

### Quickstart

O fluxo operacional está em [quickstart.md](./quickstart.md), cobrindo instalação
persistent/temporária, `init`, seleção interativa de agente, `scan`, `test`,
`check`, `security scan` e instalação segura dos hooks Git.

## Phase 1: Agent Context Update

O bloco `SPECKIT START/END` de `AGENTS.md` será atualizado para apontar para este
plano específico, mantendo também a referência à arquitetura raiz quando
necessário. O agente deve registrar a cadeia completa antes de qualquer tarefa.

## Complexity Tracking

Não há violações constitucionais previstas. A implementação de adaptadores e o
scanner próprio são complexidade necessária para cumprir suporte poliglota e
proteção de segredos; alternativas mais simples baseadas apenas em regex ou em um
agente foram rejeitadas por baixa cobertura e falta de determinismo.
