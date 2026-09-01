# Guia padrão de Playwright do Looper

Este guia é instalado automaticamente pelo `looper init`. Ele define o padrão para
testes E2E observáveis, em janela única contínua, com navegação orgânica e cursor de
mouse visual acompanhando movimentos e cliques.

## 1. Estrutura recomendada

```text
├── playwright.config.js
├── PLAYWRIGHT_GUIDE.md
└── tests/
    └── e2e/
        ├── cursor_helper.js
        └── single_window_complete_journey.spec.js
```

## 2. Configuração do Playwright

Use uma janela visível, execução sequencial e um único worker:

```javascript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120 * 1000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.WP_BASE_URL || 'http://seu-site.test',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    headless: false,
    launchOptions: { slowMo: 100 },
  },
  projects: [{
    name: 'chromium',
    use: { ...devices['Desktop Chrome'] },
  }],
});
```

O padrão visual dos testes também exige rolagem suave. Essa regra pertence ao
harness do Playwright e não deve ser adicionada nem exigida no CSS da aplicação.
O helper abaixo injeta a configuração somente na página controlada pelo teste,
inclusive quando a aplicação não tiver declarado a regra:

## 3. Cursor e helpers de interação

Crie `tests/e2e/cursor_helper.js` com o helper abaixo. Ele injeta uma seta clássica
e um anel de clique no DOM, sincronizados com os eventos reais do Playwright.

```javascript
export async function installMousePointer(page) {
  await page.addInitScript(() => {
    const initCursor = () => {
      if (!document.getElementById('playwright-smooth-scroll')) {
        const style = document.createElement('style');
        style.id = 'playwright-smooth-scroll';
        style.innerHTML = `
          html {
            scroll-behavior: smooth !important;
          }
        `;
        const appendStyle = () => document.head.appendChild(style);
        document.head
          ? appendStyle()
          : document.addEventListener('DOMContentLoaded', appendStyle, { once: true });
      }
      if (document.getElementById('playwright-mouse-pointer')) return;

      const cursor = document.createElement('div');
      cursor.id = 'playwright-mouse-pointer';
      cursor.style.cssText = `
        position: fixed !important; top: 0 !important; left: 0 !important;
        width: 20px !important; height: 20px !important;
        background-image: url('data:image/svg+xml;utf8,<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 3L10.5 21L13.5 13.5L21 10.5L3 3Z" fill="%231E1E1E" stroke="white" stroke-width="1.5" stroke-linejoin="round"/></svg>') !important;
        background-size: contain !important; background-repeat: no-repeat !important;
        z-index: 2147483647 !important; pointer-events: none !important;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,.4)) !important;
      `;
      const ring = document.createElement('div');
      ring.id = 'playwright-mouse-ring';
      ring.style.cssText = `
        position: fixed !important; width: 24px !important; height: 24px !important;
        border-radius: 50% !important; border: 2px solid rgba(0,102,204,.7) !important;
        background: rgba(0,102,204,.15) !important; z-index: 2147483646 !important;
        pointer-events: none !important; transform: translate(-50%,-50%) scale(0) !important;
        opacity: 0 !important; transition: transform .25s ease-out, opacity .25s ease-out !important;
      `;
      const attach = () => {
        if (document.body && !document.getElementById('playwright-mouse-pointer')) {
          document.body.append(cursor, ring);
        }
      };
      if (document.body) attach();
      else window.addEventListener('DOMContentLoaded', attach, { once: true });
      window.addEventListener('mousemove', (event) => {
        cursor.style.transform = `translate3d(${event.clientX}px,${event.clientY}px,0)`;
      }, { passive: true });
      window.addEventListener('mousedown', (event) => {
        cursor.style.transform = `translate3d(${event.clientX + 1}px,${event.clientY + 1}px,0) scale(.92)`;
        ring.style.left = `${event.clientX + 3}px`;
        ring.style.top = `${event.clientY + 3}px`;
        ring.style.transform = 'translate(-50%,-50%) scale(1.4)';
        ring.style.opacity = '1';
      }, { passive: true });
      window.addEventListener('mouseup', (event) => {
        cursor.style.transform = `translate3d(${event.clientX}px,${event.clientY}px,0) scale(1)`;
        ring.style.transform = 'translate(-50%,-50%) scale(0)';
        ring.style.opacity = '0';
      }, { passive: true });
    };
    initCursor();
  });
}

/** Realiza rolagem suave gradual e centraliza o elemento na tela. */
export async function smoothScrollIntoView(page, locator) {
  const handle = await locator.elementHandle();
  if (!handle) {
    throw new Error('Não foi possível localizar o elemento para rolagem suave.');
  }
  await page.evaluate((element) => {
    element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
  }, handle);
  await page.waitForTimeout(350);
}

export async function moveAndClick(page, locatorOrSelector) {
  const locator = typeof locatorOrSelector === 'string'
    ? page.locator(locatorOrSelector).first() : locatorOrSelector.first();
  await smoothScrollIntoView(page, locator);
  const box = await locator.boundingBox();
  if (!box) return locator.click();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
  await page.waitForTimeout(100);
  await page.mouse.down();
  await page.waitForTimeout(80);
  await page.mouse.up();
  await page.waitForTimeout(150);
}

export async function moveAndFill(page, locatorOrSelector, text) {
  const locator = typeof locatorOrSelector === 'string'
    ? page.locator(locatorOrSelector).first() : locatorOrSelector.first();
  await smoothScrollIntoView(page, locator);
  const box = await locator.boundingBox();
  if (box) {
    await page.mouse.move(box.x + 15, box.y + box.height / 2, { steps: 12 });
    await page.waitForTimeout(100);
    await page.mouse.down();
    await page.waitForTimeout(60);
    await page.mouse.up();
    await page.waitForTimeout(80);
  }
  await locator.fill(text);
}
```

