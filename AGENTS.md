<!-- STDD:BEGIN AGENT INSTRUCTIONS -->
## STDD — Harness Control Layer

Este projeto usa o STDD para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `stdd log "descrição curta" --type implementacao|teste|bug|refactor`.
- Execute `stdd test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.stdd/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- Preserve a análise geral de código e a análise dos Draws/JSONs como capacidades separadas; a política específica de frontend foi aposentada.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `stdd init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
<!-- STDD:END AGENT INSTRUCTIONS -->

## Regras de edição dos Draws

- Alterações de fluxos, desenhos, explicações e referências devem ser feitas no nó que mais se relaciona com o pedido. Por exemplo, ao explicar um sistema de recomendação de notificações, usar primeiro o nó de notificações; só usar outro nó se ele representar de forma mais direta as recomendações. Não criar ou alterar um nó genérico quando já existir uma cápsula específica para o assunto.
- Todo fluxo e subfluxo deve possuir um grupo específico para funcionalidades não implementadas quando houver uma funcionalidade planejada que ainda não existe. Os nós não implementados devem pertencer a esse grupo, permanecer terminais e receber a diferenciação visual do grupo; não usar cor individual no nó nem inventar continuação.

O comando do readme deve ser sempre atualizado de forma que qualquer push na main deve repletir nele. Se for necessário, pode mudar o comando, pode mudar a tag, mas o comando do README tem que estar sempre instalado e apontando para as últimas alterações. Sempre verifique o comando para ver se ele está atualizado.
