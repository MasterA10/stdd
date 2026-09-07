---
name: system-design
description: "Cria e mantém o Design System do projeto em `.looper/design.html` como uma landing page demonstrativa usando toda a estrutura e convenções do Open Design, extraindo exemplos e tokens da biblioteca local do Open Design no computador e dos artefatos em `.agents/skills/system-design/open-design/`. Use ao iniciar, revisar ou alterar a linguagem visual de uma interface e criar telas."
---

# System Design — Criação de Design System e Telas com Open Design

Use esta skill para criar e manter o Design System do projeto em `.looper/design.html` e para guiar a criação de todas as telas e interfaces, utilizando **toda a estrutura e convenções do Open Design** e extraindo referências, paletas, tokens, componentes e padrões visuais da biblioteca local do Open Design instalada no projeto.

## Artefatos e Biblioteca Local do Open Design

A biblioteca do Open Design está empacotada diretamente dentro da pasta da skill em `.agents/skills/system-design/open-design/` (e na raiz do repositório em `open-design/`):

### Estrutura dos Recursos Disponíveis

1. **`open-design/design-systems/`** (Mais de 150 design systems empacotados):
   - Cada pasta representa um design system completo e utilizável (ex.: `linear-app`, `stripe`, `vercel`, `apple`, `resend`, `shadcn`, `tailwind`, `openai`, `figma`, `raycast`, `notion`, `supabase`, etc.).
   - Arquivos essenciais em cada pacote:
     - `manifest.json`: Metadados, categoria, autor e arquivos declarados no pacote.
     - `USAGE.md`: Guia de leitura rápida e ordem de consumo para o agente.
     - `DESIGN.md`: Especificação da identidade, filosofia visual, decisões de contraste e anti-patterns.
     - `tokens.css`: Folha de estilo de tokens semânticos prontos com variáveis `:root` (`--bg`, `--surface`, `--accent`, `--border`, `--fg`, `--muted`, etc.).
     - `tailwind-v4.css`: Mapeamento de tokens compatível com Tailwind CSS v4.
     - `components.html`: Fixture com componentes funcionais e estilizados para consulta e reaproveitamento.
     - `components.manifest.json`: Inventário estruturado de componentes com seus seletores e tokens.
     - `design-tokens.json`: Tokens no formato padronizado W3C Design Tokens Community Group.
     - `preview/`: Prévias visuais interativas por categoria (tokens, tipografia, componentes, superfícies).

2. **`open-design/craft/`** (Regras rigorosas de engenharia e excelência de interface):
   - `anti-ai-slop.md`: Os 7 pecados capitais do design de IA (proibição de Tailwind índigo padrão, gradientes roxos/azuis de dois stops, emojis como ícones, cards com borda esquerda colorida, métricas inventadas e copy de preenchimento).
   - `color.md`: Arquitetura de paleta em 4 camadas (70-90% neutros, 5-10% accent único limitado a 2 usos por tela, 0-5% semânticos, <1% efeitos); contraste mínimo WCAG (4.5:1 / 3:1); boas práticas de dark mode (`#0f0f0f` ao invés de `#000`).
   - `typography.md` & `typography-hierarchy.md`: Escalas modulares, diferenciação entre display e corpo, line-heights e tracking intencional.
   - `accessibility-baseline.md`: Alvos de clique mínimos de 44px, `:focus-visible` evidente para navegação por teclado e semântica acessível.
   - `laws-of-ux.md`: Leis de Fitts, Hick, Miller e Jakob aplicadas na organização dos fluxos.
   - `state-coverage.md`: Cobertura obrigatória de estados (vazio, carregando, preenchido, erro e sucesso).
   - `animation-discipline.md`: Transições discretas (150ms-250ms), curvas ease-out e suporte estrito a `@media (prefers-reduced-motion: reduce)`.
   - `form-validation.md`: Validação em linha, foco em mensagens de erro e clareza de formulários.

3. **`open-design/design-templates/`** (Mais de 100 templates de telas reais e aplicações):
   - Modelos prontos de dashboards operacionais (`dashboard`, `github-dashboard`, `flowai-live-dashboard-template`), páginas de documentação (`docs-page`, `eng-runbook`), fluxos de entrada (`login-flow`), relatórios (`finance-report`), e landing pages (`open-design-landing`).

4. **`open-design/prompt-templates/`, `frames/` e `skills/`**:
   - Templates de prompts, frames para fluxogramas visuais e skills complementares de UI/UX.

---

## Como Navegar, Consumir os Recursos e Criar Telas

O agente deve seguir o seguinte fluxo de trabalho metódico:

### Passo 1: Navegação e Seleção do Estilo Visual
1. Identifique o tipo de aplicação (SaaS B2B, Dashboard de Dados, DevTool, E-commerce, Fintech, Consumer App, etc.).
2. Navegue em `.agents/skills/system-design/open-design/design-systems/` para encontrar o design system que melhor traduz a identidade desejada:
   - Para SaaS focado em produtividade e alta densidade: examine `linear-app` ou `raycast`.
   - Para Developer Tools e minimalismo moderno: examine `vercel` ou `supabase`.
   - Para Fintechs e operações com alta credibilidade: examine `stripe` ou `revolut`.
   - Para interfaces operacionais e dashboards flexíveis: examine `shadcn`, `tailwind` ou `posthog`.
   - Para produtos premium e refinados: examine `apple`, `resend` ou `editorial`.