## 4. Navegação orgânica

Use `page.goto()` somente no ponto inicial da jornada. Para rotas intermediárias,
use links, menus e botões reais da interface com `moveAndClick`; não cole URLs e não
abra outra página para continuar o fluxo sem exigência explícita.

```javascript
import { test, expect } from '@playwright/test';
import { installMousePointer, moveAndClick, moveAndFill } from './cursor_helper.js';

test('Jornada orgânica do usuário', async ({ page }) => {
  await installMousePointer(page);
  await page.goto('/wp-login.php');
  await moveAndFill(page, '#user_login', 'admin');
  await moveAndFill(page, '#user_pass', 'admin123');
  await moveAndClick(page, '#wp-submit');
  await moveAndClick(page, '#adminmenu a:has-text("Micro Guarulhos")');
  await moveAndClick(page, 'a:has-text("Novo evento")');
  await moveAndFill(page, 'input[name="event_name"]', 'Meu Evento');
  await moveAndClick(page, 'button:has-text("Salvar configuração")');
  await expect(page.getByRole('status')).toHaveText('Configuração salva');
  await expect(page.getByText('Meu Evento')).toBeVisible();
});
```

## 5. Execução

```bash
npx playwright test --headed
```

## 6. Escopo configurável L2/L3

O Looper permite selecionar quais níveis recebem testes:

```yaml
backlog:
  test_scope: both  # l2, l3 ou both
  test_loop:
    scope: both
```

Também é possível alterar pela interface de configurações ou pela CLI:

```bash
looper backlog config --test-scope l2
looper backlog config --test-scope l3
looper backlog config --test-scope both
```

`l2` testa somente telas e navegação; `l3` testa regras de negócio, controllers,
models, persistência e integrações; `both` mantém testes independentes para as duas
camadas.

## 7. Padrão obrigatório para testes L2

Todo teste L2 deve usar janela visível única, `workers: 1`, execução sequencial,
`installMousePointer(page)`, `moveAndClick` e `moveAndFill`. Campos devem ser
limpos explicitamente quando a jornada exigir. Confirme estados visíveis, mensagens,
habilitação, desabilitação e navegação.

Se as regras de negócio L3 ainda não estiverem implementadas, o teste L2 deve validar
as telas conectadas, links/rotas de saída e chegada à tela de destino. Não invente
respostas de API nem implemente regras de negócio no teste L2.

### O teste deve falhar quando a jornada não terminar

Uma jornada Playwright só pode ser aprovada depois de uma asserção explícita do estado
final previsto no Draw. Chegar ao fim do arquivo, deixar o navegador aberto, executar
um clique parcial ou observar que uma tela carregou não significa que o teste passou.

Se qualquer etapa não puder ser concluída, o teste deve falhar e o processo deve sair
com código diferente de zero. Use locators que aguardem estado observável e uma
asserção final; os timeouts padrão do Playwright devem propagar o erro:

Para ações críticas, faça primeiro a asserção rígida do elemento e da condição de
negócio. Não use um seletor alternativo para contornar a ausência do caminho real:

