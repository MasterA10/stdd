---
name: system-design
description: "Cria e mantém o Design System do projeto em `.looper/design.html` como uma landing page demonstrativa usando toda a estrutura e convenções do Open Design, extraindo exemplos e tokens da biblioteca local do Open Design no computador. Use ao iniciar, revisar ou alterar a linguagem visual de uma interface."
---

# System Design — Criação de Design System com Open Design

Use esta skill para criar e manter o Design System do projeto em `.looper/design.html`, utilizando **toda a estrutura e convenções do Open Design** e extraindo referências, paletas, componentes e padrões visuais da biblioteca local do Open Design instalada no computador.

## Biblioteca Local do Open Design

A skill utiliza a biblioteca e base de dados do Open Design instalada no computador:

- **Localização dos dados**: `~/Library/Application Support/Open Design/namespaces/release-stable/data/`
  - `design-systems/`: Contém definições e metadados de design systems estruturados (ex.: `DESIGN.md`, `metadata.json`).
  - `projects/`: Contém projetos completos de design systems com arquitetura consolidada:
    - `DESIGN.md`: Especificação técnica e regras de design.
    - `colors_and_type.css`: Tokens CSS de cores, tipografia, raios, sombras e estados.
    - `preview/`: Prévias visuais interativas por categoria (tokens, tipografia, componentes, superfícies).
    - `ui_kits/app/`: Kits de interface aplicados com layouts, busca, filtros, navegação e modais.
    - `assets/` e `fonts/`: Arquivos de fontes e ícones/assets de referência.
  - `design-templates/` e `library/`: Modelos e templates adicionais de componentes e composições visuais.

### Extração de Exemplos e Referências
- Inspecione a biblioteca do Open Design para extrair paletas cromáticas harmoniosas, escalas tipográficas legíveis e estruturas de componentes funcionais.
- Utilize as referências extraídas como ponto de partida ou inspiração para acelerar a criação de um sistema coeso e profissional para o projeto atual, adaptando-o às necessidades do produto.

## Estrutura do Open Design para o Design System

O Design System deve cobrir obrigatoriamente as **9 seções fundamentais do Open Design**:

1. **Visual Theme & Atmosphere (Tema Visual e Atmosfera)**:
   - Define a identidade visual, o clima emocional, o tom e a sensação geral da interface (ex.: moderno, minimalista, operacional B2B, alta densidade de dados ou editorial refinado).
   - Apresenta a declaração de propósito e contexto do produto.

2. **Color (Paleta e Papéis Semânticos)**:
   - Tokens semânticos essenciais aplicados via variáveis CSS:
     - Fundo e superfícies: `--bg`, `--surface`, `--surface-raised`, `--surface-overlay`.
     - Bordas e divisores: `--border`, `--border-subtle`, `--border-focus`.
     - Tipografia: `--text-primary`, `--text-secondary`, `--text-muted`, `--text-inverse`.
     - Destaque e ação: `--accent`, `--accent-hover`, `--accent-subtle`.
     - Feedbacks operacionais: `--success`, `--warning`, `--danger`, `--info`.
   - Garantia de contraste mínimo: 4.5:1 para texto normal e 3:1 para texto grande e controles interativos (WCAG AA).

3. **Typography (Tipografia e Hierarquia)**:
   - Papéis definidos: Display, Headings (H1 a H4), Body, Small/Caption e Code/Monospace.
   - Escala modular harmônica com tamanhos em `rem`, line-heights confortáveis (1.2 a 1.6) e pesos estruturados.
   - Fontes de alta legibilidade com fallbacks do sistema operacional robustos.

4. **Spacing & Rhythm (Espaçamento, Ritmo e Geometria)**:
   - Ritmo baseado em escala de múltiplos de 4px: `4px` (`0.25rem`), `8px` (`0.5rem`), `12px` (`0.75rem`), `16px` (`1rem`), `24px` (`1.5rem`), `32px` (`2rem`), `48px` (`3rem`), `64px` (`4rem`).
   - Raios de borda padronizados: `--radius-sm` (4px), `--radius-md` (8px), `--radius-lg` (12px), `--radius-full` (9999px).
   - Sombras e elevação: `--shadow-sm`, `--shadow-md`, `--shadow-lg`.

5. **Layout & Composition (Layout, Grid e Composição)**:
   - Estruturas de página inspiradas no Open Design: sidebar de navegação consistente (ex.: 248px fixa ou responsiva), header operacional, área de conteúdo principal fluida.
   - Grid flexível e responsivo, limites de container (`max-width`) e breakpoints limpos (`sm`, `md`, `lg`, `xl`).

6. **Components & UI Kits (Componentes e Kits de Interface)**:
   - Componentes reais e funcionais na página demonstrativa:
     - **Botões**: Variantes primária, secundária, ghost e destrutiva com estados `default`, `hover`, `active`, `:focus-visible` e `disabled`. Alvos de clique mínimos de 44px.
     - **Campos de Formulário**: Inputs de texto, selects, textareas, checkboxes, radio buttons e switches, com labels claros, estados de foco evidente e mensagens de erro acessíveis.
     - **Cards e Superfícies**: Containers com padding consistente, bordas sutis e variações de conteúdo.
     - **Badges e Indicadores de Status**: Comunicação obrigatória com **texto + cor** (nunca apenas cor).
     - **Tabelas e Listas**: Linhas com densidade equilibrada, cabeçalhos destacados e paginação/filtros.
     - **Modais e Diálogos**: Uso de `<dialog>` nativo ou containers acessíveis com foco retido e fechamento por `Escape`.

7. **Motion & Interaction (Movimento e Interação)**:
   - Transições rápidas e discretas (150ms a 250ms) usando curvas suaves (`ease-out`).
   - Estados de `:focus-visible` nítidos com outline/ring para navegação por teclado.
   - Suporte mandatório a `@media (prefers-reduced-motion: reduce)` desligando ou minimizando animações.

8. **Voice & Brand (Voz, Tom e Microcopy)**:
   - Diretrizes de tom de redação (claro, conciso, direto e sem jargões desnecessários).
   - Regras de capitalização (Sentence case para botões e labels, Title Case quando aplicável).

9. **Anti-patterns (Anti-padrões Proibidos)**:
   - Proibição absoluta do uso de emojis na interface (elementos decorativos e botões devem usar texto ou ícones SVG da biblioteca visual).
   - Proibição de múltiplos CTAs primários concorrentes no mesmo viewport.
   - Proibição de status comunicados unicamente por cor sem rótulo textual legível.
   - Proibição de alvos de toque inferiores a 44x44px.
   - Proibição de contraste insuficiente ou ausência de indicador de foco visível.

## Resultado Obrigatório: `.looper/design.html`

O artefato oficial de saída é `.looper/design.html`, estruturado como uma **landing page demonstrativa viva**:

- **Não é um documento estático ou tabela técnica descontextualizada**: O leitor deve compreender as regras visuais vendo os componentes renderizados e interagindo com eles.
- **Tokens aplicados**: As variáveis CSS são declaradas no `:root` e aplicadas diretamente em todos os componentes vivos da página.
- **Seções navegáveis**: A landing page deve conter navegação fluida entre todas as 9 seções do Open Design.

## Limites e Escopo

Esta skill define o contrato visual, tokens e demonstração em `.looper/design.html`. Ela não substitui os controladores, modelos, rotas de backend ou persistência do produto. Sempre que um novo padrão visual for estabelecido em uma interface, ele deve ser registrado em `.looper/design.html` para manter a documentação viva atualizada.
