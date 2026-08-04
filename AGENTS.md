<!-- STDD:BEGIN AGENT INSTRUCTIONS -->
## STDD — Harness Control Layer

Este projeto usa o STDD para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `stdd log "descrição curta" --type implementacao|teste|bug|refactor`.
- Execute `stdd test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.stdd/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `stdd init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
<!-- STDD:END AGENT INSTRUCTIONS -->

O comando do readme deve ser sempre atualizado de forma que qualquer push na main deve repletir nele. Se for necessário, pode mudar o comando, pode mudar a tag, mas o comando do README tem que estar sempre instalado e apontando para as últimas alterações.