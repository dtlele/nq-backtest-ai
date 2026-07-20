import { test, expect } from '@playwright/test';
import * as fs from 'fs';

test('diagnose React render crashes', async ({ page }) => {
  const errors: string[] = [];
  const logs: string[] = [];

  // Intercept console messages
  page.on('console', msg => {
    const text = msg.text();
    logs.push(`[${msg.type()}] ${text}`);
    if (msg.type() === 'error') {
      errors.push(text);
    }
  });

  // Intercept unhandled exceptions
  page.on('pageerror', exception => {
    errors.push(`Uncaught Exception: ${exception.message}\n${exception.stack}`);
  });

  console.log('Navigating to http://localhost:5173...');
  try {
    // Wait until network is mostly idle to ensure JS loads
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  } catch (e: any) {
    errors.push(`Navigation failed: ${e.message}`);
  }

  // Wait a couple of seconds to let any React effects fire
  await page.waitForTimeout(2000);

  // Take a screenshot of exactly what is being rendered
  await page.screenshot({ path: 'tests/render_screenshot.png' });

  // Try to find if the main app container rendered
  const rootContent = await page.locator('#root').innerHTML().catch(() => 'Root not found');
  
  // Write diagnostic report
  const report = `
=== DIAGNOSTIC REPORT ===
Page Title: ${await page.title().catch(() => 'Failed to get title')}
Root HTML Length: ${rootContent.length} bytes

=== CONSOLE LOGS ===
${logs.join('\n')}

=== CRITICAL ERRORS ===
${errors.join('\n')}
  `;

  fs.writeFileSync('tests/diagnostic_report.txt', report);
  
  // Always fail the test if there are errors so we can catch it
  if (errors.length > 0) {
    console.error('Test found errors! See tests/diagnostic_report.txt');
    throw new Error(`Found ${errors.length} errors during render.`);
  }

  // Also fail if root is empty (React crashed silently before rendering)
  if (rootContent.trim() === '') {
    throw new Error("React root is empty! Silent render crash.");
  }

  console.log('Test passed. UI rendered without errors.');
});
