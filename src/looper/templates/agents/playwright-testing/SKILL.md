---
name: playwright-testing
description: Cria e diagnostica testes Playwright de regressão para jornadas L2 e fluxos E2E, usando exploração observável, locators reais, asserções rígidas e evidências rastreáveis. Use ao criar, corrigir ou revisar testes de navegador.
---

# Playwright Testing

Use esta skill para transformar uma jornada observada ou especificada no Draw em um teste Playwright repetível. O teste deve comprovar estados visíveis, transições, erros e o estado final previsto; abrir uma página ou executar um clique não é evidência suficiente.

## Exploração antes do teste

O caminho preferencial é explorar a aplicação antes de escrever o script:

```bash
npx playwright-cli open "$BASE_URL"
npx playwright-cli snapshot
npx playwright-cli click <ref-do-controle-real>
npx playwright-cli snapshot
npx playwright-cli --help
```

Use `npx playwright-cli` para navegar com interação real, inspecionar a estrutura acessível, confirmar locators, reproduzir falhas, ver erros de scripts e entender em que estado a aplicação realmente ficou. Se um script falhar ou produzir resultado inesperado, volte ao `npx playwright-cli` para investigar o fluxo real antes de corrigir o teste.

Navegar não é obrigatório: se o agente já tiver evidência suficiente nos Draws, código, contratos e testes existentes para criar o teste corretamente, pode fazê-lo diretamente. Ainda assim, a exploração é recomendada porque reduz locators inventados, caminhos incorretos e asserções sobre estados que não existem.

Não confunda exploração com regressão automatizada. A navegação pelo CLI é diagnóstico e descoberta; a evidência repetível é o arquivo Playwright executado pelo runner.

## Configuração recomendada

Use uma janela visível, uma janela por jornada, execução sequencial e um worker:

```js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    headless: false,
    launchOptions: { slowMo: 100 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

Registre a suíte no `.looper/config.yaml`/`.looper/config.json` com `type: playwright`. Ela fica fora da execução padrão e só roda com:

```bash
npx playwright test --headed
looper test --playwright
```

## Implementação da jornada

- Use `page.goto()` somente para a entrada inicial.
- Para rotas intermediárias, use links, menus e botões reais.
- Prefira `getByRole`, labels e texto acessível; confirme o locator durante a exploração.
- Use uma única página/janela quando a jornada não exigir outra.
- Se o projeto tiver helpers visuais, use `installMousePointer`, `moveAndClick` e `moveAndFill` para tornar a interação observável; não invente helpers alternativos para contornar uma falha.
- Aguarde estado observável com locators e `expect`; não use `waitForTimeout` como prova de conclusão.
- Finalize cada cenário com asserção explícita do estado previsto no Draw, incluindo persistência observável quando fizer parte do comportamento.

Exemplo mínimo:

```js
import { test, expect } from '@playwright/test';

test('usuário conclui a configuração', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Configuração' }).click();
  await expect(page).toHaveURL(/configuracao/);
  await page.getByRole('button', { name: 'Salvar' }).click();
  await expect(page.getByRole('status')).toHaveText('Configuração salva');
  await expect(page.getByRole('heading', { name: 'Configuração concluída' })).toBeVisible();
});
```

## Falhas e escopo

Uma etapa crítica que falha deve falhar o teste. Não esconda a falha com `try/catch` sem relançar, `return`, `test.skip`, `test.fixme`, `test.fail`, selector alternativo, `page.goto()` direto ou uma asserção final genérica.

Para L2, valide tela, navegação, loading, vazio, erro, sucesso, foco, desabilitado e o estado final observável. Se o backend L3 ainda não existir, teste somente o caminho visual e a navegação que o Draw realmente especifica; não invente respostas de API.

Para L3, prefira os testes de unidade/integração/API apropriados para regras, controllers, persistência e integrações. O teste Playwright não substitui essas evidências.

## Fluxo com Looper

Leia o Draw e seus `code_refs` quando existirem, explore o fluxo quando isso ajudar, implemente o teste no diretório de testes do projeto, associe o nó ao arquivo e aos símbolos do teste quando a task for de implementação de testes e execute:

```bash
npx playwright test --headed
looper test --playwright
```

Se a skill for usada em `looper backlog test`, altere somente testes/fixtures autorizados, preserve produção, registre a evidência e conclua somente o ID recebido. Se a navegação revelar uma divergência do Draw, documente a evidência e não ajuste o teste para mascarar a aplicação.
