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

## Decisões confirmadas de interface

- Estados de backlog em andamento usam um degradê laranja mais claro com movimento contínuo e brilho; tasks prontas usam degradê laranja-vermelho e contorno de 2px na cor do grupo.
- Nós com teste criado e associado exibem `TestTube2` ao lado do identificador, em badge laranja-vermelho brilhante, com cerca de 24px de área e 18px de ícone interno.
- `Ctrl/Cmd+C` copia o JSON lógico do nó selecionado, preservando referências, símbolos, perguntas e campos adicionais; `Ctrl/Cmd+V` cria um novo nó com novo ID e não copia conexões.
- A barra de progresso de Runs usa exatamente a mesma nota ponderada exibida no resumo, inclusive quando não há alterações.

## Regra de evolução visual

Atualize esta seção somente quando uma interação aceita estabelecer um padrão reutilizável
de tela. Consolide decisões equivalentes, preserve contraste mínimo de 4.5:1 para texto
normal e registre também estados reduzidos quando houver animação; não transforme uma
preferência pontual ou uma tentativa não aprovada em regra visual.