3. Abra e leia primeiro o `USAGE.md` e o `DESIGN.md` do pacote escolhido para absorver os princípios, hierarquia e restrições.

### Passo 2: Extração de Tokens e Paleta
1. Abra `tokens.css` (e `tailwind-v4.css` ou `design-tokens.json` se aplicável).
2. Extraia os tokens fundamentais de cores, superfícies, bordas, sombras e raios.
3. Garanta que a paleta siga a regra das 4 camadas de `craft/color.md`:
   - **Neutros (70-90%)**: Superfícies de fundo, painéis e tipografia principal e secundária.
   - **Accent (5-10%)**: Apenas UMA cor de destaque (`--accent`), limitada a no máximo 2 utilizações visíveis no viewport (ex.: um botão primário e um active badge).
   - **Semânticos (0-5%)**: Feedback de status (`--success`, `--warning`, `--danger`).
   - **Efeitos (<1%)**: Gradientes ou glows sutis.

### Passo 3: Consulta ao Craft e Anti-AI-Slop
Antes de gerar o HTML ou CSS, revise as regras de `craft/anti-ai-slop.md`:
- **Sem emojis**: Proibição absoluta de emojis como ícones ou labels (`✨`, `🚀`, etc.). Use SVGs monoline ou texto.
- **Sem índigo padrão**: Não use as cores padrão do Tailwind (`#6366f1`, etc.). Use o `--accent` intencional do Design System.
- **Sem gradientes genéricos**: Evite gradientes roxo→azul genéricos. Superfícies sólidas limpas com contraste preciso são superiores.
- **Sem cards com borda esquerda colorida**: Estruture informações com badges semânticos e tipografia, não com bordas laterais clichês.
- **Copy realista**: Use dados e labels contextuais ao domínio do sistema, nunca "Lorem ipsum" ou métricas fictícias ("10x faster").

### Passo 4: Construção do `.looper/design.html`
Crie ou atualize `.looper/design.html` estruturado como uma **landing page demonstrativa** cobrindo obrigatoriamente as **9 seções fundamentais do Open Design**:

1. **Visual Theme & Atmosphere (Tema Visual e Atmosfera)**:
   - Identidade visual, clima emocional, tom e sensação da interface.
2. **Color (Paleta e Papéis Semânticos)**:
   - Variáveis CSS no `:root` (`--bg`, `--surface`, `--surface-raised`, `--border`, `--text-primary`, `--accent`, etc.) com garantia de contraste mínimo WCAG AA (4.5:1 texto, 3:1 controles).
3. **Typography (Tipografia e Hierarquia)**:
   - Display, H1-H4, Body, Small e Code com escalas em `rem` e line-heights confortáveis.
4. **Spacing & Rhythm (Espaçamento, Ritmo e Geometria)**:
   - Escala modular baseada em múltiplos de 4px (`4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `48px`), raios de borda e sombras de elevação.
5. **Layout & Composition (Layout, Grid e Composição)**:
   - Estrutura de sidebar, header operacional, containers com `max-width` e breakpoints responsivos.
6. **Components & UI Kits (Componentes e Kits de Interface)**:
   - Componentes reais e funcionais na página: botões (com estados `default`, `hover`, `active`, `:focus-visible`, `disabled` e touch target ≥44px), formulários (inputs com erro contextual), cards, badges (texto + cor), tabelas com densidade ajustada e modais com foco acessível.
7. **Motion & Interaction (Movimento e Interação)**:
   - Transições rápidas (150ms-250ms ease-out) e suporte obrigatório a `@media (prefers-reduced-motion: reduce)`.
8. **Voice & Brand (Voz, Tom e Microcopy)**:
   - Tom claro, direto e profissional; regras de Sentence case para botões e labels.
9. **Anti-patterns (Anti-padrões Proibidos)**:
   - Diretrizes explícitas do que nunca fazer na interface.

### Passo 5: Criação das Telas da Aplicação
Ao implementar as telas reais da aplicação (frontend/views L2 do backlog):
1. **Consistência Total**: Utilize estritamente os tokens CSS declarados no `.looper/design.html`.
2. **Reaproveitamento de Templates**: Inspecione `.agents/skills/system-design/open-design/design-templates/` para reaproveitar estruturas de layout, cabeçalhos, barras de ação e painéis comprovados.
3. **Contrato de Telas Dinâmicas**: Conecte informações dinâmicas exclusivamente via função `get_mock_fake` (ou similar) consumindo o JSON central do projeto.
4. **Cobertura de Estados**: Toda tela deve contemplar estado de carregamento, estado vazio (empty state explicativo e amigável), estado preenchido e feedback de erro.
