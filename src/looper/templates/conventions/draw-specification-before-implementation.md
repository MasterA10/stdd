---
name: builder e sincronização de convenções
description: Mantém skills, convenções e o catálogo do AGENTS.md sincronizados.
---

# Sincronização do Builder, skills e convenções

O Builder é a origem distribuível das skills do Looper. Toda alteração em uma skill
deve ser aplicada ao template empacotado em `src/looper/templates/agents/`, mantendo
a cópia instalada em `.agents/skills/` sincronizada para o repositório atual. O
`looper init` deve executar essa sincronização tanto em repositórios novos quanto em
repositórios já inicializados, sem apagar conteúdo próprio do projeto.

Quando uma convenção for criada ou alterada em `.agents/conventions/`, o `looper log`
deve executar a atualização do bloco gerenciado do `AGENTS.md`, reconstruindo o
catálogo a partir dos arquivos existentes. O catálogo lista assuntos; o conteúdo
completo permanece nos arquivos de convenção. Essa atualização deve ser idempotente,
preservar as instruções próprias do projeto e refletir também convenções adicionadas
sem uma nova execução de `init`.

Para documentação de Draws antes da implementação, níveis 1–3 podem descrever
funcionalidades planejadas sem símbolos de código. Nesse caso, registre incertezas em
`questions` e mantenha `code_refs` vazios ou pendentes; depois da implementação,
associe e releia os símbolos reais. Nunca invente arquivos, endpoints, permissões ou
símbolos placeholder.
