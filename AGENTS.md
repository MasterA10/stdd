<!-- Looper:BEGIN AGENT INSTRUCTIONS -->
## Looper — Harness Control Layer

Este projeto usa o Looper para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `looper log "descrição curta" --type implementacao|teste|bug|refactor`.
- Execute `looper test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.looper/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- A análise de código deve permanecer separada da análise dos Draws/JSONs; preserve símbolos, referências e métricas gerais quando a stack oferecer essa capacidade.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `looper init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao integrar APIs/apps externos, registre o contrato no `AGENTS.md` e consulte a documentação oficial antes de implementar.
- O `.looper/design.md` é a fonte obrigatória de decisões visuais: consulte e respeite identidade, tipografia, espaçamento, estados, acessibilidade e contraste em qualquer alteração ou implementação de interface; seu preenchimento é obrigatório antes de liberar o bootstrap.
- Ao construir, refinar ou revisar interfaces, leia e use a skill `$open-design` instalada em `.agents/skills/open-design/SKILL.md`, consultando seus recursos sob demanda.
- Mantenha memória contextual seletiva: registre decisões duráveis e aceitas no `AGENTS.md` (contratos, arquitetura, operação e escopo) ou no `.looper/design.md` (visual e interação); consolide duplicatas e não registre hipóteses, detalhes temporários, IDs de execução ou segredos.
- `$create-tests-backlog` e `$implement-backlog` pertencem exclusivamente aos loops acionados por `looper backlog test` e `looper backlog task`; não leia essas skills para edições, perguntas ou medições comuns fora do backlog.
- Quando o pedido vier de uma interação comum, trate-o como interação comum e siga somente as instruções necessárias ao pedido; não transforme a edição em task de backlog nem exija o ciclo de testes/implementação do backlog sem que o cursor tenha entregue uma task.
- No loop do backlog, execute `looper backlog complete <task-id>` com o mesmo ID recebido somente após validar a task; sem isso, o cursor não avança.
- Quando o backlog entregar o nó e os subfluxos internos juntos, implemente e teste ambos; “Tela” classifica o nível do nó e não limita a entrega ao frontend.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
<!-- Looper:END AGENT INSTRUCTIONS -->

## Memória contextual seletiva

Este arquivo é contexto vivo do projeto, não um diário de execução. Registre somente
decisões duráveis confirmadas por uma solicitação aceita, por uma integração verificada
ou por um padrão que o loop passou a exigir repetidamente.

- Use o `AGENTS.md` para contratos, arquitetura, operação, rastreabilidade, limites de escopo e instalação.
- Use o `.looper/design.md` para decisões visuais e de interação, como tipografia, cores, espaçamento, estados, animações e atalhos.
- Antes de acrescentar contexto, procure uma regra equivalente, consolide duplicatas e remova detalhes temporários; não registre hipóteses, IDs de execução, segredos ou alterações pontuais.
- Uma interação comum só atualiza esses arquivos quando produzir uma decisão reutilizável. No backlog, faça essa verificação antes de `backlog complete` e relate a atualização junto com os testes.

## Contexto confirmado do projeto

- O viewer servido por `looper draw serve` usa os assets empacotados em `src/looper/draw_assets`; o build de `draw-editor` precisa ser sincronizado para essa pasta antes da validação fora deste repositório.
- Quando o backlog entregar um nó com seus subfluxos, a entrega cobre o nó L2 e todos os L3 listados; o nível “Tela” não limita a implementação ao frontend.

## Regras de edição dos Draws

- Alterações de fluxos, desenhos, explicações e referências devem ser feitas no nó que mais se relaciona com o pedido. Por exemplo, ao explicar um sistema de recomendação de notificações, usar primeiro o nó de notificações; só usar outro nó se ele representar de forma mais direta as recomendações. Não criar ou alterar um nó genérico quando já existir uma cápsula específica para o assunto.
- Todo fluxo e subfluxo deve possuir um grupo específico para funcionalidades não implementadas quando houver uma funcionalidade planejada que ainda não existe. Os nós não implementados devem pertencer a esse grupo, permanecer terminais e receber a diferenciação visual do grupo; não usar cor individual no nó nem inventar continuação.

O comando do readme deve ser sempre atualizado de forma que qualquer push na main deve repletir nele. Se for necessário, pode mudar o comando, pode mudar a tag, mas o comando do README tem que estar sempre instalado e apontando para as últimas alterações. Sempre verifique o comando para ver se ele está atualizado.

- Ao consumir APIs, apps, SDKs ou provedores externos, registre o nome do serviço, endpoint/contrato, autenticação e pré-condições neste arquivo; consulte a documentação oficial atual antes de implementar e não invente payloads.
- O `.looper/design.md` é a fonte das decisões visuais: identidade, tipografia, espaçamento, estados, acessibilidade e contraste mínimo devem estar preenchidos antes de liberar o bootstrap.
