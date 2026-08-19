# Looper Draw Editor

Este diretório contém os fontes editáveis do viewer React Flow usado pelo Looper.
Ele existe para desenvolvimento do editor e não é copiado para os projetos inicializados pelo comando `looper init`.

## Desenvolvimento

```bash
npm install
npm run dev
```

Para gerar o viewer distribuído pelo pacote Python:

```bash
npm run build
```

Depois copie o conteúdo de `dist/` para `src/looper/draw_assets/` e execute os testes Python do Looper.
O runtime do usuário continua usando somente os assets compilados do pacote, os Draws em `.looper/draws/` e os fatos derivados em `.looper/facts/`.