```javascript
await expect(
  page.getByText('As inscrições estão temporariamente fechadas')
).not.toBeVisible();

const btnComprar = page.locator('a:has-text("Comprar"), a[href*="identificacao"]').first();
await expect(
  btnComprar,
  'Botão de comprar/inscrição deve existir e estar visível'
).toBeVisible();
await moveAndClick(page, btnComprar);
```

Se a mensagem de inscrições fechadas estiver visível, ou se `btnComprar` não existir
ou estiver oculto, o `expect` deve quebrar o teste imediatamente. Não substitua esse
erro por outro link, `page.goto()` direto ou uma ramificação facilitadora.

```javascript
test('L2 conclui a jornada de configuração', async ({ page }) => {
  await page.goto('/');
  await moveAndClick(page, 'a:has-text("Configuração")');
  await expect(page).toHaveURL(/configuracao/);
  await moveAndClick(page, 'button:has-text("Salvar")');

  // Sem esta prova, a jornada não está concluída.
  await expect(page.getByRole('status')).toHaveText('Configuração salva');
  await expect(page.getByRole('heading', { name: 'Configuração concluída' })).toBeVisible();
});
```

É proibido, para esconder uma jornada incompleta:

- envolver ações ou asserções em `try/catch` sem relançar o erro;
- usar `return`, `test.skip()`, `test.fixme()` ou `test.fail()` quando uma etapa falhar;
- usar `page.waitForTimeout()` como substituto de uma asserção de estado;
- marcar o teste como concluído apenas porque a janela abriu ou uma rota respondeu;
- capturar uma exceção e continuar para a asserção final como se o fluxo tivesse sido concluído.

Se uma etapa opcional realmente não fizer parte do cenário, remova-a do teste ou
modele explicitamente a decisão no Draw. Não transforme uma falha de aplicação,
seletor, rota, carregamento ou backend em `passed`/`not_executed`.

```javascript
test('L2 navega entre telas ainda sem backend', async ({ page }) => {
  await page.goto('/');
  await moveAndClick(page, 'a:has-text("Configuração")');
  await expect(page.getByRole('heading', { name: 'Configuração' })).toBeVisible();
  await moveAndClick(page, 'button:has-text("Continuar")');
  await expect(page).toHaveURL(/confirmacao/);
  await expect(page.getByRole('heading', { name: 'Confirmação' })).toBeVisible();
});
```

## 8. Padrão para testes L3

Testes L3 validam regras, decisões, validações de domínio, controllers, respostas
HTTP, models, persistência, integrações, retries, idempotência e erros documentados.
Eles não substituem a navegação L2. Também precisam terminar com asserções dos
efeitos esperados; exceções, respostas inválidas e efeitos ausentes devem falhar o
teste. Quando `test_scope: both`, cada camada deve manter suas próprias evidências.

## 9. Modos de validação e critério do loop

## 9.1 Dois modos de validação do fluxo

O Looper diferencia descoberta funcional de teste de regressão:

### A. Ainda não existe teste Playwright

Use `playwright-cli` para abrir a aplicação, executar o fluxo com interação real,
inspecionar cada estado e confirmar que a jornada existe e funciona. Essa validação
é exploratória e não deve ser registrada como uma suíte Playwright concluída. Se uma
etapa falhar, a validação deve ser reportada como falha/bloqueio com a evidência do
estado encontrado.

```bash
playwright-cli open "$BASE_URL"
playwright-cli snapshot
playwright-cli click <ref-do-botao-real>
playwright-cli snapshot
```

Não invente um script de regressão antes de confirmar a jornada no `playwright-cli`.

### B. Já existe teste Playwright para o fluxo

Crie ou atualize o script Playwright de regressão para refazer a mesma jornada de
forma determinística. O script deve usar os helpers deste guia, locators reais,
asserções rígidas em cada transição crítica e a asserção do estado final. Uma falha
deve fazer o comando Playwright terminar com código diferente de zero.

O `playwright-cli` continua sendo usado para explorar e diagnosticar; o script
Playwright é a evidência automatizada repetível que protege o fluxo contra regressão.
Não substitua um teste existente por uma simples exploração no CLI.

Ao receber `looper backlog test`, crie apenas o nível entregue e não altere produção.
Após validar os testes, conclua a task com o ID recebido:

```bash
looper backlog test
looper backlog complete <task-id>
```

Com `l2`, tasks L3 são `not-required`; com `l3`, tasks L2 são `not-required`; com
`both`, as duas camadas precisam de testes independentes antes da implementação.
