---
name: mock-server
description: Cria e mantém servidores locais de mock em Python para simular APIs externas com contrato, respostas determinísticas e requisições visíveis no terminal.
---

# Mock Server

Use esta skill quando a aplicação precisar chamar um endpoint local no lugar de um provedor externo, como OpenAI, gateway de pagamento, envio de e-mail ou serviço de identidade. O resultado é um servidor Python executável no terminal, com controle explícito das rotas, respostas e estados observáveis. O objetivo é reproduzir os contratos críticos do serviço, não criar uma cópia ampla do produto.

## Objetivo e limites

- Pesquise a documentação oficial atual do provedor escolhido antes de implementar. Registre método, URL, headers, autenticação, schema de entrada, schema de saída, códigos de erro e comportamento de streaming quando existirem. Não invente um contrato porque o nome da API parece familiar.
- O mock deve ser local e seguro por padrão: escute em `127.0.0.1`, use uma porta configurável e nunca encaminhe requisições reais ao provedor. Só implemente forwarding se isso for pedido explicitamente e houver uma barreira clara para evitar chamadas acidentais.
- Use Python. Prefira a biblioteca padrão (`http.server`, `json`, `argparse`, `logging`, `threading`) para que o servidor rode sem instalar dependências. Se o projeto já usar FastAPI, Flask ou outra biblioteca, preserve a stack existente e justifique a escolha.
- Não coloque chaves, tokens, cookies, payloads sensíveis ou valores de `.env` em código, fixtures, logs, commits ou documentação.
- Antes de escrever o mock, faça uma matriz do contrato do provedor separando claramente o que a aplicação envia e o que ela recebe. Para cada caminho, registre a documentação oficial consultada, pré-condições, método, URL, headers, autenticação, schema, resposta, erros, idempotência, retries e estado necessário.
- Faça sempre estas duas perguntas: qual credencial, formato e permissão são necessários para enviar a requisição? Qual mecanismo de webhook é necessário para receber eventos? Não trate uma URL pública, uma assinatura ou uma inscrição como detalhe opcional.

## Entrega esperada

Adapte os nomes ao projeto, mas mantenha responsabilidades separadas:

- `mock_server/server.py`: inicialização, configuração de host/porta e ciclo do servidor;
- `mock_server/routes.py` ou módulos por provedor: roteamento e validação do contrato;
- `mock_server/fixtures/`: respostas e cenários determinísticos, sem segredo;
- `mock_server/state.py`: estado em memória apenas quando o fluxo exigir sequência, como criar e depois consultar uma cobrança;
- `mock_server/README.md` ou seção equivalente: comando de execução, URL base, variáveis e exemplos de uso;
- testes que exercitem sucesso, payload inválido, autenticação inválida, rota desconhecida e os estados relevantes.

Não misture regras do provedor com o servidor HTTP genérico. O servidor deve aceitar múltiplos provedores por configuração ou módulos, sem copiar a implementação inteira para cada porta.

## Contrato e rotas

1. Identifique a URL base usada pela aplicação e torne-a configurável, por exemplo `MOCK_SERVER_BASE_URL=http://127.0.0.1:8081`. Não altere permanentemente endpoints de produção; use configuração de ambiente ou injeção de cliente.
2. Reproduza somente os endpoints necessários para o cenário. Preserve método, caminho, headers relevantes, query string, códigos HTTP, `Content-Type`, formato de erro e semântica de idempotência.
3. Valide JSON e campos obrigatórios antes de responder. Erros devem ser determinísticos e compatíveis com o contrato documentado.
4. Para streaming, implemente apenas se a aplicação realmente consumir streaming; reproduza o framing e `Content-Type` documentados e inclua um teste que consuma todos os eventos.
5. Para autenticação, aceite uma credencial de teste configurável e registre apenas se a validação passou. Nunca exiba o valor recebido.

## Contratos críticos de envio e recebimento

O mock deve modelar os caminhos críticos com a mesma ordem e as mesmas pré-condições do serviço real:

