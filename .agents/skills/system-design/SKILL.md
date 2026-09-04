---
name: system-design
description: Define e mantém o design system do projeto em `.looper/design.html` como uma landing page demonstrativa, com tokens aplicados em componentes reais, explicações de uso e estados acessíveis. Use ao iniciar, revisar ou alterar a linguagem visual de uma interface.
---

# System Design

Use esta skill para transformar decisões visuais em um design system pequeno, explícito, versionável e fácil de validar visualmente. A fonte de verdade continua sendo `.looper/design.html`; não crie um arquivo paralelo de tokens sem solicitação explícita.

## Resultado obrigatório

`.looper/design.html` deve ser uma página de demonstração do próprio design system, com qualidade de landing page. Ela combina conteúdo informativo e exemplos renderizados: cada regra importante deve ser explicada em linguagem simples e mostrada na prática logo ao lado ou abaixo.

Não entregue um documento que seja apenas tabela de hexadecimais, lista de medidas, código ou markup solto. O leitor deve conseguir entender a regra olhando para a interface em funcionamento — por exemplo, a seção de botões explica o uso e exibe os próprios botões nos estados relevantes.

Mantenha os tokens semânticos implementados como variáveis CSS ou outro mecanismo equivalente e aplique-os de verdade aos exemplos. Eles podem continuar inspecionáveis no HTML/CSS, mas a apresentação principal deve mostrar cores, tipografia, espaçamento, bordas, raios e elevação aplicados, sem exigir que o leitor leia código.

## Processo

1. Leia `.looper/design.html` e a implementação de UI existente antes de propor mudanças. Preserve decisões aceitas e consolide duplicatas.
2. Inspecione referências visuais fornecidas, quando houver, extraindo princípios e não markup incidental. Se uma referência não puder ser aberta, continue com a descrição do usuário e marque escolhas não resolvidas como `[PREENCHER]`.
3. Defina tokens semânticos antes dos valores específicos de componentes. Prefira papéis como `color.surface.canvas`, `color.text.primary`, `color.action.primary`, `space.4`, `radius.md` e `shadow.sm`.
4. Construa ou atualize a página demonstrativa em seções coerentes. Use texto curto para explicar intenção, aplicação, restrições e estados; use componentes vivos para provar cada decisão.
5. Confira a página em tamanhos de tela relevantes e valide contraste, foco por teclado, leitura sem cor e comportamento com movimento reduzido. Consulte `$modern-web-guidance` para padrões atuais de HTML/CSS e interação.
6. Registre somente decisões duráveis e aprovadas. Não invente identidade, fontes, cores ou medidas e não apresente suposições como fatos confirmados.

## Estrutura mínima da demonstração

Adapte a ordem ao produto, mas cubra visualmente:

- uma abertura que explique o propósito, o tom e como usar o sistema;
- tipografia com hierarquia, pesos, tamanhos, line-height e exemplos de texto reais;
- paleta semântica mostrada em superfícies, textos, bordas, ações e feedbacks aplicados — não somente em swatches;
- espaçamento, grid, containers e breakpoints demonstrados por composição, escala ou layout responsivo;
- bordas, raios, sombras, densidade e superfícies exemplificados em cards, campos e outros elementos;
- componentes reutilizáveis, no mínimo botões e campos, com variantes e estados hover, ativo, foco e desabilitado quando aplicáveis;
- estados de loading, vazio, erro e sucesso quando fizerem sentido para o produto;
- regras de acessibilidade, contraste, foco e `prefers-reduced-motion` explicadas e demonstradas;
- uma nota final sobre consistência e sobre como consumir os tokens na aplicação.

Cada exemplo precisa usar os tokens definidos. Evite valores isolados que só existem para decorar a própria página. Use conteúdo representativo do domínio quando ele for conhecido; caso contrário, use conteúdo neutro e deixe a identidade pendente sem criar uma marca fictícia.

## Tokens e acessibilidade

Prefira uma escala pequena e nomes estáveis. Registre o valor bruto junto ao uso sem transformar isso no foco da página. Cubra, conforme aplicável, marca e cores, famílias e escala tipográfica, espaçamento e densidade, containers e breakpoints, raios, bordas, elevação, motion, foco e estados.

Especifique loading, vazio, erro, sucesso, hover, ativo, desabilitado e foco. Garanta contraste mínimo de 4.5:1 para texto normal e 3:1 para texto grande e componentes de UI. Defina uma alternativa para `prefers-reduced-motion`. Não use emojis na interface; nomes, labels e estados devem usar texto ou ícones da biblioteca visual do projeto.

## Limites

Esta skill define o contrato visual e a página demonstrativa do sistema; ela não implementa telas do produto, controllers, modelos, persistência ou integrações. Ao estabelecer um padrão reutilizável durante uma mudança de UI, atualize também a demonstração em `.looper/design.html`.
