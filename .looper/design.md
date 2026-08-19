# Design do Looper

## Identidade visual

O Looper usa uma identidade editorial e técnica: superfícies claras, cartões com bordas suaves e ações críticas em gradiente vermelho-laranja. A linguagem deve ser direta, humana e orientada a evidências.

### Degradê e paleta de marca

- O degradê oficial é `linear-gradient(135deg, #e31b23 0%, #ff8c00 100%)`: vermelho Looper no início, laranja Looper no fim e direção diagonal de 135 graus.
- O estado de hover usa a variação escura `linear-gradient(135deg, #b91c1c 0%, #ea580c 100%)`; ela é uma variação de interação, não uma nova identidade.
- A paleta estrutural usa `#ffffff`/`#1e293b` para superfícies, `#f8fafc`/`#0f172a` para canvas, `#0f172a`/`#f8fafc` para texto, `#64748b` para apoio, `#e2e8f0` para linhas, `#ef4444` para destaque e `#10b981` para sucesso.
- O degradê de marca deve ser usado em ações primárias, modais, badges, indicadores e estados de backlog. Não aplicar degradê individual por grupo de nó.

## Tipografia e espaçamento

- A fonte principal é `Fira Sans`, com fallback `'Inter', system-ui, -apple-system, sans-serif`; títulos usam peso forte e o texto de apoio permanece compacto.
- Usar uma escala de espaçamento baseada em múltiplos de 4px, áreas de leitura com rolagem interna e quebra de palavras longas.
- A composição usa cartões de aproximadamente 18px de raio, modais de 24px, controles compactos de 8–12px e hierarquia clara entre cabeçalho, conteúdo, divisores e rodapé.

## Composição de telas e componentes

- O viewer é composto por toolbar superior, barra lateral de navegação e canvas React Flow; a barra lateral inicia na aba Runs quando a página carrega.
- Modais usam superfície tematizada, borda sutil em laranja, faixa superior de 4px com o degradê oficial, rolagem interna e ações alinhadas no rodapé.
- Nós mantêm grupo e borda como informação estrutural: a cor do grupo permanece no contorno e no pill, enquanto o preenchimento dos estados de backlog usa a identidade Looper.
- O badge de teste associado é preto, tem cerca de 24px, contém um ícone de tubo branco de aproximadamente 18px e fica ao lado do identificador do nó.

## Estados e interação

Todo painel deve representar loading, vazio, erro, sucesso, foco e bloqueio. Modais são responsivos, possuem foco visível, textarea auto dimensionável e rolagem interna. Erros são consequências condicionais e nunca uma etapa inevitável.

- Nós em implementação usam o mesmo degradê oficial dos botões de salvar, texto branco e uma faixa laranja clara que percorre o nó continuamente; em `prefers-reduced-motion`, a faixa e o movimento são desativados.
- Nós concluídos usam o mesmo degradê oficial, texto branco e contorno de 2px na cor do grupo.
- A diferenciação de andamento não depende apenas de cor: o movimento, o texto de estado e os títulos acessíveis também comunicam a situação.

## Acessibilidade e contraste

Texto normal mantém contraste mínimo de 4.5:1; texto grande, 3:1; componentes e foco visível, 3:1. Ícones e textos sobre estados de backlog usam branco quando o fundo é o degradê vermelho-laranja. Tags de menção usam gradiente vermelho-laranja, mas o significado não depende somente da cor. Toda animação precisa de estado reduzido para `prefers-reduced-motion`.

## Integrações externas

O viewer comunica apenas com o Draw Server local. Qualquer API, app ou SDK adicional deve ser registrado no `AGENTS.md` e implementado conforme a documentação oficial do contrato.

## Decisões confirmadas de interface

- Estados de backlog em andamento e concluídos usam o degradê oficial vermelho-laranja; o andamento acrescenta faixa clara em movimento e a conclusão acrescenta contorno de 2px na cor do grupo.
- O degradê de marca, suas cores, direção e variação de hover estão definidos em “Degradê e paleta de marca” e devem ser reutilizados, sem duplicar valores divergentes nos componentes.
- Nós com teste criado e associado exibem o ícone de tubo branco ao lado do identificador, em badge preto de cerca de 24px e área visual de aproximadamente 18px.
- `Ctrl/Cmd+C` copia o JSON lógico do nó selecionado, preservando referências, símbolos, perguntas e campos adicionais; `Ctrl/Cmd+V` cria um novo nó com novo ID e não copia conexões.
- A barra de progresso de Runs usa exatamente a mesma nota ponderada exibida no resumo, inclusive quando não há alterações.
- Ao carregar o viewer, a barra lateral inicia na aba Runs; as demais abas continuam disponíveis para troca manual.

## Regra de evolução visual

Atualize esta seção somente quando uma interação aceita estabelecer um padrão reutilizável
de tela. Consolide decisões equivalentes, preserve contraste mínimo de 4.5:1 para texto
normal e registre também estados reduzidos quando houver animação; não transforme uma
preferência pontual ou uma tentativa não aprovada em regra visual.