1. **Envio autenticado:** valide a credencial no mesmo local em que o provedor a espera (por exemplo, header, query ou corpo), o esquema exato, o formato do valor, escopos quando existirem e o comportamento de credencial ausente, malformada ou inválida. Não aceite qualquer header alternativo apenas para facilitar o teste.
2. **Ativação do recebimento:** quando o serviço exigir criação, registro, assinatura ou verificação de webhook antes de entregar eventos, implemente essa chamada como uma transição explícita de estado. Uma URL configurada no mock não significa que o webhook está ativo. O fluxo de entrega deve permanecer bloqueado até a ativação documentada ter ocorrido.
3. **Webhook recebido:** implemente um endpoint receptor separado, com método e caminho configuráveis conforme o provedor. Valide `Content-Type`, corpo, assinatura, timestamp, segredo, tolerância contra replay, identificador do evento e idempotência somente quando esses requisitos existirem no contrato oficial. Se o provedor não assinar, registre explicitamente que a proteção é somente por URL ou outra garantia documentada; nunca invente uma assinatura.
4. **Resposta e reentrega:** reproduza o status, corpo e headers que confirmam o recebimento. Modele duplicatas, ordem, retry e timeout apenas conforme documentado ou conforme o cenário explicitamente escolhido, deixando a decisão registrada no contrato do mock.

O servidor local deve expor apenas as rotas mínimas necessárias para esses fluxos. Não implemente o serviço inteiro, não faça forwarding e não transforme o webhook em um simples `POST` que sempre retorna sucesso. O teste deve provar a sequência `configurar/autorizar -> ativar webhook -> receber evento`, além de provar que cada etapa falha quando sua pré-condição está ausente.

Use credenciais e segredos de assinatura fictícios, injetados por configuração de teste e separados entre autenticação de saída e validação de entrada. Nunca reutilize o segredo real do provedor. O estado de ativação deve ser reinicializável entre testes e observável por respostas ou introspecção de teste segura, sem expor segredos.

Exemplo: se a aplicação usa OpenAI, consulte a documentação oficial do endpoint específico (por exemplo, Responses ou Chat Completions), confirme o schema vigente e crie apenas a rota local equivalente, como `POST /v1/responses`. O exemplo não autoriza assumir que endpoints, campos ou headers de outra versão são intercambiáveis.

## Observabilidade no terminal

Cada requisição deve produzir uma linha legível no terminal onde o servidor foi iniciado, contendo pelo menos:

`timestamp método caminho status duração_ms request_id`

Inclua tamanho do corpo e um resumo seguro quando ajudar no diagnóstico. Redija `Authorization`, cookies, API keys, tokens, e-mails ou campos marcados como sensíveis; em caso de dúvida, omita o valor. Não despeje automaticamente o body bruto. Ofereça uma opção explícita de debug para payloads sintéticos e seguros, com redaction ainda ativa.

Registre também início e encerramento do servidor, porta efetiva, rota desconhecida, erro de parsing e exceções internas. Gere um `request_id` por requisição e devolva-o no header de resposta quando compatível. O log não substitui os testes: ele deve permitir confirmar rapidamente qual chamada a aplicação realmente fez.

## Execução e validação

Forneça um comando reproduzível, por exemplo:

```bash
python -m mock_server --host 127.0.0.1 --port 8081
```

O processo deve permanecer em primeiro plano, tratar `Ctrl-C` de forma limpa e indicar a URL base ao iniciar. Use `curl` ou o cliente real da aplicação para demonstrar ao menos uma chamada. Verifique que a aplicação está apontando para o host local, que nenhuma chamada sai para a internet e que o terminal mostra método, rota e status.

Antes de concluir, execute os testes do projeto e um teste direto do servidor. Confirme respostas para sucesso e falhas, isolamento entre testes, encerramento sem threads órfãs e comportamento quando a porta já estiver ocupada. Se houver persistência em memória, disponibilize reset controlado para os testes e deixe claro que ela não é produção.

Para cada integração, cubra no mínimo: envio sem credencial, credencial inválida, payload inválido, tentativa de receber antes da ativação, ativação válida, webhook com assinatura ausente ou inválida quando aplicável, evento válido, evento duplicado e rota desconhecida. Remova da matriz os casos que a documentação oficial provar não existir e registre essa ausência.

Ao entregar, informe os arquivos criados/alterados, o contrato oficial consultado, comando de execução, porta, rotas suportadas, cenários cobertos e limitações conhecidas.
