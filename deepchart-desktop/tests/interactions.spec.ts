import { test, expect } from '@playwright/test';

test.describe('DeepPrint Pro - Advanced UI & Vector Interactions', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navighiamo all'app locale
    await page.goto('/');
    
    // Attendiamo che il DOM React abbia montato il layout istituzionale
    await page.waitForSelector('aside'); 
    await page.waitForSelector('main');
  });

  test('Sidebar Tabs route to correct panes', async ({ page }) => {
    // 1. Assicuriamoci che il grafico Footprint sia caricato di default (cursor-grab)
    const chartContainer = page.locator('.cursor-grab');
    await expect(chartContainer).toBeVisible();

    // 2. Clicchiamo sul secondo tab (Stats)
    const statsTab = page.locator('aside > div').nth(1);
    await statsTab.click();

    // 3. Verifichiamo che il grafico sia scomparso e appaia il testo corretto
    await expect(page.getByText('STATS PANE - Coming Soon')).toBeVisible();
    await expect(chartContainer).not.toBeVisible();

    // 4. Ritorniamo al tab Chart
    const chartTab = page.locator('aside > div').nth(0);
    await chartTab.click();
    await expect(chartContainer).toBeVisible();
  });

  test('Order Book (DOM) renders completely', async ({ page }) => {
    // Verifichiamo che la colonna destra del DOM sia presente
    const domHeader = page.getByText('ORDER BOOK (DOM)');
    await expect(domHeader).toBeVisible();

    // Verifichiamo che le colonne strutturali ci siano
    await expect(page.getByText('BID SIZ')).toBeVisible();
    await expect(page.getByText('PRICE').first()).toBeVisible();
    await expect(page.getByText('ASK SIZ')).toBeVisible();
  });

  test('Unified Grid Vector Pan (Drag & Drop) executes flawlessly', async ({ page }) => {
    // Prendiamo il contenitore del grafico in modo invariante
    const chart = page.getByTestId('chart-container');
    await expect(chart).toBeVisible();
    
    // Verifichiamo il box
    const box = await chart.boundingBox();
    expect(box).not.toBeNull();
    if (!box) return;

    // Prima del drag, il cursore è grab
    await expect(chart).toHaveClass(/cursor-grab/);

    // Simuliamo un "Mouse Down" al centro del grafico
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();

    // Durante il drag, la classe CSS deve cambiare in cursor-grabbing per il feedback visivo
    await expect(chart).toHaveClass(/cursor-grabbing/);
    
    // Trasciniamo il grafico di 200px a sinistra e in alto
    await page.mouse.move(box.x + box.width / 2 - 200, box.y + box.height / 2 - 200, { steps: 5 });
    
    // Rilasciamo il mouse
    await page.mouse.up();
    
    // Il cursore deve tornare normale
    await expect(chart).toHaveClass(/cursor-grab/);
  });
});
