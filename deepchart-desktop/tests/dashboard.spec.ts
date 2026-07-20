import { test, expect } from '@playwright/test';

test.describe('DeepPrint Pro UI Tests', () => {
  test('Dashboard should mount without React crashes', async ({ page }) => {
    // Intercetta eventuali eccezioni React in console per far fallire il test se presenti
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    
    // Non andiamo in crash per errori di WebSocket (poiché il test gira senza backend python)
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('WebSocket')) {
        errors.push(msg.text());
      }
    });

    await page.goto('/');

    // 1. Verifica che la pagina abbia il titolo corretto
    await expect(page).toHaveTitle(/DeepPrint Pro/);

    // 2. Verifica che il layout React sia stato iniettato (cerca il tag main)
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();

    // 3. Verifica i blocchi strutturali principali
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('aside')).toBeVisible(); // La sidebar di sinistra
    
    // 4. Verifica il Footprint container
    const chartContainer = page.locator('.flex-1.overflow-auto'); // L'area di scroll del chart
    await expect(chartContainer).toBeVisible();

    // Assicurati che non ci siano stati crash React
    expect(errors).toHaveLength(0);
  });
});
