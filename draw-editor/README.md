# STDD Draw Editor

Este diretório contém os fontes editáveis do viewer React Flow usado pelo STDD.
Ele existe para desenvolvimento do editor e não é copiado para os projetos inicializados pelo comando `stdd init`.

## Desenvolvimento

```bash
npm install
npm run dev
```

Para gerar o viewer distribuído pelo pacote Python:

```bash
npm run build
```

Depois copie o conteúdo de `dist/` para `src/stdd/draw_assets/` e execute os testes Python do STDD.
O runtime do usuário continua usando somente os assets compilados do pacote e os JSONs em `.stdd/draws/`.
