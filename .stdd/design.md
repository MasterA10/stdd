# Design do STDD

## Identidade visual

O STDD usa uma identidade editorial e técnica: superfícies claras, cartões com bordas suaves e ações críticas em gradiente vermelho-laranja. A linguagem deve ser direta, humana e orientada a evidências.

## Tipografia e espaçamento

Usar uma sans-serif de sistema, títulos com hierarquia forte e texto de apoio compacto. Manter uma escala de espaçamento baseada em múltiplos de 4px, áreas de leitura com rolagem interna e quebra de palavras longas.

## Estados e interação

Todo painel deve representar loading, vazio, erro, sucesso, foco e bloqueio. Modais são responsivos, possuem foco visível, textarea auto dimensionável e rolagem interna. Erros são consequências condicionais e nunca uma etapa inevitável.

## Acessibilidade e contraste

Texto normal mantém contraste mínimo de 4.5:1; texto grande, 3:1; componentes e foco visível, 3:1. Tags de menção usam gradiente vermelho-laranja, mas o significado não depende somente da cor.

## Integrações externas

O viewer comunica apenas com o Draw Server local. Qualquer API, app ou SDK adicional deve ser registrado no `AGENTS.md` e implementado conforme a documentação oficial do contrato.
