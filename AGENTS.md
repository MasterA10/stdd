<!-- STDD:BEGIN AGENT INSTRUCTIONS -->
## STDD — Harness Control Layer

Este projeto usa o STDD para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `stdd log "descrição curta" --type implementacao|teste|bug|refactor`.
- Execute `stdd test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.stdd/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- A análise de código deve permanecer separada da análise dos Draws/JSONs; preserve símbolos, referências e métricas gerais quando a stack oferecer essa capacidade.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `stdd init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao integrar APIs/apps externos, registre o contrato no `AGENTS.md` e consulte a documentação oficial antes de implementar.
- O `.stdd/design.md` é a fonte obrigatória de decisões visuais: consulte e respeite identidade, tipografia, espaçamento, estados, acessibilidade e contraste em qualquer alteração ou implementação de interface; seu preenchimento é obrigatório antes de liberar o bootstrap.
- `$create-tests-backlog` e `$implement-backlog` pertencem exclusivamente aos loops acionados por `stdd backlog test` e `stdd backlog task`; não leia essas skills para edições, perguntas ou medições comuns fora do backlog.
- Quando o pedido vier de uma interação comum, trate-o como interação comum e siga somente as instruções necessárias ao pedido; não transforme a edição em task de backlog nem exija o ciclo de testes/implementação do backlog sem que o cursor tenha entregue uma task.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
<!-- STDD:END AGENT INSTRUCTIONS -->

## Regras de edição dos Draws

- Alterações de fluxos, desenhos, explicações e referências devem ser feitas no nó que mais se relaciona com o pedido. Por exemplo, ao explicar um sistema de recomendação de notificações, usar primeiro o nó de notificações; só usar outro nó se ele representar de forma mais direta as recomendações. Não criar ou alterar um nó genérico quando já existir uma cápsula específica para o assunto.
- Todo fluxo e subfluxo deve possuir um grupo específico para funcionalidades não implementadas quando houver uma funcionalidade planejada que ainda não existe. Os nós não implementados devem pertencer a esse grupo, permanecer terminais e receber a diferenciação visual do grupo; não usar cor individual no nó nem inventar continuação.

O comando do readme deve ser sempre atualizado de forma que qualquer push na main deve repletir nele. Se for necessário, pode mudar o comando, pode mudar a tag, mas o comando do README tem que estar sempre instalado e apontando para as últimas alterações. Sempre verifique o comando para ver se ele está atualizado.

- Ao consumir APIs, apps, SDKs ou provedores externos, registre o nome do serviço, endpoint/contrato, autenticação e pré-condições neste arquivo; consulte a documentação oficial atual antes de implementar e não invente payloads.
- O `.stdd/design.md` é a fonte das decisões visuais: identidade, tipografia, espaçamento, estados, acessibilidade e contraste mínimo devem estar preenchidos antes de liberar o bootstrap.
