# STDD

STDD é um framework de controle de desenvolvimento orientado por testes. Ele instala skills para agentes de código, detecta a stack do repositório, configura os runners disponíveis e registra evidências em `.stdd/`.

## Instalação

O método recomendado é instalar o CLI diretamente de uma tag do repositório usando [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install stdd --from git+https://github.com/MasterA10/stdd.git@vX.Y.Z
```

Substitua `vX.Y.Z` pela tag desejada, mantendo o `v`. Em desenvolvimento local, dentro deste repositório:

```bash
uv tool install --editable .
```

Confirme a instalação:

```bash
stdd --help
```

## Inicializar um repositório

Entre no diretório onde o projeto deve ser criado e execute:

```bash
stdd init meu-projeto
cd meu-projeto
```

Em um terminal interativo, o STDD oferece uma seleção múltipla numerada:

```text
Selecione as integrações do agente (ex.: 1,3 ou 4 para todos):
  1. Codex
  2. Claude
  3. Gemini
  4. Todos
```

Depois da escolha, o CLI pergunta se deve executar o setup da stack. O setup não instala dependências nem inicia serviços sem autorização; ele apenas detecta arquivos e comandos locais.

Para automação sem perguntas:

```bash
stdd init meu-projeto --integration codex
stdd init meu-projeto --integration claude --integration gemini
stdd init meu-projeto --all-integrations
```

As skills são instaladas em:

- Codex: `.agents/skills/`
- Claude: `.claude/skills/`
- Gemini: `.gemini/skills/`

O framework permanece em uma única pasta `.stdd/`, e o setup escreve o `.gitignore` na raiz do projeto.

## Usar as skills no Codex

Depois de inicializar o projeto, abra o Codex dentro do repositório. As skills ficam em `.agents/skills/<skill>/SKILL.md` e podem ser chamadas diretamente pelo nome, no formato de skills do Codex:

```text
$setup Detecte a stack deste repositório e configure os runners sem instalar dependências.
$feature Quero implementar autenticação por sessão; transforme o pedido em uma feature testável.
$draw-feature Desenhe o fluxo de autenticação, incluindo falhas e subfluxos.
$static-analysis Analise dependências, complexidade, funções longas e segredos hardcoded.
$implement Execute a implementação aprovada e rode os gates do STDD.
```

Também é possível chamar a skill sem instrução adicional quando o objetivo já estiver claro:

```text
$setup
$feature
$implement
```

O agente deve ler o `SKILL.md` correspondente antes de agir. A skill define o contrato, os diretórios permitidos, os testes e os gates; a mensagem enviada no terminal fornece o contexto da tarefa. O processo recomendado é:

```text
$setup
$feature Descreva aqui o que o produto precisa fazer.
$draw-feature Mostre a arquitetura e os trade-offs dessa feature.
$implement Execute somente depois da aprovação.
```

Para Claude e Gemini, as mesmas skills são instaladas em `.claude/skills/` e `.gemini/skills/`; a forma exata de chamada pode ser o comando de skill adotado pelo agente, mas os nomes e contratos permanecem iguais.

## Configurar a stack

Se o setup não foi executado durante o init:

```bash
stdd setup
```

O comando identifica manifests e runners sem presumir Python. Exemplos de runners que podem ser gerados:

- Python: `python -m pytest`
- JavaScript/TypeScript: `npm test`, `pnpm test` ou `yarn test`
- Go: `go test ./...`
- Rust: `cargo test`
- Java: `mvn test` ou `./mvnw test`
- .NET: `dotnet test`

A configuração fica em `.stdd/config.json`. O setup também adiciona padrões de ambiente, dependências, builds e caches ao `.gitignore`, preservando regras existentes.

## Executar testes

```bash
stdd test
```

Esse é o alias global. Ele executa as suítes configuradas, análise estática, contrato e runners da stack. Suítes que exigem aprovação explícita aparecem como `not_executed` quando não autorizadas.

Opções úteis:

```bash
stdd test --suite unit
stdd test --exclude performance
stdd test --profile mvp
stdd test --approve-actions
```

## Segurança e análise estática

O scanner interno procura credenciais hardcoded, tokens conhecidos e valores copiados de `.env` para o código. O valor nunca é gravado no relatório; ele aparece como `[REDACTED]`. Um vazamento detectado bloqueia o gate de testes.

Arquivos `.env`, `.pyc`, caches, ambientes virtuais e artefatos de build são ignorados pelo Git automaticamente. Variáveis de ambiente sem referência no código geram aviso, não bloqueio automático, porque podem ser utilizadas por infraestrutura ou serviços externos.

## Registrar trabalho

```bash
stdd log "Implementa autenticação" --impl
stdd log "Adiciona testes de autenticação" --test
stdd log "Corrige regressão" --bug
stdd log "Reestrutura código sem planejamento prévio" --refactor
```

Mantenha registros de implementação e testes separados quando forem trabalhos diferentes.

## Artefatos principais

```text
.stdd/
├── config.json
├── draw.html
├── draws/
├── runs.html
└── runs/
```

As skills dos agentes ficam fora de `.stdd`, em seus diretórios próprios, e os demais artefatos do framework permanecem dentro de `.stdd`.
