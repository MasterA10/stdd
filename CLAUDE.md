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
- `$create-tests-backlog`, `$implement-frontend` e `$implement-backend` pertencem exclusivamente aos loops acionados por `looper backlog test`, `looper backlog frontend`, `looper backlog backend` e `looper backlog task`; não leia essas skills para edições, perguntas ou medições comuns fora do backlog.
- Quando o pedido vier de uma interação comum, trate-o como interação comum e siga somente as instruções necessárias ao pedido; não transforme a edição em task de backlog nem exija o ciclo de testes/implementação do backlog sem que o cursor tenha entregue uma task.
- No loop do backlog, execute `looper backlog complete <task-id>` com o mesmo ID recebido somente após validar a task; sem isso, o cursor não avança.
- Quando o backlog entregar o nó e os subfluxos internos juntos, implemente e teste ambos; “Tela” classifica o nível do nó e não limita a entrega ao frontend.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
### Estratégia de desenvolvimento do backlog

- O modo é separado: conclua todos os nós L2 como frontend/view antes de liberar qualquer L3.
- Nas tasks L2, implemente a tela, estados, interações e links/transições entre telas; não implemente controller, model, regra de negócio, persistência ou integrações de backend.
- Nas tasks L3, implemente o backend/controller/model e seus testes; o loop de testes não cria testes para L2.
- Os filtros `--frontend` e `--backend` são transitórios e não concluem a outra camada.
<!-- Looper:END AGENT INSTRUCTIONS -->
