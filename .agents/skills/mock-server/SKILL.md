---
name: mock-server
description: Cria e mantém servidores locais de mock em Python para simular APIs externas com contrato, respostas determinísticas e requisições visíveis no terminal.
---

# Mock Server

Use esta skill quando a aplicação precisar chamar um endpoint local no lugar de um provedor externo, como OpenAI, gateway de pagamento, envio de e-mail ou serviço de identidade. O resultado é um servidor Python executável no terminal, com controle explícito das rotas, respostas e estados observáveis.

## Objetivo e limites

- Pesquise a documentação oficial atual do provedor escolhido antes de implementar. Registre método, URL, headers, autenticação, schema de entrada, schema de saída, códigos de erro e comportamento de streaming quando existirem. Não invente um contrato porque o nome da API parece familiar.
- O mock deve ser local e seguro por padrão: escute em `127.0.0.1`, use uma porta configurável e nunca encaminhe requisições reais ao provedor. Só implemente forwarding se isso for pedido explicitamente e houver uma barreira clara para evitar chamadas acidentais.
- Use Python. Prefira a biblioteca padrão (`http.server`, `json`, `argparse`, `logging`, `threading`) para que o servidor rode sem instalar dependências. Se o projeto já usar FastAPI, Flask ou outra biblioteca, preserve a stack existente e justifique a escolha.
- Não coloque chaves, tokens, cookies, payloads sensíveis ou valores de `.env` em código, fixtures, logs, commits ou documentação.

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

Ao entregar, informe os arquivos criados/alterados, o contrato oficial consultado, comando de execução, porta, rotas suportadas, cenários cobertos e limitações conhecidas.
